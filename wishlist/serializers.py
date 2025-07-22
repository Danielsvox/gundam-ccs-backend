from rest_framework import serializers
from django.contrib.auth import get_user_model
from products.serializers import ProductListSerializer
from .models import Wishlist, WishlistItem, WishlistShare, PriceAlert, WishlistAnalytics

User = get_user_model()


class WishlistItemSerializer(serializers.ModelSerializer):
    """Serializer for wishlist items."""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = WishlistItem
        fields = ('id', 'wishlist', 'product', 'product_id',
                  'priority', 'notes', 'current_price', 'added_at')
        read_only_fields = ('id', 'wishlist', 'product',
                            'current_price', 'added_at')

    def get_current_price(self, obj):
        """Get current price of the product."""
        return obj.product.current_price


class WishlistItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating wishlist items."""

    product_id = serializers.IntegerField()

    class Meta:
        model = WishlistItem
        fields = ('product_id', 'priority', 'notes')

    def validate(self, attrs):
        """Validate wishlist item data."""
        from products.models import Product

        product_id = attrs['product_id']

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Product not found.')

        # Check if product is already in user's wishlist
        user = self.context['request'].user
        wishlist = Wishlist.objects.filter(user=user).first()
        if wishlist and WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
            raise serializers.ValidationError(
                'Product is already in your wishlist.')

        attrs['product'] = product
        return attrs

    def create(self, validated_data):
        """Create a new wishlist item."""
        user = self.context['request'].user
        wishlist, created = Wishlist.objects.get_or_create(user=user)
        validated_data['wishlist'] = wishlist
        return super().create(validated_data)


class WishlistItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating wishlist items."""

    class Meta:
        model = WishlistItem
        fields = ('priority', 'notes')


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for wishlists."""

    items = WishlistItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ('id', 'user', 'name', 'is_public', 'items',
                  'total_items', 'total_value', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'total_items',
                            'total_value', 'created_at', 'updated_at')

    def get_total_items(self, obj):
        """Get total number of items in wishlist."""
        return obj.total_items

    def get_total_value(self, obj):
        """Get total value of wishlist."""
        return obj.total_value


class WishlistCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating wishlists."""

    class Meta:
        model = Wishlist
        fields = ('name', 'is_public')

    def create(self, validated_data):
        """Create a new wishlist."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class WishlistUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating wishlists."""

    class Meta:
        model = Wishlist
        fields = ('name', 'is_public')


