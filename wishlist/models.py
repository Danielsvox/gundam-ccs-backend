from django.db import models
from django.contrib.auth import get_user_model
from products.models import Product

User = get_user_model()


class Wishlist(models.Model):
    """User wishlist for saving products."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='wishlists')
    name = models.CharField(max_length=100, default='My Wishlist')
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.user.email}"

    @property
    def total_items(self):
        """Get total number of items in wishlist."""
        return self.items.count()

    @property
    def total_value(self):
        """Calculate total value of all items in wishlist."""
        return sum(item.product.current_price for item in self.items.all())

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        ordering = ['-created_at']


class WishlistItem(models.Model):
    """Individual items in a wishlist."""

    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)  # User notes about the item
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        default='medium'
    )

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.name}"

    class Meta:
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        unique_together = ['wishlist', 'product']
        ordering = ['-priority', '-added_at']


class WishlistShare(models.Model):
    """Wishlist sharing functionality."""

    wishlist = models.ForeignKey(
        Wishlist, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shared_wishlists')
    shared_with_email = models.EmailField()
    share_token = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Share of {self.wishlist.name} with {self.shared_with_email}"

    @property
    def is_expired(self):
        """Check if the share link has expired."""
        from django.utils import timezone
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    class Meta:
        verbose_name = 'Wishlist Share'
        verbose_name_plural = 'Wishlist Shares'
        ordering = ['-created_at']


class PriceAlert(models.Model):
    """Price alerts for wishlist items."""

    ALERT_TYPES = [
        ('below_price', 'Below Price'),
        ('percentage_drop', 'Percentage Drop'),
        ('back_in_stock', 'Back in Stock'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='price_alerts')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    target_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    percentage_drop = models.PositiveIntegerField(
        blank=True, null=True)  # e.g., 20 for 20%
    is_active = models.BooleanField(default=True)
    triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.alert_type == 'below_price':
            return f"Alert when {self.product.name} drops below ${self.target_price}"
        elif self.alert_type == 'percentage_drop':
            return f"Alert when {self.product.name} drops {self.percentage_drop}%"
        else:
            return f"Alert when {self.product.name} is back in stock"

    def check_alert(self):
        """Check if the alert should be triggered."""
        if self.triggered or not self.is_active:
            return False

        current_price = self.product.current_price

        if self.alert_type == 'below_price' and self.target_price:
            if current_price <= self.target_price:
                return True
        elif self.alert_type == 'percentage_drop' and self.percentage_drop:
            # This would need to track historical prices
            # For now, we'll just check if it's on sale
            if self.product.is_on_sale:
                discount = self.product.discount_percentage
                if discount >= self.percentage_drop:
                    return True
        elif self.alert_type == 'back_in_stock':
            if self.product.in_stock and self.product.stock_quantity > 0:
                return True

        return False

    def trigger_alert(self):
        """Trigger the price alert."""
        from django.utils import timezone

        self.triggered = True
        self.triggered_at = timezone.now()
        self.is_active = False
        self.save()

        # Here you would send email notification
        # self.send_notification()

    class Meta:
        verbose_name = 'Price Alert'
        verbose_name_plural = 'Price Alerts'
        ordering = ['-created_at']
        unique_together = ['user', 'product', 'alert_type']


class WishlistAnalytics(models.Model):
    """Analytics for wishlist items."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='wishlist_analytics')
    times_added = models.PositiveIntegerField(default=0)
    times_removed = models.PositiveIntegerField(default=0)
    current_wishlist_count = models.PositiveIntegerField(default=0)
    last_added = models.DateTimeField(blank=True, null=True)
    last_removed = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analytics for {self.product.name}"

    class Meta:
        verbose_name = 'Wishlist Analytics'
        verbose_name_plural = 'Wishlist Analytics'
        unique_together = ['product']
