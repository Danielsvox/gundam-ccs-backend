from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()


class Payment(models.Model):
    """Payment records."""

    PAYMENT_METHODS = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('manual', 'Manual'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payments')

    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, default='stripe')
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Stripe specific fields
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=100, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.order.order_number} - ${self.amount}"

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']


class Refund(models.Model):
    """Payment refunds."""

    REFUND_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    REFUND_REASONS = [
        ('duplicate', 'Duplicate'),
        ('fraudulent', 'Fraudulent'),
        ('requested_by_customer', 'Requested by Customer'),
        ('expired_uncaptured', 'Expired Uncaptured'),
    ]

    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    reason = models.CharField(
        max_length=30, choices=REFUND_REASONS, blank=True)
    status = models.CharField(
        max_length=20, choices=REFUND_STATUS_CHOICES, default='pending')

    # Stripe specific fields
    stripe_refund_id = models.CharField(max_length=255, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refund {self.id} - {self.payment} - ${self.amount}"

    class Meta:
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
        ordering = ['-created_at']


class PaymentMethod(models.Model):
    """Stored payment methods for users."""

    PAYMENT_METHOD_TYPES = [
        ('card', 'Credit/Debit Card'),
        ('bank_account', 'Bank Account'),
        ('paypal', 'PayPal'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_TYPES, default='card')
    is_default = models.BooleanField(default=False)

    # Stripe specific fields
    stripe_payment_method_id = models.CharField(max_length=255, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True)

    # Card details (masked)
    last4 = models.CharField(max_length=4, blank=True)
    # visa, mastercard, etc.
    brand = models.CharField(max_length=20, blank=True)
    exp_month = models.PositiveIntegerField(blank=True, null=True)
    exp_year = models.PositiveIntegerField(blank=True, null=True)

    # Bank account details (masked)
    bank_name = models.CharField(max_length=100, blank=True)
    account_last4 = models.CharField(max_length=4, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set all other payment methods of this user to not default
            PaymentMethod.objects.filter(
                user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.type == 'card':
            return f"{self.brand.title()} ****{self.last4}"
        elif self.type == 'bank_account':
            return f"{self.bank_name} ****{self.account_last4}"
        return f"{self.get_type_display()} - {self.user.email}"

    class Meta:
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['-is_default', '-created_at']


class WebhookEvent(models.Model):
    """Stripe webhook events."""

    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    api_version = models.CharField(max_length=20, blank=True)
    created = models.DateTimeField()
    livemode = models.BooleanField(default=False)

    # Event data
    data = models.JSONField()

    # Processing status
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"

    class Meta:
        verbose_name = 'Webhook Event'
        verbose_name_plural = 'Webhook Events'
        ordering = ['-created_at']


class Subscription(models.Model):
    """Subscription models for recurring payments (future feature)."""

    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
        ('unpaid', 'Unpaid'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='subscriptions')
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='incomplete')

    # Billing details
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(blank=True, null=True)

    # Pricing
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    interval = models.CharField(max_length=20)  # month, year, etc.
    interval_count = models.PositiveIntegerField(default=1)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Subscription {self.stripe_subscription_id} - {self.user.email}"

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-created_at']
