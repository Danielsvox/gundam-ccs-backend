from rest_framework import status, generics, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg
from django.shortcuts import get_object_or_404

from .models import Category, Product, ProductImage, Review, ProductSpecification
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductSearchSerializer, ProductFilterSerializer, ReviewSerializer,
    ReviewCreateSerializer, ReviewUpdateSerializer, ProductImageSerializer,
    ProductSpecificationSerializer
)


class CategoryListView(generics.ListAPIView):
    """Category list view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True)


class CategoryDetailView(generics.RetrieveAPIView):
    """Category detail view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True)
    lookup_field = 'slug'


class ProductListView(generics.ListAPIView):
    """Product list view with filtering and search."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'grade',
                        'manufacturer', 'in_stock', 'is_featured']
    search_fields = ['name', 'description', 'short_description']
    ordering_fields = ['price', 'sale_price', 'rating', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get filtered products."""
        queryset = Product.objects.filter(
            is_active=True).select_related('category')

        # Custom filters
        category_slug = self.request.query_params.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        on_sale = self.request.query_params.get('on_sale')
        if on_sale == 'true':
            queryset = queryset.filter(sale_price__isnull=False)

        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    """Product detail view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.filter(is_active=True)
    lookup_field = 'slug'


class ProductSearchView(generics.ListAPIView):
    """Product search view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSearchSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description',
                     'short_description', 'category__name']

    def get_queryset(self):
        """Get search results."""
        queryset = Product.objects.filter(
            is_active=True).select_related('category')

        # Get search query
        query = self.request.query_params.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(short_description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(grade__icontains=query) |
                Q(manufacturer__icontains=query)
            )

        return queryset


class FeaturedProductsView(generics.ListAPIView):
    """Featured products view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        """Get featured products."""
        return Product.objects.filter(is_active=True, is_featured=True).select_related('category')


class NewArrivalsView(generics.ListAPIView):
    """New arrivals view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        """Get new arrivals."""
        from django.utils import timezone
        from datetime import timedelta

        # Get products added in the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return Product.objects.filter(
            is_active=True,
            created_at__gte=thirty_days_ago
        ).select_related('category').order_by('-created_at')[:20]


class OnSaleProductsView(generics.ListAPIView):
    """On sale products view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        """Get products on sale."""
        return Product.objects.filter(
            is_active=True,
            sale_price__isnull=False
        ).select_related('category')


class ReviewListView(generics.ListCreateAPIView):
    """Review list and create view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        """Get reviews for a specific product."""
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug, is_active=True)
        return Review.objects.filter(product=product).select_related('user')

    def get_permissions(self):
        """Set permissions based on request method."""
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return ReviewCreateSerializer
        return ReviewSerializer

    def perform_create(self, serializer):
        """Create review for the product."""
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug, is_active=True)
        serializer.save(user=self.request.user, product=product)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Review detail view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReviewUpdateSerializer

    def get_queryset(self):
        """Get user's reviews."""
        return Review.objects.filter(user=self.request.user)

    def get_permissions(self):
        """Set permissions based on request method."""
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'GET':
            return ReviewSerializer
        return ReviewUpdateSerializer


