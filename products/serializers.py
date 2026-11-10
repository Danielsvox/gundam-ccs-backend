from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Category, Product, ProductImage, Review, ProductSpecification

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for categories."""

    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'image',
                  'is_active', 'product_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'slug', 'product_count',
                            'created_at', 'updated_at')

    def get_product_count(self, obj):
        """Get the number of products in this category.

        Memoised per request: a product list nests the category on every row and
        used to run one COUNT query per product.
        """
        counts = self.context.setdefault('_category_counts', {})
        if obj.pk not in counts:
            counts[obj.pk] = obj.products.filter(is_active=True).count()
        return counts[obj.pk]


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images."""

    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text',
                  'is_primary', 'order', 'created_at')
        read_only_fields = ('id', 'created_at')


class ProductSpecificationSerializer(serializers.ModelSerializer):
    """Serializer for product specifications."""

    class Meta:
        model = ProductSpecification
        fields = ('id', 'name', 'value', 'order')
        read_only_fields = ('id',)


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for product reviews."""

    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ('id', 'product', 'user', 'user_name', 'user_avatar', 'rating', 'title',
                  'comment', 'is_verified_purchase', 'helpful_votes', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'user_name', 'user_avatar', 'is_verified_purchase',
                            'helpful_votes', 'created_at', 'updated_at')

    def get_user_name(self, obj):
        """Get user's display name."""
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    def get_user_avatar(self, obj):
        """Get user's avatar URL."""
        if obj.user.avatar:
            return obj.user.avatar.url
        return None

    def create(self, validated_data):
        """Create a new review."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


def _primary_image_data(product, context):
    """Pick the primary image in Python so a prefetch_related('images') is enough."""
    images = list(product.images.all())
    if not images:
        return None
    primary = next((img for img in images if img.is_primary), images[0])
    return ProductImageSerializer(primary, context=context).data


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for listing products."""

    category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    is_on_sale = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'short_description', 'category', 'grade', 'scale',
                  'manufacturer', 'price', 'sale_price', 'current_price', 'is_on_sale',
                  'discount_percentage', 'in_stock', 'stock_quantity', 'rating', 'review_count',
                  'is_featured', 'primary_image', 'created_at')
        read_only_fields = ('id', 'slug', 'rating',
                            'review_count', 'created_at')

    def get_primary_image(self, obj):
        """Primary image (or first image). Works from the prefetch cache, no extra queries."""
        return _primary_image_data(obj, self.context)

    def get_current_price(self, obj):
        """Get the current price of the product."""
        return obj.current_price

    def get_is_on_sale(self, obj):
        """Check if the product is on sale."""
        return obj.is_on_sale

    def get_discount_percentage(self, obj):
        """Get the discount percentage."""
        return obj.discount_percentage


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product details."""

    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    current_price = serializers.SerializerMethodField()
    is_on_sale = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'description', 'short_description', 'category',
                  'grade', 'scale', 'manufacturer', 'release_date', 'price', 'sale_price',
                  'current_price', 'is_on_sale', 'discount_percentage', 'in_stock',
                  'stock_quantity', 'sku', 'weight', 'dimensions', 'rating', 'review_count',
                  'is_featured', 'is_active', 'images', 'specifications', 'reviews',
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'slug', 'sku', 'rating',
                            'review_count', 'created_at', 'updated_at')

    def get_current_price(self, obj):
        """Get the current price of the product."""
        return obj.current_price

    def get_is_on_sale(self, obj):
        """Check if the product is on sale."""
        return obj.is_on_sale

    def get_discount_percentage(self, obj):
        """Get the discount percentage."""
        return obj.discount_percentage


class ProductSearchSerializer(serializers.ModelSerializer):
    """Serializer for product search results."""

    category = CategorySerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'category', 'grade', 'current_price', 'rating',
                  'review_count', 'primary_image')

    def get_primary_image(self, obj):
        """Get the primary image for the product."""
        return _primary_image_data(obj, self.context)

    def get_current_price(self, obj):
        """Get the current price of the product."""
        return obj.current_price


class ProductFilterSerializer(serializers.Serializer):
    """Serializer for product filtering."""

    category = serializers.CharField(required=False)
    grade = serializers.CharField(required=False)
    manufacturer = serializers.CharField(required=False)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False)
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False)
    in_stock = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    search = serializers.CharField(required=False)
    ordering = serializers.CharField(required=False)


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews."""

    class Meta:
        model = Review
        fields = ('product', 'rating', 'title', 'comment')

    def validate(self, attrs):
        """Validate review data."""
        user = self.context['request'].user
        product = attrs['product']

        # Check if user has already reviewed this product
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError(
                'You have already reviewed this product.')

        return attrs

    def create(self, validated_data):
        """Create a new review."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating reviews."""

    class Meta:
        model = Review
        fields = ('rating', 'title', 'comment')

    def validate(self, attrs):
        """Validate review update."""
        user = self.context['request'].user
        review = self.instance

        # Ensure user can only update their own reviews
        if review.user != user:
            raise serializers.ValidationError(
                'You can only update your own reviews.')

        return attrs
