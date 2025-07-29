from rest_framework import serializers
from .models import (
    Payment, PaymentMethod, Refund, WebhookEvent, ExchangeRateLog, ExchangeRateAlert, ExchangeRateSnapshot,
    PagoMovilBankCode, PagoMovilRecipient, PagoMovilVerificationRequest
)


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records."""

    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    order_number = serializers.CharField(
        source='order.order_number', read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id', 'order', 'order_number', 'user', 'amount', 'currency',
            'payment_method', 'payment_method_display', 'status', 'status_display',
            'stripe_payment_intent_id', 'stripe_charge_id', 'error_message',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'order', 'user', 'stripe_payment_intent_id', 'stripe_charge_id',
            'error_message', 'created_at', 'updated_at'
        )


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods."""

    type_display = serializers.CharField(
        source='get_type_display', read_only=True)
    brand_display = serializers.CharField(source='brand', read_only=True)

    class Meta:
        model = PaymentMethod
        fields = (
            'id', 'user', 'type', 'type_display', 'is_default',
            'stripe_payment_method_id', 'last4', 'brand', 'brand_display',
            'exp_month', 'exp_year', 'bank_name', 'account_last4',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'user', 'stripe_payment_method_id', 'last4', 'brand',
            'exp_month', 'exp_year', 'bank_name', 'account_last4',
            'created_at', 'updated_at'
        )


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating payment intents."""

    order_id = serializers.IntegerField()

    def validate_order_id(self, value):
        """Validate that the order exists and belongs to the user."""
        from orders.models import Order
        request = self.context.get('request')

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated.")

        try:
            order = Order.objects.get(id=value, user=request.user)
            if order.payment_status == 'paid':
                raise serializers.ValidationError(
                    "Order has already been paid.")
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")

        return value


class ConfirmPaymentSerializer(serializers.Serializer):
    """Serializer for confirming payments."""

    payment_intent_id = serializers.CharField(max_length=255)

    def validate_payment_intent_id(self, value):
        """Validate that the payment intent exists and belongs to the user."""
        request = self.context.get('request')

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated.")

        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=value,
                user=request.user
            )
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment intent not found.")

        return value


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout data."""

    shipping_address = serializers.DictField()
    billing_address = serializers.DictField(required=False)
    customer_notes = serializers.CharField(
        max_length=1000, required=False, allow_blank=True)
    shipping_method_id = serializers.IntegerField(required=False)

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


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds."""

    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    reason_display = serializers.CharField(
        source='get_reason_display', read_only=True)
    payment_order_number = serializers.CharField(
        source='payment.order.order_number', read_only=True)

    class Meta:
        model = Refund
        fields = (
            'id', 'payment', 'payment_order_number', 'amount', 'currency',
            'reason', 'reason_display', 'status', 'status_display',
            'stripe_refund_id', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'payment', 'stripe_refund_id', 'created_at', 'updated_at'
        )


class WebhookEventSerializer(serializers.ModelSerializer):
    """Serializer for webhook events."""

    class Meta:
        model = WebhookEvent
        fields = (
            'id', 'stripe_event_id', 'event_type', 'api_version',
            'created', 'livemode', 'processed', 'processing_error',
            'created_at', 'processed_at'
        )
        read_only_fields = '__all__'


class PaymentSummarySerializer(serializers.ModelSerializer):
    """Serializer for payment summary."""

    order_number = serializers.CharField(
        source='order.order_number', read_only=True)
    customer_name = serializers.CharField(
        source='order.user.get_full_name', read_only=True)
    customer_email = serializers.CharField(
        source='order.user.email', read_only=True)
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id', 'order_number', 'customer_name', 'customer_email',
            'amount', 'currency', 'payment_method', 'payment_method_display',
            'status', 'status_display', 'created_at'
        )
        read_only_fields = '__all__'


class CreateRefundSerializer(serializers.Serializer):
    """Serializer for creating refunds."""

    payment_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.ChoiceField(
        choices=Refund.REFUND_REASONS, required=False)

    def validate_payment_id(self, value):
        """Validate that the payment exists."""
        try:
            payment = Payment.objects.get(id=value)
            if payment.status != 'succeeded':
                raise serializers.ValidationError(
                    "Payment must be successful to refund.")
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found.")

        return value

    def validate_amount(self, value):
        """Validate refund amount."""
        payment_id = self.initial_data.get('payment_id')
        if payment_id:
            try:
                payment = Payment.objects.get(id=payment_id)
                if value > payment.amount:
                    raise serializers.ValidationError(
                        "Refund amount cannot exceed payment amount.")
            except Payment.DoesNotExist:
                pass

        return value


class PaymentMethodCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payment methods with Stripe."""

    payment_method_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = PaymentMethod
        fields = ('type', 'payment_method_id', 'is_default')

    def create(self, validated_data):
        """Create payment method with Stripe integration."""
        import stripe
        from django.conf import settings

        stripe.api_key = settings.STRIPE_SECRET_KEY

        payment_method_id = validated_data.pop('payment_method_id')
        user = self.context['request'].user

        try:
            # Attach payment method to customer
            customer_id = getattr(user, 'stripe_customer_id', None)
            if not customer_id:
                # Create customer if doesn't exist
                customer = stripe.Customer.create(
                    email=user.email,
                    name=user.get_full_name() or user.email
                )
                user.stripe_customer_id = customer.id
                user.save()
                customer_id = customer.id

            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )

            # Get payment method details
            pm = stripe.PaymentMethod.retrieve(payment_method_id)

            # Create local payment method record
            payment_method = PaymentMethod.objects.create(
                user=user,
                stripe_payment_method_id=payment_method_id,
                stripe_customer_id=customer_id,
                type=validated_data.get('type', 'card'),
                is_default=validated_data.get('is_default', False),
                last4=pm.card.last4 if pm.card else '',
                brand=pm.card.brand if pm.card else '',
                exp_month=pm.card.exp_month if pm.card else None,
                exp_year=pm.card.exp_year if pm.card else None,
                bank_name=pm.ideal.bank if hasattr(
                    pm, 'ideal') and pm.ideal else '',
                account_last4=pm.ideal.bank if hasattr(
                    pm, 'ideal') and pm.ideal else ''
            )

            return payment_method

        except stripe.error.StripeError as e:
            raise serializers.ValidationError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise serializers.ValidationError(
                f"Error creating payment method: {str(e)}")


