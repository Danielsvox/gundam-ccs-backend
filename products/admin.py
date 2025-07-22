from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Product, ProductImage, Review, ProductSpecification


class ProductImageInline(admin.TabularInline):
    """Inline admin for product images."""

    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order')


class ProductSpecificationInline(admin.TabularInline):
    """Inline admin for product specifications."""

    model = ProductSpecification
    extra = 1
    fields = ('name', 'value', 'order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin."""

    list_display = ('name', 'slug', 'is_active', 'product_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    fieldsets = (
        ('Basic Info', {'fields': ('name', 'slug', 'description')}),
        ('Image', {'fields': ('image',)}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at', 'updated_at')

    def product_count(self, obj):
        """Display product count for category."""
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Product admin."""

    list_display = ('name', 'category', 'grade', 'price', 'current_price_display',
                    'in_stock', 'stock_quantity', 'rating', 'is_featured', 'created_at')
    list_filter = ('category', 'grade', 'in_stock', 'is_featured',
                   'is_active', 'manufacturer', 'created_at')
    search_fields = ('name', 'description', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Info', {'fields': ('name', 'slug',
         'description', 'short_description')}),
        ('Pricing', {'fields': ('price', 'sale_price')}),
        ('Category & Grade', {
         'fields': ('category', 'grade', 'scale', 'manufacturer')}),
        ('Inventory', {'fields': ('in_stock', 'stock_quantity', 'sku')}),
        ('Details', {'fields': ('release_date', 'weight', 'dimensions')}),
        ('Status', {'fields': ('is_featured', 'is_active')}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at', 'updated_at', 'rating', 'review_count')
    inlines = [ProductImageInline, ProductSpecificationInline]

    def current_price_display(self, obj):
        """Display current price with sale indicator."""
        if obj.is_on_sale:
            return format_html(
                '<span style="color: red;">${} <small>({}% off)</small></span>',
                obj.current_price,
                obj.discount_percentage
            )
        return f"${obj.current_price}"
    current_price_display.short_description = 'Current Price'

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('category')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Product image admin."""

    list_display = ('product', 'image_preview',
                    'is_primary', 'order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'alt_text')
    ordering = ('product', 'order', 'created_at')

    fieldsets = (
        ('Product', {'fields': ('product',)}),
        ('Image', {'fields': ('image', 'alt_text')}),
        ('Settings', {'fields': ('is_primary', 'order')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at',)

    def image_preview(self, obj):
        """Display image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Review admin."""

    list_display = ('product', 'user', 'rating', 'title',
                    'is_verified_purchase', 'helpful_votes', 'created_at')
    list_filter = ('rating', 'is_verified_purchase', 'created_at')
    search_fields = ('product__name', 'user__email', 'title', 'comment')
    ordering = ('-created_at',)

    fieldsets = (
        ('Product & User', {'fields': ('product', 'user')}),
        ('Review', {'fields': ('rating', 'title', 'comment')}),
        ('Status', {'fields': ('is_verified_purchase', 'helpful_votes')}),
        ('Timestamps', {'fields': ('created_at',
         'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('product', 'user')


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    """Product specification admin."""

    list_display = ('product', 'name', 'value', 'order')
    list_filter = ('order',)
    search_fields = ('product__name', 'name', 'value')
    ordering = ('product', 'order', 'name')

    fieldsets = (
        ('Product', {'fields': ('product',)}),
        ('Specification', {'fields': ('name', 'value', 'order')}),
    )
