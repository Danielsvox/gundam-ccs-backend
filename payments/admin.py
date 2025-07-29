from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from .models import (
    Payment, PaymentMethod, Refund, WebhookEvent, Subscription,
    ExchangeRateLog, ExchangeRateAlert, ExchangeRateSnapshot,
    PagoMovilBankCode, PagoMovilRecipient, PagoMovilVerificationRequest
)
from .services.exchange_rate_service import exchange_rate_service
from decimal import Decimal


@admin.register(ExchangeRateLog)
class ExchangeRateLogAdmin(admin.ModelAdmin):
    """Admin interface for exchange rate logs."""

    list_display = (
        'rate_display', 'source_display', 'timestamp', 'change_percentage_display',
        'fetch_success_display', 'is_active_display'
    )
    list_filter = (
        'source', 'fetch_success', 'is_active', 'timestamp'
    )
    search_fields = ('usd_to_ves', 'source', 'error_message')
    readonly_fields = (
        'timestamp', 'change_percentage', 'rate_chart_link'
    )
    ordering = ('-timestamp',)

    actions = ['activate_rate', 'deactivate_rate', 'refresh_current_rate']

    fieldsets = (
        ('Rate Information', {
            'fields': ('usd_to_ves', 'source', 'timestamp')
        }),
        ('Status', {
            'fields': ('is_active', 'fetch_success')
        }),
        ('Change Tracking', {
            'fields': ('change_percentage',),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Tools', {
            'fields': ('rate_chart_link',),
            'classes': ('collapse',)
        })
    )

    def rate_display(self, obj):
        """Display rate with formatting."""
        if obj.fetch_success:
            return format_html(
                '<strong>{} VES</strong>',
                obj.usd_to_ves
            )
        else:
            return format_html(
                '<span style="color: red;">{} VES (Failed)</span>',
                obj.usd_to_ves
            )
    rate_display.short_description = 'Rate (USD → VES)'

    def source_display(self, obj):
        """Display source with icon."""
        icons = {
            'google_finance': '🔍',
            'exchangerate_host': '🌐',
            'open_exchange_rates': '💱',
            'manual': '👤',
            'fallback': '🔄'
        }
        icon = icons.get(obj.source, '❓')
        return format_html('{} {}', icon, obj.get_source_display())
    source_display.short_description = 'Source'

    def change_percentage_display(self, obj):
        """Display change percentage with color coding."""
        if obj.change_percentage is None:
            return '-'

        if obj.change_percentage > 0:
            color = 'green'
            icon = '📈'
        elif obj.change_percentage < 0:
            color = 'red'
            icon = '📉'
        else:
            color = 'gray'
            icon = '➡️'

        return format_html(
            '<span style="color: {};">{} {:.2f}%</span>',
            color, icon, obj.change_percentage
        )
    change_percentage_display.short_description = 'Change %'

    def fetch_success_display(self, obj):
        """Display fetch success status."""
        if obj.fetch_success:
            return format_html('<span style="color: green;">✓ Success</span>')
        else:
            return format_html('<span style="color: red;">✗ Failed</span>')
    fetch_success_display.short_description = 'Fetch Status'

    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html('<span style="color: green;">● Active</span>')
        else:
            return format_html('<span style="color: gray;">○ Inactive</span>')
    is_active_display.short_description = 'Status'

    def rate_chart_link(self, obj):
        """Link to rate chart/statistics."""
        if obj.pk:
            return format_html(
                '<a href="/admin/payments/exchangeratelog/stats/" target="_blank">📊 View Rate Statistics</a>'
            )
        return '-'
    rate_chart_link.short_description = 'Charts & Stats'

    def activate_rate(self, request, queryset):
        """Activate selected rates."""
        if queryset.count() > 1:
            messages.error(request, "You can only activate one rate at a time.")
            return

        rate = queryset.first()
        if rate:
            # Deactivate all other rates
            ExchangeRateLog.objects.filter(is_active=True).update(is_active=False)
            rate.is_active = True
            rate.save()

            # Clear cache
            from django.core.cache import cache
            cache.delete('exchange_rate:current')

            messages.success(request, f"Rate {rate.usd_to_ves} VES activated successfully.")
    activate_rate.short_description = "Activate selected rate"

    def deactivate_rate(self, request, queryset):
        """Deactivate selected rates."""
        count = queryset.update(is_active=False)
        messages.success(request, f"{count} rate(s) deactivated.")
    deactivate_rate.short_description = "Deactivate selected rates"

    def refresh_current_rate(self, request, queryset):
        """Refresh current rate from external sources."""
        try:
            rate_data = exchange_rate_service.fetch_and_store_rate()
            if rate_data:
                messages.success(
                    request,
                    f"Rate refreshed successfully: {rate_data['usd_to_ves']} VES from {rate_data['source']}"
                )
            else:
                messages.error(request, "Failed to refresh rate from external sources.")
        except Exception as e:
            messages.error(request, f"Error refreshing rate: {str(e)}")
    refresh_current_rate.short_description = "Refresh current rate"


