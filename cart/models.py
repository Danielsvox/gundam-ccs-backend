from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product

User = get_user_model()


class Cart(models.Model):
    """Shopping cart for users."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total_items(self):
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        """Calculate total price of all items in cart."""
        return sum(item.total_price for item in self.items.all())

    @property
    def total_price_with_tax(self):
        """Calculate total price including tax (assuming 8.5% tax rate)."""
        from decimal import Decimal
        return self.total_price * Decimal('1.085')

    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'


class CartItem(models.Model):
    """Individual items in the shopping cart."""

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart}"

    @property
    def total_price(self):
        """Calculate total price for this item."""
        return self.product.current_price * self.quantity

    @property
    def is_available(self):
        """Check if the product is available in the requested quantity."""
        return self.product.in_stock and self.product.stock_quantity >= self.quantity

    def save(self, *args, **kwargs):
        # Ensure quantity doesn't exceed available stock
        if self.product.stock_quantity < self.quantity:
            self.quantity = self.product.stock_quantity
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'product']
        ordering = ['-added_at']


class CartCoupon(models.Model):
    """Coupons that can be applied to carts."""

    COUPON_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES)
    # Percentage or fixed amount
    value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_purchase = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    maximum_discount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_valid(self):
        """Check if the coupon is still valid."""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )

    def calculate_discount(self, cart_total):
        """Calculate discount amount for given cart total."""
        from decimal import Decimal

        if not self.is_valid or cart_total < self.minimum_purchase:
            return 0

        if self.coupon_type == 'percentage':
            discount = cart_total * (self.value / Decimal('100'))
            if self.maximum_discount:
                discount = min(discount, self.maximum_discount)
            return discount
        elif self.coupon_type == 'fixed':
            return min(self.value, cart_total)
        elif self.coupon_type == 'free_shipping':
            return 0  # Free shipping is handled separately

        return 0

    class Meta:
        verbose_name = 'Cart Coupon'
        verbose_name_plural = 'Cart Coupons'
        ordering = ['-created_at']


class AppliedCoupon(models.Model):
    """Coupons applied to specific carts."""

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='applied_coupons')
    coupon = models.ForeignKey(CartCoupon, on_delete=models.CASCADE)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coupon.code} applied to {self.cart}"

    class Meta:
        verbose_name = 'Applied Coupon'
        verbose_name_plural = 'Applied Coupons'
        unique_together = ['cart', 'coupon']
