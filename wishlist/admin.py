from django.contrib import admin
from django.utils.html import format_html
from .models import Wishlist, WishlistItem, WishlistShare, PriceAlert, WishlistAnalytics


class WishlistItemInline(admin.TabularInline):
    """Inline admin for wishlist items."""

    model = WishlistItem
    extra = 0
    fields = ('product', 'priority', 'notes', 'added_at')
    readonly_fields = ('added_at',)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """Wishlist admin."""

    list_display = ('name', 'user', 'is_public',
                    'total_items', 'total_value', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'user__email')
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Info', {'fields': ('user', 'name')}),
        ('Settings', {'fields': ('is_public',)}),
        ('Summary', {'fields': ('total_items', 'total_value')}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('total_items', 'total_value',
                       'created_at', 'updated_at')
    inlines = [WishlistItemInline]

    def total_items(self, obj):
        """Display total items in wishlist."""
        return obj.total_items
    total_items.short_description = 'Items'

    def total_value(self, obj):
        """Display total value of wishlist."""
        return f"${obj.total_value}"
    total_value.short_description = 'Total Value'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    """Wishlist item admin."""

    list_display = ('wishlist', 'product', 'priority',
                    'current_price', 'added_at')
    list_filter = ('priority', 'added_at')
    search_fields = ('wishlist__name', 'wishlist__user__email',
                     'product__name', 'notes')
    ordering = ('-added_at',)

    fieldsets = (
        ('Wishlist & Product', {'fields': ('wishlist', 'product')}),
        ('Details', {'fields': ('priority', 'notes')}),
        ('Timestamps', {'fields': ('added_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('added_at',)

    def current_price(self, obj):
        """Display current price of product."""
        return f"${obj.product.current_price}"
    current_price.short_description = 'Current Price'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('wishlist__user', 'product')


@admin.register(WishlistShare)
class WishlistShareAdmin(admin.ModelAdmin):
    """Wishlist share admin."""

    list_display = ('wishlist', 'shared_by', 'shared_with_email',
                    'is_active', 'is_expired', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('wishlist__name', 'shared_by__email',
                     'shared_with_email', 'share_token')
    ordering = ('-created_at',)

    fieldsets = (
        ('Wishlist & Sharing', {
         'fields': ('wishlist', 'shared_by', 'shared_with_email')}),
        ('Share Details', {
         'fields': ('share_token', 'is_active', 'expires_at')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('share_token', 'created_at')

    def is_expired(self, obj):
        """Display if share is expired."""
        if obj.is_expired:
            return format_html('<span style="color: red;">✗ Expired</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    is_expired.short_description = 'Expired'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('wishlist__user', 'shared_by')


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    """Price alert admin."""

    list_display = ('user', 'product', 'alert_type',
                    'target_info', 'is_active', 'triggered', 'created_at')
    list_filter = ('alert_type', 'is_active', 'triggered', 'created_at')
    search_fields = ('user__email', 'product__name')
    ordering = ('-created_at',)

    fieldsets = (
        ('User & Product', {'fields': ('user', 'product')}),
        ('Alert Settings', {
         'fields': ('alert_type', 'target_price', 'percentage_drop')}),
        ('Status', {'fields': ('is_active', 'triggered', 'triggered_at')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('triggered_at', 'created_at')

    def target_info(self, obj):
        """Display target information."""
        if obj.alert_type == 'below_price' and obj.target_price:
            return f"Below ${obj.target_price}"
        elif obj.alert_type == 'percentage_drop' and obj.percentage_drop:
            return f"{obj.percentage_drop}% drop"
        elif obj.alert_type == 'back_in_stock':
            return "Back in stock"
        return "N/A"
    target_info.short_description = 'Target'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user', 'product')


@admin.register(WishlistAnalytics)
class WishlistAnalyticsAdmin(admin.ModelAdmin):
    """Wishlist analytics admin."""

    list_display = ('product', 'times_added', 'times_removed',
                    'current_wishlist_count', 'last_added', 'last_removed')
    list_filter = ('last_added', 'last_removed')
    search_fields = ('product__name',)
    ordering = ('-times_added',)

    fieldsets = (
        ('Product', {'fields': ('product',)}),
        ('Statistics', {'fields': ('times_added',
         'times_removed', 'current_wishlist_count')}),
        ('Timestamps', {'fields': ('last_added', 'last_removed',
         'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('times_added', 'times_removed', 'current_wishlist_count',
                       'last_added', 'last_removed', 'created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('product')