@admin.register(ExchangeRateAlert)
class ExchangeRateAlertAdmin(admin.ModelAdmin):
    """Admin interface for exchange rate alerts."""

    list_display = (
        'alert_type_display', 'rate_info', 'threshold_display',
        'acknowledged_display', 'created_at'
    )
    list_filter = (
        'alert_type', 'acknowledged', 'created_at'
    )
    search_fields = ('message', 'exchange_rate__usd_to_ves')
    readonly_fields = (
        'alert_type', 'exchange_rate', 'threshold_value', 'message', 'created_at'
    )
    ordering = ('-created_at',)

    actions = ['acknowledge_alerts', 'unacknowledge_alerts']

    fieldsets = (
        ('Alert Information', {
            'fields': ('alert_type', 'exchange_rate', 'threshold_value', 'message')
        }),
        ('Acknowledgment', {
            'fields': ('acknowledged', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def alert_type_display(self, obj):
        """Display alert type with icon."""
        icons = {
            'high_change': '⚠️',
            'fetch_error': '❌',
            'manual_override': '👤',
            'source_fallback': '🔄'
        }
        icon = icons.get(obj.alert_type, '🔔')
        return format_html('{} {}', icon, obj.get_alert_type_display())
    alert_type_display.short_description = 'Alert Type'

    def rate_info(self, obj):
        """Display related rate information."""
        if obj.exchange_rate:
            return format_html(
                '{} VES ({})',
                obj.exchange_rate.usd_to_ves,
                obj.exchange_rate.source
            )
        return '-'
    rate_info.short_description = 'Rate Info'

    def threshold_display(self, obj):
        """Display threshold value."""
        if obj.threshold_value is not None:
            return f"{obj.threshold_value}%"
        return '-'
    threshold_display.short_description = 'Threshold'

    def acknowledged_display(self, obj):
        """Display acknowledgment status."""
        if obj.acknowledged:
            ack_info = f"by {obj.acknowledged_by.email}" if obj.acknowledged_by else ""
            return format_html(
                '<span style="color: green;">✓ Acknowledged</span><br/><small>{}</small>',
                ack_info
            )
        else:
            return format_html('<span style="color: orange;">🔔 Pending</span>')
    acknowledged_display.short_description = 'Status'

    def acknowledge_alerts(self, request, queryset):
        """Acknowledge selected alerts."""
        count = queryset.filter(acknowledged=False).update(
            acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
        messages.success(request, f"{count} alert(s) acknowledged.")
    acknowledge_alerts.short_description = "Acknowledge selected alerts"

    def unacknowledge_alerts(self, request, queryset):
        """Unacknowledge selected alerts."""
        count = queryset.update(
            acknowledged=False,
            acknowledged_by=None,
            acknowledged_at=None
        )
        messages.success(request, f"{count} alert(s) unacknowledged.")
    unacknowledge_alerts.short_description = "Unacknowledge selected alerts"


@admin.register(ExchangeRateSnapshot)
class ExchangeRateSnapshotAdmin(admin.ModelAdmin):
    """Admin interface for exchange rate snapshots."""

    list_display = (
        'entity_display', 'rate_display', 'amounts_display', 'snapshot_timestamp'
    )
    list_filter = ('snapshot_timestamp',)
    search_fields = ('order__order_number', 'payment__id', 'usd_to_ves')
    readonly_fields = ('usd_to_ves', 'amount_usd', 'amount_ves', 'snapshot_timestamp')
    ordering = ('-snapshot_timestamp',)

    def entity_display(self, obj):
        """Display related entity."""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html(
                '<a href="{}">Order #{}</a>',
                url, obj.order.order_number
            )
        elif obj.payment:
            url = reverse('admin:payments_payment_change', args=[obj.payment.id])
            return format_html(
                '<a href="{}">Payment #{}</a>',
                url, obj.payment.id
            )
        return '-'
    entity_display.short_description = 'Related Entity'

    def rate_display(self, obj):
        """Display exchange rate."""
        return f"{obj.usd_to_ves} VES per USD"
    rate_display.short_description = 'Exchange Rate'

    def amounts_display(self, obj):
        """Display amounts in both currencies."""
        return format_html(
            '<strong>${}</strong> = <strong>Bs. {}</strong>',
            obj.amount_usd, obj.amount_ves
        )
    amounts_display.short_description = 'Amounts'


# Enhanced Payment admin with exchange rate info integrated
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payment admin."""

    list_display = ('id', 'order', 'user', 'amount', 'currency',
                    'payment_method', 'exchange_rate_info', 'status', 'created_at', 'payment_actions')
    list_filter = ('payment_method', 'status', 'currency', 'created_at')
    search_fields = ('order__order_number', 'user__email',
                     'stripe_payment_intent_id', 'stripe_charge_id')
    ordering = ('-created_at',)
    actions = ['confirm_manual_payments', 'mark_payments_failed']

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

    def payment_actions(self, obj):
        """Display payment action buttons."""
        if obj.payment_method == 'manual' and obj.status == 'pending':
            return format_html(
                '<a class="button" href="{}">Confirm Payment</a>',
                f'/admin/payments/payment/{obj.id}/confirm-manual-payment/'
            )
        return '-'
    payment_actions.short_description = 'Actions'

    def exchange_rate_info(self, obj):
        """Display exchange rate snapshot info."""
        try:
            snapshot = obj.exchange_rate_snapshot
            return format_html(
                'Rate: {} VES<br/>VES Amount: Bs. {}',
                snapshot.usd_to_ves, snapshot.amount_ves
            )
        except ExchangeRateSnapshot.DoesNotExist:
            return format_html('<span style="color: gray;">No rate snapshot</span>')
    exchange_rate_info.short_description = 'Exchange Rate'

    def confirm_manual_payments(self, request, queryset):
        """Confirm selected manual payments."""
        manual_payments = queryset.filter(
            payment_method='manual', status='pending')

        confirmed_count = 0
        for payment in manual_payments:
            try:
                # Update payment status
                payment.status = 'succeeded'
                payment.save()

                # Update order status
                order = payment.order
                order.payment_status = 'paid'
                order.status = 'confirmed'
                order.save()

                # Create status history entry
                from orders.models import OrderStatusHistory
                OrderStatusHistory.objects.create(
                    order=order,
                    status='confirmed',
                    notes='Manual payment confirmed via admin'
                )

                # Send WhatsApp notification
                from .services import payment_processor
                payment_processor.process_successful_payment(order, payment)

                confirmed_count += 1
            except Exception as e:
                self.message_user(
                    request, f'Error confirming payment {payment.id}: {str(e)}', level='ERROR')

        self.message_user(
            request, f'Successfully confirmed {confirmed_count} manual payments.')
    confirm_manual_payments.short_description = "Confirm selected manual payments"

    def mark_payments_failed(self, request, queryset):
        """Mark selected payments as failed."""
        updated = queryset.update(status='failed')
        self.message_user(
            request, f'Successfully marked {updated} payments as failed.')
    mark_payments_failed.short_description = "Mark selected payments as failed"


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


@admin.register(PagoMovilBankCode)
class PagoMovilBankCodeAdmin(admin.ModelAdmin):
    """Admin interface for Pago Móvil bank codes."""
    
    list_display = ('bank_code', 'bank_name', 'is_active', 'recipient_count')
    list_filter = ('is_active',)
    search_fields = ('bank_code', 'bank_name')
    ordering = ('bank_name',)
    
    def recipient_count(self, obj):
        """Show number of recipients for this bank."""
        return obj.recipients.filter(is_active=True).count()
    recipient_count.short_description = 'Active Recipients'


@admin.register(PagoMovilRecipient)
class PagoMovilRecipientAdmin(admin.ModelAdmin):
    """Admin interface for Pago Móvil recipients."""
    
    list_display = ('recipient_name', 'bank_code', 'recipient_id', 'recipient_phone', 'is_active')
    list_filter = ('is_active', 'bank_code')
    search_fields = ('recipient_name', 'recipient_id', 'recipient_phone')
    ordering = ('bank_code__bank_name', 'recipient_name')
    
    fieldsets = (
        ('Recipient Information', {
            'fields': ('recipient_name', 'recipient_id', 'recipient_phone')
        }),
        ('Bank Information', {
            'fields': ('bank_code',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(PagoMovilVerificationRequest)
class PagoMovilVerificationRequestAdmin(admin.ModelAdmin):
    """Admin interface for Pago Móvil verification requests."""
    
    list_display = (
        'id', 'user_email', 'sender_id', 'amount_ves', 'usd_equivalent',
        'bank_code', 'status', 'created_at', 'approved_by'
    )
    list_filter = ('status', 'bank_code', 'created_at', 'approved_at')
    search_fields = ('user__email', 'sender_id', 'sender_phone')
    readonly_fields = (
        'user', 'order', 'exchange_rate_used', 'usd_equivalent',
        'created_at', 'updated_at', 'approved_at'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'order', 'status', 'created_at', 'updated_at')
        }),
        ('Sender Information', {
            'fields': ('sender_id', 'sender_phone')
        }),
        ('Payment Details', {
            'fields': ('bank_code', 'recipient', 'amount_ves', 'exchange_rate_used', 'usd_equivalent')
        }),
        ('Admin Actions', {
            'fields': ('approved_by', 'approved_at', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_selected', 'reject_selected']
    
    def user_email(self, obj):
        """Show user email."""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def approve_selected(self, request, queryset):
        """Approve selected verification requests."""
        count = 0
        for verification in queryset.filter(status='pending'):
            verification.approve(request.user)
            count += 1
        
        self.message_user(
            request,
            f"Successfully approved {count} verification request(s)."
        )
    approve_selected.short_description = "Approve selected verification requests"
    
    def reject_selected(self, request, queryset):
        """Reject selected verification requests."""
        count = 0
        for verification in queryset.filter(status='pending'):
            verification.reject(request.user, "Bulk rejection")
            count += 1
        
        self.message_user(
            request,
            f"Successfully rejected {count} verification request(s)."
        )
    reject_selected.short_description = "Reject selected verification requests"
    
    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related(
            'user', 'bank_code', 'recipient', 'approved_by'
        )