class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializer for exchange rate information."""
    
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = ExchangeRateLog
        fields = (
            'id', 'usd_to_ves', 'source', 'source_display', 'timestamp',
            'is_active', 'fetch_success', 'change_percentage'
        )
        read_only_fields = '__all__'


class ExchangeRateCurrentSerializer(serializers.Serializer):
    """Serializer for current exchange rate response."""
    
    usd_to_ves = serializers.DecimalField(max_digits=10, decimal_places=4)
    last_updated = serializers.DateTimeField()
    source = serializers.CharField()
    change_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)


class ExchangeRateHistorySerializer(serializers.ModelSerializer):
    """Serializer for exchange rate history."""
    
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = ExchangeRateLog
        fields = (
            'id', 'usd_to_ves', 'source', 'source_display', 'timestamp',
            'change_percentage', 'fetch_success', 'error_message'
        )
        read_only_fields = '__all__'


class ManualRateSetSerializer(serializers.Serializer):
    """Serializer for setting manual exchange rate."""
    
    rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        min_value=1,
        max_value=100000,
        help_text="Exchange rate in VES per USD"
    )
    
    def validate_rate(self, value):
        """Validate the exchange rate value."""
        if value <= 0:
            raise serializers.ValidationError("Exchange rate must be positive")
        
        # Sanity check - warn if rate seems too high or low
        if value < 10:
            raise serializers.ValidationError("Exchange rate seems too low. Please verify.")
        if value > 100:
            # Just log a warning for very high rates
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Very high exchange rate set: {value} VES per USD")
        
        return value


class CurrencyConversionSerializer(serializers.Serializer):
    """Serializer for currency conversion requests."""
    
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    from_currency = serializers.ChoiceField(choices=['USD', 'VES'])
    to_currency = serializers.ChoiceField(choices=['USD', 'VES'])
    rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        help_text="Optional: specific rate to use for conversion"
    )
    
    def validate(self, data):
        """Validate conversion request."""
        if data['from_currency'] == data['to_currency']:
            raise serializers.ValidationError("From and to currencies must be different")
        return data


class CurrencyConversionResponseSerializer(serializers.Serializer):
    """Serializer for currency conversion response."""
    
    original_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    converted_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    from_currency = serializers.CharField()
    to_currency = serializers.CharField()
    exchange_rate = serializers.DecimalField(max_digits=10, decimal_places=4)
    rate_source = serializers.CharField()
    conversion_timestamp = serializers.DateTimeField()


class ExchangeRateAlertSerializer(serializers.ModelSerializer):
    """Serializer for exchange rate alerts."""
    
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    exchange_rate_details = ExchangeRateSerializer(source='exchange_rate', read_only=True)
    acknowledged_by_email = serializers.CharField(source='acknowledged_by.email', read_only=True)
    
    class Meta:
        model = ExchangeRateAlert
        fields = (
            'id', 'alert_type', 'alert_type_display', 'exchange_rate_details',
            'threshold_value', 'message', 'acknowledged', 'acknowledged_by_email',
            'acknowledged_at', 'created_at'
        )
        read_only_fields = (
            'id', 'alert_type', 'exchange_rate_details', 'threshold_value',
            'message', 'acknowledged_by_email', 'acknowledged_at', 'created_at'
        )


class ExchangeRateSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for exchange rate snapshots used in orders/payments."""
    
    class Meta:
        model = ExchangeRateSnapshot
        fields = (
            'id', 'usd_to_ves', 'amount_usd', 'amount_ves', 'snapshot_timestamp'
        )
        read_only_fields = '__all__'