class ProductImageListView(generics.ListAPIView):
    """Product image list view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductImageSerializer

    def get_queryset(self):
        """Get images for a specific product."""
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug, is_active=True)
        return ProductImage.objects.filter(product=product)


class ProductSpecificationListView(generics.ListAPIView):
    """Product specification list view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSpecificationSerializer

    def get_queryset(self):
        """Get specifications for a specific product."""
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug, is_active=True)
        return ProductSpecification.objects.filter(product=product)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_stats(request, product_slug):
    """Get product statistics."""
    product = get_object_or_404(Product, slug=product_slug, is_active=True)

    # Calculate review statistics
    reviews = Review.objects.filter(product=product)
    total_reviews = reviews.count()

    if total_reviews > 0:
        avg_rating = reviews.aggregate(
            avg_rating=Avg('rating'))['avg_rating']
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[i] = reviews.filter(rating=i).count()
    else:
        avg_rating = 0
        rating_distribution = {i: 0 for i in range(1, 6)}

    return Response({
        'product_id': product.id,
        'total_reviews': total_reviews,
        'average_rating': avg_rating,
        'rating_distribution': rating_distribution,
        'stock_quantity': product.stock_quantity,
        'is_on_sale': product.is_on_sale,
        'discount_percentage': product.discount_percentage if product.is_on_sale else 0,
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def helpful_review(request, review_id):
    """Mark review as helpful."""
    review = get_object_or_404(Review, id=review_id)

    # Increment helpful votes
    review.helpful_votes += 1
    review.save()

    return Response({
        'message': 'Review marked as helpful.',
        'helpful_votes': review.helpful_votes
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def related_products(request, product_slug):
    """Get related products."""
    product = get_object_or_404(Product, slug=product_slug, is_active=True)

    # Get products from the same category and grade
    related = Product.objects.filter(
        is_active=True,
        category=product.category,
        grade=product.grade
    ).exclude(id=product.id).select_related('category')[:8]

    serializer = ProductListSerializer(related, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_categories(request):
    """Get all product categories with product counts."""
    categories = Category.objects.filter(is_active=True)

    category_data = []
    for category in categories:
        product_count = Product.objects.filter(
            category=category,
            is_active=True
        ).count()

        category_data.append({
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'image': category.image.url if category.image else None,
            'product_count': product_count,
        })

    return Response(category_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def product_grades(request):
    """Get all product grades with counts."""
    grades = Product.objects.filter(is_active=True).values('grade').distinct()

    grade_data = []
    for grade_info in grades:
        grade = grade_info['grade']
        count = Product.objects.filter(grade=grade, is_active=True).count()

        grade_data.append({
            'grade': grade,
            'display_name': dict(Product.GRADE_CHOICES)[grade],
            'count': count,
        })

    return Response(grade_data)


# ============================================================================
# ADMIN-ONLY VIEWS - Only accessible by admins/superadmins
# ============================================================================

class IsAdminUser(permissions.BasePermission):
    """Custom permission to only allow admin users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_staff or request.user.is_superuser))


class AdminProductCreateView(generics.CreateAPIView):
    """Admin-only product creation view."""

    permission_classes = [IsAdminUser]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.all()

    def perform_create(self, serializer):
        """Create product with admin user."""
        serializer.save(created_by=self.request.user)


class AdminProductUpdateView(generics.UpdateAPIView):
    """Admin-only product update view."""

    permission_classes = [IsAdminUser]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.all()
    lookup_field = 'slug'

    def perform_update(self, serializer):
        """Update product with admin user."""
        serializer.save(updated_by=self.request.user)


class AdminProductDeleteView(generics.DestroyAPIView):
    """Admin-only product deletion view."""

    permission_classes = [IsAdminUser]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.all()
    lookup_field = 'slug'

    def perform_destroy(self, instance):
        """Soft delete product (set is_active=False)."""
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])


class AdminProductListView(generics.ListAPIView):
    """Admin-only product list view (includes inactive products)."""

    permission_classes = [IsAdminUser]
    serializer_class = ProductDetailSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'grade', 'manufacturer',
                        'in_stock', 'is_featured', 'is_active']
    search_fields = ['name', 'description', 'short_description', 'sku']
    ordering_fields = ['price', 'sale_price', 'rating', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        """Get all products (including inactive) for admin view."""
        return Product.objects.all().select_related('category')


class AdminCategoryCreateView(generics.CreateAPIView):
    """Admin-only category creation view."""

    permission_classes = [IsAdminUser]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class AdminCategoryUpdateView(generics.UpdateAPIView):
    """Admin-only category update view."""

    permission_classes = [IsAdminUser]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    lookup_field = 'slug'


class AdminCategoryDeleteView(generics.DestroyAPIView):
    """Admin-only category deletion view."""

    permission_classes = [IsAdminUser]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    lookup_field = 'slug'

    def perform_destroy(self, instance):
        """Soft delete category (set is_active=False)."""
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])


class AdminCategoryListView(generics.ListAPIView):
    """Admin-only category list view (includes inactive categories)."""

    permission_classes = [IsAdminUser]
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['name']

    def get_queryset(self):
        """Get all categories (including inactive) for admin view."""
        return Category.objects.all()


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_bulk_product_action(request):
    """Admin-only bulk product actions (activate/deactivate/delete)."""
    action = request.data.get('action')
    product_ids = request.data.get('product_ids', [])

    if not action or not product_ids:
        return Response({
            'error': 'Action and product_ids are required.'
        }, status=status.HTTP_400_BAD_REQUEST)

    products = Product.objects.filter(id__in=product_ids)

    if action == 'activate':
        products.update(is_active=True)
        message = f'{products.count()} products activated.'
    elif action == 'deactivate':
        products.update(is_active=False)
        message = f'{products.count()} products deactivated.'
    elif action == 'delete':
        products.update(is_active=False)  # Soft delete
        message = f'{products.count()} products deleted.'
    elif action == 'feature':
        products.update(is_featured=True)
        message = f'{products.count()} products marked as featured.'
    elif action == 'unfeature':
        products.update(is_featured=False)
        message = f'{products.count()} products unmarked as featured.'
    else:
        return Response({
            'error': 'Invalid action. Allowed: activate, deactivate, delete, feature, unfeature'
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'message': message,
        'affected_count': products.count()
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    """Admin-only dashboard statistics."""
    from django.db.models import Count, Sum, Avg
    from django.utils import timezone
    from datetime import timedelta

    # Get date range (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Product statistics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    featured_products = Product.objects.filter(is_featured=True).count()
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=5, is_active=True).count()

    # Recent products
    recent_products = Product.objects.filter(
        created_at__gte=thirty_days_ago).count()

    # Category statistics
    total_categories = Category.objects.count()
    active_categories = Category.objects.filter(is_active=True).count()

    # Review statistics
    total_reviews = Review.objects.count()
    recent_reviews = Review.objects.filter(
        created_at__gte=thirty_days_ago).count()
    avg_rating = Review.objects.aggregate(avg_rating=Avg('rating'))[
        'avg_rating'] or 0

    return Response({
        'products': {
            'total': total_products,
            'active': active_products,
            'featured': featured_products,
            'low_stock': low_stock_products,
            'recent': recent_products,
        },
        'categories': {
            'total': total_categories,
            'active': active_categories,
        },
        'reviews': {
            'total': total_reviews,
            'recent': recent_reviews,
            'average_rating': round(avg_rating, 2),
        }
    })
