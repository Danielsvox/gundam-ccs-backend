from rest_framework import serializers
from django.contrib.auth import get_user_model
from products.serializers import ProductListSerializer
from cart.serializers import CartCouponSerializer
from .models import Order, OrderItem, OrderStatusHistory, ShippingMethod, TaxRate

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items."""

    product = ProductListSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'product_sku',
                  'quantity', 'unit_price', 'total_price')
        read_only_fields = ('id', 'product_name', 'product_sku', 'total_price')

    def get_total_price(self, obj):
        """Calculate total price for this item."""
        return obj.total_price


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for order status history."""

    class Meta:
        model = OrderStatusHistory
        fields = ('id', 'status', 'notes', 'created_at')
        read_only_fields = ('id', 'created_at')


class ShippingMethodSerializer(serializers.ModelSerializer):
    """Serializer for shipping methods."""

    class Meta:
        model = ShippingMethod
        fields = ('id', 'name', 'description', 'price',
                  'estimated_days', 'is_active')
        read_only_fields = ('id',)


class TaxRateSerializer(serializers.ModelSerializer):
    """Serializer for tax rates."""

    rate_percentage = serializers.SerializerMethodField()

    class Meta:
        model = TaxRate
        fields = ('id', 'country', 'state', 'city', 'postal_code',
                  'rate', 'rate_percentage', 'is_active')
        read_only_fields = ('id',)

    def get_rate_percentage(self, obj):
        """Get rate as percentage."""
        return obj.rate * 100


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for listing orders."""

    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'order_number', 'status', 'payment_status',
                  'total_amount', 'total_items', 'created_at')
        read_only_fields = ('id', 'order_number',
                            'total_amount', 'total_items', 'created_at')

    def get_total_items(self, obj):
        """Get total number of items in order."""
        return obj.total_items


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order details."""

    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    applied_coupon = CartCouponSerializer(read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'order_number', 'status', 'payment_status', 'subtotal', 'tax_amount',
                  'shipping_amount', 'discount_amount', 'total_amount', 'shipping_address',
                  'billing_address', 'payment_intent_id', 'payment_method', 'applied_coupon',
                  'tracking_number', 'tracking_url', 'shipped_at', 'delivered_at', 'customer_notes',
                  'admin_notes', 'items', 'status_history', 'total_items', 'created_at', 'updated_at')
        read_only_fields = ('id', 'order_number', 'subtotal', 'tax_amount', 'shipping_amount',
                            'discount_amount', 'total_amount', 'total_items', 'created_at', 'updated_at')

    def get_total_items(self, obj):
        """Get total number of items in order."""
        return obj.total_items


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders."""

    shipping_address = serializers.JSONField()
    billing_address = serializers.JSONField(required=False)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Order
        fields = ('shipping_address', 'billing_address',
                  'customer_notes', 'coupon_code')

    def validate_shipping_address(self, value):
        """Validate shipping address."""
        required_fields = ['name', 'line1', 'city',
                           'state', 'postal_code', 'country']
        for field in required_fields:
            if not value.get(field):
                raise serializers.ValidationError(
                    f"Shipping address {field} is required.")
        return value

    def validate_billing_address(self, value):
        """Validate billing address if provided."""
        if value:
            required_fields = ['name', 'line1', 'city',
                               'state', 'postal_code', 'country']
            for field in required_fields:
                if not value.get(field):
                    raise serializers.ValidationError(
                        f"Billing address {field} is required.")
        return value


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders."""

    class Meta:
        model = Order
        fields = ('customer_notes',)

    def validate(self, attrs):
        """Validate order update."""
        # Only allow updating customer notes
        return attrs


class OrderCancelSerializer(serializers.Serializer):
    """Serializer for cancelling orders."""

    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate cancellation."""
        order = self.context['order']
        if not order.can_cancel():
            raise serializers.ValidationError(
                'This order cannot be cancelled.')
        return attrs


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status (admin only)."""

    class Meta:
        model = Order
        fields = ('status', 'admin_notes')

    def validate_status(self, value):
        """Validate status change."""
        order = self.instance
        current_status = order.status

        # Define allowed status transitions
        allowed_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered'],
            'delivered': [],
            'cancelled': [],
            'refunded': [],
        }

        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f'Cannot change status from {current_status} to {value}.')

        return value


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for order tracking information."""

    class Meta:
        model = Order
        fields = ('order_number', 'status', 'tracking_number',
                  'tracking_url', 'shipped_at', 'delivered_at')
        read_only_fields = ('order_number', 'status',
                            'shipped_at', 'delivered_at')


class OrderSummarySerializer(serializers.ModelSerializer):
    """Serializer for order summary."""

    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('order_number', 'status', 'total_amount',
                  'total_items', 'created_at')
        read_only_fields = ('order_number', 'total_amount',
                            'total_items', 'created_at')

    def get_total_items(self, obj):
        """Get total number of items in order."""
        return obj.total_items


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout process."""

    shipping_address = serializers.JSONField()
    billing_address = serializers.JSONField(required=False)
    shipping_method_id = serializers.IntegerField()
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_shipping_address(self, value):
        """Validate shipping address."""
        required_fields = ['first_name', 'last_name', 'address_line_1',
                           'city', 'state', 'postal_code', 'country', 'phone']
        for field in required_fields:
            if not value.get(field):
                raise serializers.ValidationError(
                    f'{field.replace("_", " ").title()} is required.')
        return value

    def validate_billing_address(self, value):
        """Validate billing address."""
        if value:
            required_fields = ['first_name', 'last_name', 'address_line_1',
                               'city', 'state', 'postal_code', 'country', 'phone']
            for field in required_fields:
                if not value.get(field):
                    raise serializers.ValidationError(
                        f'{field.replace("_", " ").title()} is required.')
        return value

    def validate_shipping_method_id(self, value):
        """Validate shipping method."""
        try:
            shipping_method = ShippingMethod.objects.get(
                id=value, is_active=True)
        except ShippingMethod.DoesNotExist:
            raise serializers.ValidationError('Invalid shipping method.')
        return value