class WishlistShareSerializer(serializers.ModelSerializer):
    """Serializer for wishlist shares."""

    wishlist = WishlistSerializer(read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = WishlistShare
        fields = ('id', 'wishlist', 'shared_by', 'shared_with_email', 'share_token',
                  'is_active', 'is_expired', 'expires_at', 'created_at')
        read_only_fields = ('id', 'shared_by', 'share_token', 'created_at')

    def get_is_expired(self, obj):
        """Check if share is expired."""
        return obj.is_expired


class WishlistShareCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating wishlist shares."""

    class Meta:
        model = WishlistShare
        fields = ('wishlist', 'shared_with_email', 'expires_at')

    def validate(self, attrs):
        """Validate share data."""
        wishlist = attrs['wishlist']
        user = self.context['request'].user

        # Ensure user owns the wishlist
        if wishlist.user != user:
            raise serializers.ValidationError(
                'You can only share your own wishlists.')

        return attrs

    def create(self, validated_data):
        """Create a new wishlist share."""
        import secrets

        validated_data['shared_by'] = self.context['request'].user
        validated_data['share_token'] = secrets.token_urlsafe(32)
        return super().create(validated_data)


class WishlistShareViewSerializer(serializers.ModelSerializer):
    """Serializer for viewing shared wishlists."""

    wishlist = WishlistSerializer(read_only=True)
    shared_by_name = serializers.SerializerMethodField()

    class Meta:
        model = WishlistShare
        fields = ('id', 'wishlist', 'shared_by_name',
                  'shared_with_email', 'created_at')
        read_only_fields = ('id', 'shared_by_name',
                            'shared_with_email', 'created_at')

    def get_shared_by_name(self, obj):
        """Get name of user who shared the wishlist."""
        return f"{obj.shared_by.first_name} {obj.shared_by.last_name}".strip() or obj.shared_by.username


class PriceAlertSerializer(serializers.ModelSerializer):
    """Serializer for price alerts."""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PriceAlert
        fields = ('id', 'user', 'product', 'product_id', 'alert_type', 'target_price',
                  'percentage_drop', 'is_active', 'triggered', 'triggered_at', 'created_at')
        read_only_fields = ('id', 'user', 'product',
                            'triggered', 'triggered_at', 'created_at')

    def validate(self, attrs):
        """Validate price alert data."""
        from products.models import Product

        product_id = attrs['product_id']
        alert_type = attrs['alert_type']
        target_price = attrs.get('target_price')
        percentage_drop = attrs.get('percentage_drop')

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Product not found.')

        # Validate alert type specific fields
        if alert_type == 'below_price' and not target_price:
            raise serializers.ValidationError(
                'Target price is required for below price alerts.')
        elif alert_type == 'percentage_drop' and not percentage_drop:
            raise serializers.ValidationError(
                'Percentage drop is required for percentage drop alerts.')
        elif alert_type == 'percentage_drop' and (percentage_drop <= 0 or percentage_drop > 100):
            raise serializers.ValidationError(
                'Percentage drop must be between 1 and 100.')

        # Check if user already has an alert for this product
        user = self.context['request'].user
        if PriceAlert.objects.filter(user=user, product=product, alert_type=alert_type, is_active=True).exists():
            raise serializers.ValidationError(
                'You already have an active alert for this product.')

        attrs['product'] = product
        return attrs

    def create(self, validated_data):
        """Create a new price alert."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PriceAlertUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating price alerts."""

    class Meta:
        model = PriceAlert
        fields = ('target_price', 'percentage_drop', 'is_active')

    def validate(self, attrs):
        """Validate price alert update."""
        alert_type = self.instance.alert_type

        if alert_type == 'below_price' and 'target_price' in attrs and not attrs['target_price']:
            raise serializers.ValidationError(
                'Target price is required for below price alerts.')
        elif alert_type == 'percentage_drop' and 'percentage_drop' in attrs:
            percentage_drop = attrs['percentage_drop']
            if percentage_drop <= 0 or percentage_drop > 100:
                raise serializers.ValidationError(
                    'Percentage drop must be between 1 and 100.')

        return attrs


class WishlistAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for wishlist analytics."""

    product = ProductListSerializer(read_only=True)

    class Meta:
        model = WishlistAnalytics
        fields = ('id', 'product', 'times_added', 'times_removed', 'current_wishlist_count',
                  'last_added', 'last_removed', 'created_at', 'updated_at')
        read_only_fields = ('id', 'times_added', 'times_removed', 'current_wishlist_count',
                            'last_added', 'last_removed', 'created_at', 'updated_at')


class WishlistSummarySerializer(serializers.ModelSerializer):
    """Serializer for wishlist summary."""

    total_items = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ('id', 'name', 'total_items', 'total_value')
        read_only_fields = ('id', 'total_items', 'total_value')

    def get_total_items(self, obj):
        """Get total number of items in wishlist."""
        return obj.total_items

    def get_total_value(self, obj):
        """Get total value of wishlist."""
        return obj.total_value


class WishlistToCartSerializer(serializers.Serializer):
    """Serializer for moving items from wishlist to cart."""

    item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )

    def validate_item_ids(self, value):
        """Validate item IDs."""
        user = self.context['request'].user
        wishlist = Wishlist.objects.filter(user=user).first()

        if not wishlist:
            raise serializers.ValidationError('No wishlist found.')

        # Check if all items belong to user's wishlist
        valid_items = WishlistItem.objects.filter(
            wishlist=wishlist,
            id__in=value
        ).values_list('id', flat=True)

        invalid_items = set(value) - set(valid_items)
        if invalid_items:
            raise serializers.ValidationError(
                f'Invalid item IDs: {invalid_items}')

        return value
