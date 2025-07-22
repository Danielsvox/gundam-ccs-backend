from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Orders
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='create_order'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/cancel/',
         views.OrderCancelView.as_view(), name='cancel_order'),
    path('orders/<int:pk>/track/',
         views.OrderTrackingView.as_view(), name='order_tracking'),

    # Checkout
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),

    # Shipping
    path('shipping-methods/', views.ShippingMethodListView.as_view(),
         name='shipping_methods'),

    # Tax Calculation
    path('tax-rates/', views.TaxRateListView.as_view(), name='tax_rates'),
]
