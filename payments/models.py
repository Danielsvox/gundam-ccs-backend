from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order
from django.utils import timezone

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


class ExchangeRateLog(models.Model):
    """Store historical exchange rates for USD to VES conversion."""

    RATE_SOURCES = [
        ('google_finance', 'Google Finance'),
        ('exchangerate_host', 'Exchangerate.host'),
        ('open_exchange_rates', 'Open Exchange Rates'),
        ('manual', 'Manual Override'),
        ('fallback', 'Fallback Source')
    ]

    usd_to_ves = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Exchange rate from USD to VES (Bolívares)"
    )
    source = models.CharField(
        max_length=50,
        choices=RATE_SOURCES,
        default='google_finance'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this is the current active rate"
    )
    fetch_success = models.BooleanField(
        default=True,
        help_text="Whether the rate was successfully fetched"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if fetch failed"
    )
    change_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage change from previous rate"
    )

    class Meta:
        verbose_name = 'Exchange Rate Log'
        verbose_name_plural = 'Exchange Rate Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'is_active']),
            models.Index(fields=['source', 'timestamp']),
        ]

    def __str__(self):
        return f"USD→VES: {self.usd_to_ves} ({self.source}) - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_current_rate(cls):
        """Get the current active exchange rate."""
        try:
            return cls.objects.filter(is_active=True, fetch_success=True).latest('timestamp')
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_rate_at_timestamp(cls, timestamp):
        """Get the exchange rate that was active at a specific timestamp."""
        try:
            return cls.objects.filter(
                timestamp__lte=timestamp,
                fetch_success=True
            ).latest('timestamp')
        except cls.DoesNotExist:
            return None

    def save(self, *args, **kwargs):
        """Override save to calculate change percentage and manage active status."""
        # Save first to ensure timestamp is set
        super().save(*args, **kwargs)
        
        if self.fetch_success:
            # Calculate change percentage from previous rate
            previous_rate = ExchangeRateLog.objects.filter(
                fetch_success=True,
                timestamp__lt=self.timestamp
            ).exclude(id=self.id).order_by('-timestamp').first()

            if previous_rate:
                change = ((self.usd_to_ves - previous_rate.usd_to_ves) / previous_rate.usd_to_ves) * 100
                self.change_percentage = round(change, 2)
                # Save again to update change_percentage
                super().save(update_fields=['change_percentage'])

            # If this is a successful rate, deactivate all other active rates
            if self.is_active:
                ExchangeRateLog.objects.filter(is_active=True).exclude(id=self.id).update(is_active=False)


class ExchangeRateAlert(models.Model):
    """Store alerts for significant exchange rate changes."""

    ALERT_TYPES = [
        ('high_change', 'High Percentage Change'),
        ('fetch_error', 'Fetch Error'),
        ('manual_override', 'Manual Override'),
        ('source_fallback', 'Source Fallback')
    ]

    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    exchange_rate = models.ForeignKey(
        ExchangeRateLog,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    threshold_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Threshold value that triggered the alert"
    )
    message = models.TextField()
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Exchange Rate Alert'
        verbose_name_plural = 'Exchange Rate Alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# Add exchange rate field to existing models for historical tracking
class ExchangeRateSnapshot(models.Model):
    """Snapshot of exchange rate used in orders/payments for historical reference."""

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='exchange_rate_snapshot'
    )
    payment = models.OneToOneField(
        'Payment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='exchange_rate_snapshot'
    )
    usd_to_ves = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Exchange rate at the time of order/payment"
    )
    amount_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount in USD"
    )
    amount_ves = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Equivalent amount in VES"
    )
    snapshot_timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Exchange Rate Snapshot'
        verbose_name_plural = 'Exchange Rate Snapshots'

    def __str__(self):
        entity = self.order or self.payment
        entity_type = "Order" if self.order else "Payment"
        return f"{entity_type} {entity.id if entity else 'N/A'} - ${self.amount_usd} = Bs. {self.amount_ves}"


class PagoMovilBankCode(models.Model):
    """Store valid Venezuelan bank codes for Pago Móvil."""
    
    bank_code = models.CharField(max_length=10, unique=True)
    bank_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Pago Móvil Bank Code'
        verbose_name_plural = 'Pago Móvil Bank Codes'
        ordering = ['bank_name']
    
    def __str__(self):
        return f"{self.bank_code} - {self.bank_name}"


class PagoMovilRecipient(models.Model):
    """Store Pago Móvil recipient information."""
    
    bank_code = models.ForeignKey(
        PagoMovilBankCode,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    recipient_id = models.CharField(
        max_length=20,
        help_text="Recipient ID (starts with V or J)"
    )
    recipient_phone = models.CharField(
        max_length=20,
        help_text="Registered phone number for Pago Móvil"
    )
    recipient_name = models.CharField(
        max_length=100,
        help_text="Recipient name"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Pago Móvil Recipient'
        verbose_name_plural = 'Pago Móvil Recipients'
        unique_together = ['bank_code', 'recipient_id', 'recipient_phone']
    
    def __str__(self):
        return f"{self.recipient_name} ({self.recipient_id}) - {self.bank_code.bank_name}"


class PagoMovilVerificationRequest(models.Model):
    """Store Pago Móvil verification requests."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='pagomovil_requests'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='pagomovil_requests',
        null=True,
        blank=True
    )
    
    # Sender information
    sender_id = models.CharField(
        max_length=20,
        help_text="Sender ID (e.g., V-12345678 or J-12345678-0)"
    )
    sender_phone = models.CharField(
        max_length=20,
        help_text="Sender phone number"
    )
    
    # Bank and recipient information
    bank_code = models.ForeignKey(
        PagoMovilBankCode,
        on_delete=models.CASCADE,
        related_name='verification_requests'
    )
    recipient = models.ForeignKey(
        PagoMovilRecipient,
        on_delete=models.CASCADE,
        related_name='verification_requests'
    )
    
    # Amount and exchange rate
    amount_ves = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Amount in VES"
    )
    exchange_rate_used = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Exchange rate at submission time"
    )
    usd_equivalent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="USD equivalent amount"
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(
        blank=True,
        help_text="Admin notes"
    )
    
    # Admin tracking
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_pagomovil_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pago Móvil Verification Request'
        verbose_name_plural = 'Pago Móvil Verification Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at', 'status']),
        ]
    
    def __str__(self):
        return f"Pago Móvil {self.id} - {self.user.email} - {self.amount_ves} VES ({self.status})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate USD equivalent if not set."""
        if not self.usd_equivalent and self.amount_ves and self.exchange_rate_used:
            self.usd_equivalent = self.amount_ves / self.exchange_rate_used
        super().save(*args, **kwargs)
    
    @property
    def formatted_sender_id(self):
        """Format sender ID for display."""
        return self.sender_id.upper()
    
    @property
    def formatted_amount(self):
        """Format amount for display."""
        return f"Bs. {self.amount_ves:,.2f}"
    
    @property
    def formatted_usd_equivalent(self):
        """Format USD equivalent for display."""
        return f"${self.usd_equivalent:,.2f}"
    
    def approve(self, admin_user):
        """Approve the verification request."""
        self.status = 'approved'
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.save()
        
        # Update order if exists
        if self.order:
            self.order.payment_status = 'paid'
            self.order.status = 'confirmed'
            self.order.save()
    
    def reject(self, admin_user, reason=""):
        """Reject the verification request."""
        self.status = 'rejected'
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        if reason:
            self.notes = f"Rejected: {reason}"
        self.save()
