from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    # Cart Management
    path('', views.CartView.as_view(), name='cart_detail'),
    path('summary/', views.CartSummaryView.as_view(), name='cart_summary'),

    # Cart Items
    path('items/', views.CartItemListView.as_view(), name='cart_items'),
    path('items/<int:pk>/', views.CartItemDetailView.as_view(),
         name='cart_item_detail'),

    # Coupons
    path('coupons/', views.CartCouponListView.as_view(), name='coupon_list'),
    path('coupons/apply/', views.ApplyCouponView.as_view(), name='apply_coupon'),
    path('coupons/remove/', views.RemoveCouponView.as_view(), name='remove_coupon'),
    path('applied-coupons/', views.AppliedCouponListView.as_view(),
         name='applied_coupons'),

    # Additional endpoints for frontend compatibility
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('count/', views.cart_count, name='cart_count'),
    path('merge/', views.merge_cart, name='merge_cart'),
]
