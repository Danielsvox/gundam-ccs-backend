from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(),
         name='category_detail'),

    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(),
         name='product_detail'),
    path('products/search/', views.ProductSearchView.as_view(),
         name='product_search'),
    path('products/featured/', views.FeaturedProductsView.as_view(),
         name='featured_products'),
    path('products/new-arrivals/',
         views.NewArrivalsView.as_view(), name='new_arrivals'),
    path('products/on-sale/', views.OnSaleProductsView.as_view(),
         name='on_sale_products'),

    # Reviews
    path('reviews/', views.ReviewListView.as_view(), name='review_list'),
    path('reviews/<int:pk>/', views.ReviewDetailView.as_view(), name='review_detail'),

    # Product Images
    path('products/<int:product_id>/images/',
         views.ProductImageListView.as_view(), name='product_images'),

    # Product Specifications
    path('products/<int:product_id>/specifications/',
         views.ProductSpecificationListView.as_view(), name='product_specifications'),
]
