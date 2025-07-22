from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, Refund, PaymentMethod, WebhookEvent, Subscription


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payment admin."""

    list_display = ('id', 'order', 'user', 'amount', 'currency',
                    'payment_method', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'currency', 'created_at')
    search_fields = ('order__order_number', 'user__email',
                     'stripe_payment_intent_id', 'stripe_charge_id')
    ordering = ('-created_at',)

    fieldsets = (
        ('Order & User', {'fields': ('order', 'user')}),
        ('Payment Details', {'fields': ('amount',
         'currency', 'payment_method', 'status')}),
        ('Stripe Info', {'fields': ('stripe_payment_intent_id',
         'stripe_charge_id', 'stripe_customer_id')}),
        ('Error Handling', {'fields': ('error_message', 'error_code')}),
        ('Metadata', {'fields': ('metadata',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('order', 'user')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """Refund admin."""

    list_display = ('id', 'payment', 'amount', 'currency',
                    'reason', 'status', 'created_at')
    list_filter = ('reason', 'status', 'currency', 'created_at')
    search_fields = ('payment__order__order_number', 'stripe_refund_id')
    ordering = ('-created_at',)

    fieldsets = (
        ('Payment', {'fields': ('payment',)}),
        ('Refund Details', {
         'fields': ('amount', 'currency', 'reason', 'status')}),
        ('Stripe Info', {'fields': ('stripe_refund_id',)}),
        ('Metadata', {'fields': ('metadata',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('payment__order', 'payment__user')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Payment method admin."""

    list_display = ('user', 'type', 'display_info', 'is_default', 'created_at')
    list_filter = ('type', 'is_default', 'created_at')
    search_fields = ('user__email', 'stripe_payment_method_id')
    ordering = ('-created_at',)

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Method Type', {'fields': ('type', 'is_default')}),
        ('Stripe Info', {
         'fields': ('stripe_payment_method_id', 'stripe_customer_id')}),
        ('Card Details', {'fields': ('last4', 'brand',
         'exp_month', 'exp_year'), 'classes': ('collapse',)}),
        ('Bank Details', {'fields': ('bank_name',
         'account_last4'), 'classes': ('collapse',)}),
        ('Metadata', {'fields': ('metadata',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at', 'updated_at')

    def display_info(self, obj):
        """Display payment method info."""
        if obj.type == 'card':
            return f"{obj.brand.title()} ****{obj.last4}"
        elif obj.type == 'bank_account':
            return f"{obj.bank_name} ****{obj.account_last4}"
        return obj.get_type_display()
    display_info.short_description = 'Payment Info'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user')


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    """Webhook event admin."""

    list_display = ('stripe_event_id', 'event_type', 'livemode',
                    'processed', 'created', 'created_at')
    list_filter = ('event_type', 'livemode',
                   'processed', 'created', 'created_at')
    search_fields = ('stripe_event_id', 'event_type')
    ordering = ('-created_at',)

    fieldsets = (
        ('Event Info', {
         'fields': ('stripe_event_id', 'event_type', 'api_version')}),
        ('Stripe Details', {'fields': ('created', 'livemode')}),
        ('Processing', {'fields': ('processed',
         'processed_at', 'processing_error')}),
        ('Event Data', {'fields': ('data',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created', 'created_at', 'processed_at')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Subscription admin."""

    list_display = ('stripe_subscription_id', 'user', 'status', 'amount',
                    'currency', 'interval', 'current_period_end', 'created_at')
    list_filter = ('status', 'currency', 'interval',
                   'cancel_at_period_end', 'created_at')
    search_fields = ('stripe_subscription_id',
                     'user__email', 'stripe_customer_id')
    ordering = ('-created_at',)

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Stripe Info', {
         'fields': ('stripe_subscription_id', 'stripe_customer_id')}),
        ('Status', {'fields': ('status',)}),
        ('Billing', {'fields': ('current_period_start',
         'current_period_end', 'cancel_at_period_end', 'canceled_at')}),
        ('Pricing', {'fields': ('amount',
         'currency', 'interval', 'interval_count')}),
        ('Metadata', {'fields': ('metadata',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('current_period_start', 'current_period_end',
                       'canceled_at', 'created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user')
