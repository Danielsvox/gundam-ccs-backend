from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, CartCoupon, AppliedCoupon


class CartItemInline(admin.TabularInline):
    """Inline admin for cart items."""

    model = CartItem
    extra = 0
    fields = ('product', 'quantity', 'total_price', 'is_available')
    readonly_fields = ('total_price', 'is_available')


class AppliedCouponInline(admin.TabularInline):
    """Inline admin for applied coupons."""

    model = AppliedCoupon
    extra = 0
    fields = ('coupon', 'discount_amount', 'applied_at')
    readonly_fields = ('discount_amount', 'applied_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Cart admin."""

    list_display = ('user', 'total_items', 'total_price',
                    'total_price_with_tax', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email',)
    ordering = ('-created_at',)

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Summary', {'fields': ('total_items',
         'total_price', 'total_price_with_tax')}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('total_items', 'total_price',
                       'total_price_with_tax', 'created_at', 'updated_at')
    inlines = [CartItemInline, AppliedCouponInline]

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Cart item admin."""

    list_display = ('cart', 'product', 'quantity', 'unit_price',
                    'total_price', 'is_available', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('cart__user__email', 'product__name')
    ordering = ('-added_at',)

    fieldsets = (
        ('Cart & Product', {'fields': ('cart', 'product')}),
        ('Quantity & Price', {
         'fields': ('quantity', 'unit_price', 'total_price')}),
        ('Status', {'fields': ('is_available',)}),
        ('Timestamps', {'fields': ('added_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('unit_price', 'total_price',
                       'is_available', 'added_at', 'updated_at')

    def unit_price(self, obj):
        """Display unit price."""
        return f"${obj.product.current_price}"
    unit_price.short_description = 'Unit Price'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('cart__user', 'product')


@admin.register(CartCoupon)
class CartCouponAdmin(admin.ModelAdmin):
    """Cart coupon admin."""

    list_display = ('code', 'name', 'coupon_type', 'value',
                    'minimum_purchase', 'is_valid', 'used_count', 'is_active')
    list_filter = ('coupon_type', 'is_active', 'valid_from', 'valid_until')
    search_fields = ('code', 'name', 'description')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Info', {'fields': ('code', 'name', 'description')}),
        ('Coupon Type', {'fields': ('coupon_type', 'value',
         'minimum_purchase', 'maximum_discount')}),
        ('Usage', {'fields': ('usage_limit', 'used_count')}),
        ('Validity', {'fields': ('is_active', 'valid_from', 'valid_until')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('used_count', 'created_at')

    def is_valid(self, obj):
        """Display if coupon is valid."""
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid.short_description = 'Valid'


@admin.register(AppliedCoupon)
class AppliedCouponAdmin(admin.ModelAdmin):
    """Applied coupon admin."""

    list_display = ('cart', 'coupon', 'discount_amount', 'applied_at')
    list_filter = ('applied_at',)
    search_fields = ('cart__user__email', 'coupon__code', 'coupon__name')
    ordering = ('-applied_at',)

    fieldsets = (
        ('Cart & Coupon', {'fields': ('cart', 'coupon')}),
        ('Discount', {'fields': ('discount_amount',)}),
        ('Timestamps', {'fields': ('applied_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('discount_amount', 'applied_at')

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('cart__user', 'coupon')