class PagoMovilBankCodeSerializer(serializers.ModelSerializer):
    """Serializer for Pago Móvil bank codes."""
    
    class Meta:
        model = PagoMovilBankCode
        fields = ('id', 'bank_code', 'bank_name', 'is_active')
        read_only_fields = ('id',)


class PagoMovilRecipientSerializer(serializers.ModelSerializer):
    """Serializer for Pago Móvil recipients."""
    
    bank_code_info = PagoMovilBankCodeSerializer(source='bank_code', read_only=True)
    
    class Meta:
        model = PagoMovilRecipient
        fields = (
            'id', 'bank_code', 'bank_code_info', 'recipient_id', 
            'recipient_phone', 'recipient_name', 'is_active'
        )
        read_only_fields = ('id',)


class PagoMovilVerificationRequestSerializer(serializers.ModelSerializer):
    """Serializer for Pago Móvil verification requests."""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    bank_code_info = PagoMovilBankCodeSerializer(source='bank_code', read_only=True)
    recipient_info = PagoMovilRecipientSerializer(source='recipient', read_only=True)
    formatted_amount = serializers.CharField(read_only=True)
    formatted_usd_equivalent = serializers.CharField(read_only=True)
    approved_by_email = serializers.CharField(source='approved_by.email', read_only=True)
    
    class Meta:
        model = PagoMovilVerificationRequest
        fields = (
            'id', 'user', 'user_email', 'order', 'sender_id', 'sender_phone',
            'bank_code', 'bank_code_info', 'recipient', 'recipient_info',
            'amount_ves', 'exchange_rate_used', 'usd_equivalent',
            'formatted_amount', 'formatted_usd_equivalent',
            'status', 'notes', 'approved_by', 'approved_by_email',
            'approved_at', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'user_email', 'bank_code_info', 'recipient_info',
            'formatted_amount', 'formatted_usd_equivalent',
            'approved_by', 'approved_by_email', 'approved_at',
            'created_at', 'updated_at'
        )
    
    def validate_sender_id(self, value):
        """Validate sender ID format."""
        import re
        
        # Remove spaces and convert to uppercase
        value = value.replace(' ', '').upper()
        
        # Check format: V-12345678 or J-12345678-0
        pattern = r'^[VJPE][-]\d{8}([-]\d)?$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Sender ID must be in format V-12345678 or J-12345678-0"
            )
        
        return value
    
    def validate_sender_phone(self, value):
        """Validate sender phone number."""
        import re
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', value)
        
        # Venezuelan phone numbers should be 10-11 digits
        if len(digits_only) < 10 or len(digits_only) > 11:
            raise serializers.ValidationError(
                "Phone number must be 10-11 digits"
            )
        
        return value
    
    def validate(self, data):
        """Additional validation for the request."""
        # Check rate limiting (max 3 submissions per hour per user)
        user = data.get('user')
        if user:
            from django.utils import timezone
            from datetime import timedelta
            
            recent_requests = PagoMovilVerificationRequest.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_requests >= 3:
                raise serializers.ValidationError(
                    "Maximum 3 verification requests per hour allowed"
                )
        
        return data


class PagoMovilVerificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Pago Móvil verification requests."""
    
    class Meta:
        model = PagoMovilVerificationRequest
        fields = (
            'order', 'sender_id', 'sender_phone', 'bank_code', 
            'recipient', 'amount_ves'
        )
    
    def validate_sender_id(self, value):
        """Validate sender ID format."""
        import re
        
        # Remove spaces and convert to uppercase
        value = value.replace(' ', '').upper()
        
        # Check format: V-12345678 or J-12345678-0
        pattern = r'^[VJPE][-]\d{8}([-]\d)?$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Sender ID must be in format V-12345678 or J-12345678-0"
            )
        
        return value
    
    def validate_sender_phone(self, value):
        """Validate sender phone number."""
        import re
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', value)
        
        # Venezuelan phone numbers should be 10-11 digits
        if len(digits_only) < 10 or len(digits_only) > 11:
            raise serializers.ValidationError(
                "Phone number must be 10-11 digits"
            )
        
        return value
    
    def validate(self, data):
        """Additional validation for the request."""
        # Check rate limiting (max 3 submissions per hour per user)
        user = self.context['request'].user
        from django.utils import timezone
        from datetime import timedelta
        
        recent_requests = PagoMovilVerificationRequest.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        if recent_requests >= 3:
            raise serializers.ValidationError(
                "Maximum 3 verification requests per hour allowed"
            )
        
        return data


class PagoMovilStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating Pago Móvil verification status."""
    
    status = serializers.ChoiceField(choices=[
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ])
    notes = serializers.CharField(required=False, allow_blank=True)


class PagoMovilPaymentInfoSerializer(serializers.Serializer):
    """Serializer for Pago Móvil payment information."""
    
    bank_codes = PagoMovilBankCodeSerializer(many=True)
    recipients = PagoMovilRecipientSerializer(many=True)
    current_exchange_rate = serializers.DecimalField(max_digits=10, decimal_places=4)
    instructions = serializers.CharField()
