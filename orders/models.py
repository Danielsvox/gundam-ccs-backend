from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product
from cart.models import CartCoupon

User = get_user_model()


class Order(models.Model):
    """Customer orders."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Shipping information
    shipping_address = models.JSONField()
    billing_address = models.JSONField(blank=True, null=True)

    # Payment information
    payment_intent_id = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)

    # Coupon
    applied_coupon = models.ForeignKey(
        CartCoupon, on_delete=models.SET_NULL, blank=True, null=True)

    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    tracking_url = models.URLField(blank=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate a unique order number."""
        import random
        import string
        from django.utils import timezone

        # Format: GUN-YYYYMMDD-XXXXX
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=5))
        order_number = f"GUN-{date_str}-{random_str}"

        # Ensure uniqueness
        while Order.objects.filter(order_number=order_number).exists():
            random_str = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=5))
            order_number = f"GUN-{date_str}-{random_str}"

        return order_number

    def __str__(self):
        return f"Order {self.order_number} - {self.user.email}"

    @property
    def total_items(self):
        """Get total number of items in order."""
        return sum(item.quantity for item in self.items.all())

    def can_cancel(self):
        """Check if order can be cancelled."""
        return self.status in ['pending', 'confirmed']

    def cancel(self):
        """Cancel the order."""
        if self.can_cancel():
            self.status = 'cancelled'
            self.save()
            return True
        return False

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']


class OrderItem(models.Model):
    """Individual items in an order."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # Store product name at time of order
    product_name = models.CharField(max_length=200)
    # Store product SKU at time of order
    product_sku = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_sku:
            self.product_sku = self.product.sku
        if not self.total_price:
            self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product_name} in {self.order}"

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'


class OrderStatusHistory(models.Model):
    """Track order status changes."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"

    class Meta:
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status History'
        ordering = ['-created_at']


class ShippingMethod(models.Model):
    """Available shipping methods."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days = models.CharField(
        max_length=50)  # e.g., "3-5 business days"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"

    class Meta:
        verbose_name = 'Shipping Method'
        verbose_name_plural = 'Shipping Methods'
        ordering = ['price']


class TaxRate(models.Model):
    """Tax rates for different regions."""

    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    rate = models.DecimalField(
        max_digits=5, decimal_places=4)  # e.g., 0.085 for 8.5%
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        location = f"{self.city}, {self.state}" if self.city and self.state else self.state or self.country
        return f"{location} - {self.rate * 100}%"

    class Meta:
        verbose_name = 'Tax Rate'
        verbose_name_plural = 'Tax Rates'
        unique_together = ['country', 'state', 'city', 'postal_code']
