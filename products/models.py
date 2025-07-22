from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.contrib.auth import get_user_model

User = get_user_model()


class Category(models.Model):
    """Product categories for Gundam model kits."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']


class Product(models.Model):
    """Gundam model kit products."""

    GRADE_CHOICES = [
        ('PG', 'Perfect Grade'),
        ('MG', 'Master Grade'),
        ('RG', 'Real Grade'),
        ('HG', 'High Grade'),
        ('SD', 'Super Deformed'),
        ('FM', 'Full Mechanics'),
        ('RE', 'RE/100'),
        ('NG', 'No Grade'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='products')
    grade = models.CharField(
        max_length=10, choices=GRADE_CHOICES, default='HG')
    # e.g., "1/144", "1/100"
    scale = models.CharField(max_length=20, blank=True)
    manufacturer = models.CharField(max_length=100, default='Bandai')
    release_date = models.DateField(blank=True, null=True)
    in_stock = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    weight = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True)  # in grams
    dimensions = models.CharField(
        max_length=100, blank=True)  # e.g., "L x W x H"
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_products'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            self.sku = f"GUN-{self.id:06d}" if self.id else "GUN-000000"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def current_price(self):
        """Return the current price (sale price if available, otherwise regular price)."""
        return self.sale_price if self.sale_price else self.price

    @property
    def is_on_sale(self):
        """Check if the product is on sale."""
        return self.sale_price is not None and self.sale_price < self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage if on sale."""
        if self.is_on_sale:
            return int(((self.price - self.sale_price) / self.price) * 100)
        return 0

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']


class ProductImage(models.Model):
    """Product images."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Set all other images of this product to not primary
            ProductImage.objects.filter(
                product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'
        ordering = ['order', 'created_at']


class Review(models.Model):
    """Product reviews and ratings."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product rating and review count
        self.update_product_stats()

    def update_product_stats(self):
        """Update product rating and review count."""
        reviews = Review.objects.filter(product=self.product)
        total_rating = sum(review.rating for review in reviews)
        count = reviews.count()

        self.product.rating = total_rating / count if count > 0 else 0
        self.product.review_count = count
        self.product.save()

    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name}"

    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        unique_together = ['product', 'user']


class ProductSpecification(models.Model):
    """Product specifications and details."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}: {self.value}"

    class Meta:
        verbose_name = 'Product Specification'
        verbose_name_plural = 'Product Specifications'
        ordering = ['order', 'name']
        unique_together = ['product', 'name']
