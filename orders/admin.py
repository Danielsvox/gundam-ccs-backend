from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, OrderStatusHistory, ShippingMethod, TaxRate


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items."""

    model = OrderItem
    extra = 0
    fields = ('product', 'product_name', 'product_sku',
              'quantity', 'unit_price', 'total_price')
    readonly_fields = ('product_name', 'product_sku', 'total_price')


class OrderStatusHistoryInline(admin.TabularInline):
    """Inline admin for order status history."""

    model = OrderStatusHistory
    extra = 0
    fields = ('status', 'notes', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order admin."""

    list_display = ('order_number', 'user', 'status', 'payment_status',
                    'total_amount', 'total_items', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__email', 'payment_intent_id')
    ordering = ('-created_at',)

    fieldsets = (
        ('Order Info', {'fields': ('order_number',
         'user', 'status', 'payment_status')}),
        ('Pricing', {'fields': ('subtotal', 'tax_amount',
         'shipping_amount', 'discount_amount', 'total_amount')}),
        ('Shipping', {'fields': ('shipping_address',
         'billing_address', 'tracking_number', 'tracking_url')}),
        ('Payment', {'fields': ('payment_intent_id',
         'payment_method', 'applied_coupon')}),
        ('Timestamps', {'fields': ('shipped_at',
         'delivered_at', 'created_at', 'updated_at')}),
        ('Notes', {'fields': ('customer_notes', 'admin_notes')}),
    )

    readonly_fields = ('order_number', 'subtotal', 'tax_amount', 'shipping_amount',
                       'discount_amount', 'total_amount', 'total_items', 'created_at', 'updated_at')
    inlines = [OrderItemInline, OrderStatusHistoryInline]

    def total_items(self, obj):
        """Display total items in order."""
        return obj.total_items
    total_items.short_description = 'Items'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user', 'applied_coupon')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Order item admin."""

    list_display = ('order', 'product', 'product_name',
                    'quantity', 'unit_price', 'total_price')
    list_filter = ('order__status',)
    search_fields = ('order__order_number', 'product__name',
                     'product_name', 'product_sku')
    ordering = ('-order__created_at',)

    fieldsets = (
        ('Order & Product', {'fields': ('order', 'product')}),
        ('Product Details', {'fields': ('product_name', 'product_sku')}),
        ('Quantity & Price', {
         'fields': ('quantity', 'unit_price', 'total_price')}),
    )

    readonly_fields = ('product_name', 'product_sku', 'total_price')

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('order', 'product')


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    """Order status history admin."""

    list_display = ('order', 'status', 'notes', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'notes')
    ordering = ('-created_at',)

    fieldsets = (
        ('Order', {'fields': ('order',)}),
        ('Status Change', {'fields': ('status', 'notes')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('order')


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    """Shipping method admin."""

    list_display = ('name', 'price', 'estimated_days',
                    'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('price',)

    fieldsets = (
        ('Basic Info', {'fields': ('name', 'description')}),
        ('Pricing & Delivery', {'fields': ('price', 'estimated_days')}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at',)


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    """Tax rate admin."""

    list_display = ('country', 'state', 'city', 'postal_code',
                    'rate_display', 'is_active', 'created_at')
    list_filter = ('country', 'state', 'is_active', 'created_at')
    search_fields = ('country', 'state', 'city', 'postal_code')
    ordering = ('country', 'state', 'city')

    fieldsets = (
        ('Location', {'fields': ('country', 'state', 'city', 'postal_code')}),
        ('Rate', {'fields': ('rate',)}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at',)

    def rate_display(self, obj):
        """Display rate as percentage."""
        return f"{obj.rate * 100}%"
    rate_display.short_description = 'Rate'
