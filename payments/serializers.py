from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Payment, Refund, PaymentMethod, WebhookEvent, Subscription

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments."""

    class Meta:
        model = Payment
        fields = ('id', 'order', 'user', 'amount', 'currency', 'payment_method', 'status',
                  'stripe_payment_intent_id', 'stripe_charge_id', 'stripe_customer_id',
                  'error_message', 'error_code', 'metadata', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'stripe_payment_intent_id', 'stripe_charge_id',
                            'stripe_customer_id', 'error_message', 'error_code', 'created_at', 'updated_at')


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments."""

    class Meta:
        model = Payment
        fields = ('order', 'amount', 'currency', 'payment_method')

    def validate(self, attrs):
        """Validate payment data."""
        order = attrs['order']
        amount = attrs['amount']

        # Ensure payment amount matches order total
        if amount != order.total_amount:
            raise serializers.ValidationError(
                'Payment amount must match order total.')

        # Ensure order belongs to current user
        user = self.context['request'].user
        if order.user != user:
            raise serializers.ValidationError(
                'You can only create payments for your own orders.')

        return attrs

    def create(self, validated_data):
        """Create a new payment."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating Stripe payment intents."""

    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default='usd', max_length=3)
    order_id = serializers.IntegerField()
    payment_method_types = serializers.ListField(
        child=serializers.CharField(),
        default=['card']
    )

    def validate_amount(self, value):
        """Validate amount."""
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value

    def validate_order_id(self, value):
        """Validate order exists and belongs to user."""
        from orders.models import Order

        try:
            order = Order.objects.get(
                id=value, user=self.context['request'].user)
        except Order.DoesNotExist:
            raise serializers.ValidationError('Order not found.')

        return value


class PaymentConfirmSerializer(serializers.Serializer):
    """Serializer for confirming payments."""

    payment_intent_id = serializers.CharField()
    order_id = serializers.IntegerField()

    def validate_payment_intent_id(self, value):
        """Validate payment intent ID."""
        if not value:
            raise serializers.ValidationError('Payment intent ID is required.')
        return value

    def validate_order_id(self, value):
        """Validate order exists and belongs to user."""
        from orders.models import Order

        try:
            order = Order.objects.get(
                id=value, user=self.context['request'].user)
        except Order.DoesNotExist:
            raise serializers.ValidationError('Order not found.')

        return value


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds."""

    class Meta:
        model = Refund
        fields = ('id', 'payment', 'amount', 'currency', 'reason', 'status',
                  'stripe_refund_id', 'metadata', 'created_at', 'updated_at')
        read_only_fields = ('id', 'stripe_refund_id',
                            'created_at', 'updated_at')


class RefundCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating refunds."""

    class Meta:
        model = Refund
        fields = ('payment', 'amount', 'reason')

    def validate(self, attrs):
        """Validate refund data."""
        payment = attrs['payment']
        amount = attrs['amount']

        # Ensure refund amount doesn't exceed payment amount
        if amount > payment.amount:
            raise serializers.ValidationError(
                'Refund amount cannot exceed payment amount.')

        # Ensure payment belongs to current user
        user = self.context['request'].user
        if payment.user != user:
            raise serializers.ValidationError(
                'You can only create refunds for your own payments.')

        return attrs


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods."""

    display_info = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = ('id', 'user', 'type', 'is_default', 'stripe_payment_method_id',
                  'last4', 'brand', 'exp_month', 'exp_year', 'bank_name', 'account_last4',
                  'display_info', 'metadata', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'stripe_payment_method_id', 'last4', 'brand',
                            'exp_month', 'exp_year', 'bank_name', 'account_last4', 'created_at', 'updated_at')

    def get_display_info(self, obj):
        """Get display information for payment method."""
        if obj.type == 'card':
            return f"{obj.brand.title()} ****{obj.last4}"
        elif obj.type == 'bank_account':
            return f"{obj.bank_name} ****{obj.account_last4}"
        return obj.get_type_display()


class PaymentMethodCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment methods."""

    payment_method_id = serializers.CharField(write_only=True)

    class Meta:
        model = PaymentMethod
        fields = ('type', 'payment_method_id', 'is_default')

    def create(self, validated_data):
        """Create a new payment method."""
        validated_data['user'] = self.context['request'].user
        validated_data['stripe_payment_method_id'] = validated_data.pop(
            'payment_method_id')
        return super().create(validated_data)


class WebhookEventSerializer(serializers.ModelSerializer):
    """Serializer for webhook events."""

    class Meta:
        model = WebhookEvent
        fields = ('id', 'stripe_event_id', 'event_type', 'api_version', 'created',
                  'livemode', 'data', 'processed', 'processed_at', 'processing_error', 'created_at')
        read_only_fields = ('id', 'stripe_event_id', 'event_type', 'api_version', 'created',
                            'livemode', 'data', 'processed', 'processed_at', 'processing_error', 'created_at')


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions."""

    class Meta:
        model = Subscription
        fields = ('id', 'user', 'stripe_subscription_id', 'stripe_customer_id', 'status',
                  'current_period_start', 'current_period_end', 'cancel_at_period_end', 'canceled_at',
                  'amount', 'currency', 'interval', 'interval_count', 'metadata', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'stripe_subscription_id', 'stripe_customer_id',
                            'current_period_start', 'current_period_end', 'canceled_at', 'created_at', 'updated_at')


class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for payment status updates."""

    payment_intent_id = serializers.CharField()
    status = serializers.CharField()
    order_id = serializers.IntegerField()

    def validate_status(self, value):
        """Validate payment status."""
        valid_statuses = ['succeeded', 'processing',
                          'requires_payment_method', 'canceled', 'failed']
        if value not in valid_statuses:
            raise serializers.ValidationError('Invalid payment status.')
        return value


class PaymentMethodAttachSerializer(serializers.Serializer):
    """Serializer for attaching payment methods to customers."""

    payment_method_id = serializers.CharField()
    customer_id = serializers.CharField()

    def validate_payment_method_id(self, value):
        """Validate payment method ID."""
        if not value:
            raise serializers.ValidationError('Payment method ID is required.')
        return value

    def validate_customer_id(self, value):
        """Validate customer ID."""
        if not value:
            raise serializers.ValidationError('Customer ID is required.')
        return value


class PaymentMethodDetachSerializer(serializers.Serializer):
    """Serializer for detaching payment methods from customers."""

    payment_method_id = serializers.CharField()

    def validate_payment_method_id(self, value):
        """Validate payment method ID."""
        if not value:
            raise serializers.ValidationError('Payment method ID is required.')
        return value
