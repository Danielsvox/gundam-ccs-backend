from rest_framework import serializers
from django.contrib.auth import get_user_model
from products.serializers import ProductListSerializer
from .models import Cart, CartItem, CartCoupon, AppliedCoupon

User = get_user_model()


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items."""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total_price = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_id', 'quantity',
                  'total_price', 'is_available', 'added_at', 'updated_at')
        read_only_fields = ('id', 'product', 'total_price',
                            'is_available', 'added_at', 'updated_at')

    def get_total_price(self, obj):
        """Calculate total price for this item."""
        return obj.total_price

    def get_is_available(self, obj):
        """Check if the product is available in the requested quantity."""
        return obj.is_available

    def validate_quantity(self, value):
        """Validate quantity."""
        if value <= 0:
            raise serializers.ValidationError(
                'Quantity must be greater than 0.')
        return value


class CartItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating cart items."""

    product_id = serializers.IntegerField()

    class Meta:
        model = CartItem
        fields = ('product_id', 'quantity')

    def validate(self, attrs):
        """Validate cart item data."""
        from products.models import Product

        product_id = attrs['product_id']
        quantity = attrs.get('quantity', 1)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Product not found.')

        if not product.in_stock:
            raise serializers.ValidationError('Product is out of stock.')

        if product.stock_quantity < quantity:
            raise serializers.ValidationError(
                f'Only {product.stock_quantity} items available in stock.')

        attrs['product'] = product
        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating cart items."""

    class Meta:
        model = CartItem
        fields = ('quantity',)

    def validate_quantity(self, value):
        """Validate quantity."""
        if value <= 0:
            raise serializers.ValidationError(
                'Quantity must be greater than 0.')

        # Check stock availability
        if hasattr(self, 'instance') and self.instance:
            if self.instance.product.stock_quantity < value:
                raise serializers.ValidationError(
                    f'Only {self.instance.product.stock_quantity} items available in stock.')

        return value


class CartCouponSerializer(serializers.ModelSerializer):
    """Serializer for cart coupons."""

    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = CartCoupon
        fields = ('id', 'code', 'name', 'description', 'coupon_type', 'value', 'minimum_purchase',
                  'maximum_discount', 'usage_limit', 'used_count', 'is_active', 'is_valid',
                  'valid_from', 'valid_until', 'created_at')
        read_only_fields = ('id', 'used_count', 'created_at')

    def get_is_valid(self, obj):
        """Check if the coupon is valid."""
        return obj.is_valid


class AppliedCouponSerializer(serializers.ModelSerializer):
    """Serializer for applied coupons."""

    coupon = CartCouponSerializer(read_only=True)

    class Meta:
        model = AppliedCoupon
        fields = ('id', 'coupon', 'discount_amount', 'applied_at')
        read_only_fields = ('id', 'discount_amount', 'applied_at')


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart."""

    items = CartItemSerializer(many=True, read_only=True)
    applied_coupons = AppliedCouponSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    total_price_with_tax = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'user', 'items', 'applied_coupons', 'total_items', 'total_price',
                  'total_price_with_tax', 'discount_amount', 'final_price', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'total_items', 'total_price', 'total_price_with_tax',
                            'discount_amount', 'final_price', 'created_at', 'updated_at')

    def get_total_items(self, obj):
        """Get total number of items in cart."""
        return obj.total_items

    def get_total_price(self, obj):
        """Get total price of all items in cart."""
        return obj.total_price

    def get_total_price_with_tax(self, obj):
        """Get total price including tax."""
        return obj.total_price_with_tax

    def get_discount_amount(self, obj):
        """Calculate total discount from applied coupons."""
        return sum(coupon.discount_amount for coupon in obj.applied_coupons.all())

    def get_final_price(self, obj):
        """Calculate final price after discounts."""
        total_price = obj.total_price
        discount_amount = self.get_discount_amount(obj)
        return max(0, total_price - discount_amount)


class ApplyCouponSerializer(serializers.Serializer):
    """Serializer for applying coupons to cart."""

    coupon_code = serializers.CharField()

    def validate_coupon_code(self, value):
        """Validate coupon code."""
        try:
            coupon = CartCoupon.objects.get(code=value.upper())
            if not coupon.is_valid:
                raise serializers.ValidationError('Coupon is not valid.')
        except CartCoupon.DoesNotExist:
            raise serializers.ValidationError('Invalid coupon code.')

        return value


class CartSummarySerializer(serializers.ModelSerializer):
    """Serializer for cart summary."""

    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'total_items', 'total_price',
                  'discount_amount', 'final_price')
        read_only_fields = ('id', 'total_items', 'total_price',
                            'discount_amount', 'final_price')

    def get_total_items(self, obj):
        """Get total number of items in cart."""
        return obj.total_items

    def get_total_price(self, obj):
        """Get total price of all items in cart."""
        return obj.total_price

    def get_discount_amount(self, obj):
        """Calculate total discount from applied coupons."""
        return sum(coupon.discount_amount for coupon in obj.applied_coupons.all())

    def get_final_price(self, obj):
        """Calculate final price after discounts."""
        total_price = obj.total_price
        discount_amount = self.get_discount_amount(obj)
        return max(0, total_price - discount_amount)
