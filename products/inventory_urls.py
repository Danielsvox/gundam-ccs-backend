from django.urls import path

from . import inventory_api as v

app_name = 'inventory'

urlpatterns = [
    path('me/', v.InventoryMeView.as_view(), name='me'),
    path('products/', v.InventoryProductListCreateView.as_view(), name='products'),
    path('products/<int:pk>/', v.InventoryProductDetailView.as_view(), name='product'),
    path('products/<int:pk>/stock/', v.StockAdjustView.as_view(), name='stock'),
    path('products/<int:pk>/movements/', v.StockMovementListView.as_view(), name='movements'),
]