from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    # Wishlist Management
    path('wishlists/', views.WishlistListView.as_view(), name='wishlist_list'),
    path('wishlists/create/', views.CreateWishlistView.as_view(),
         name='create_wishlist'),
    path('wishlists/<int:pk>/', views.WishlistDetailView.as_view(),
         name='wishlist_detail'),
    path('wishlists/<int:pk>/update/',
         views.UpdateWishlistView.as_view(), name='update_wishlist'),
    path('wishlists/<int:pk>/delete/',
         views.DeleteWishlistView.as_view(), name='delete_wishlist'),
    path('wishlists/<int:pk>/share/',
         views.ShareWishlistView.as_view(), name='share_wishlist'),

    # Wishlist Items
    path('wishlists/<int:wishlist_id>/items/',
         views.WishlistItemsView.as_view(), name='wishlist_items'),
    path('wishlists/<int:wishlist_id>/items/add/',
         views.AddToWishlistView.as_view(), name='add_to_wishlist'),
    path('wishlists/<int:wishlist_id>/items/<int:pk>/',
         views.WishlistItemDetailView.as_view(), name='wishlist_item_detail'),
    path('wishlists/<int:wishlist_id>/items/<int:pk>/remove/',
         views.RemoveFromWishlistView.as_view(), name='remove_from_wishlist'),
    path('wishlists/<int:wishlist_id>/items/<int:pk>/move/',
         views.MoveWishlistItemView.as_view(), name='move_wishlist_item'),

    # Wishlist Sharing
    path('wishlists/shared/<str:share_token>/',
         views.SharedWishlistView.as_view(), name='shared_wishlist'),
    path('wishlists/<int:pk>/share-settings/',
         views.WishlistShareSettingsView.as_view(), name='wishlist_share_settings'),

    # Price Alerts
    path('price-alerts/', views.PriceAlertListView.as_view(),
         name='price_alert_list'),
    path('price-alerts/create/', views.CreatePriceAlertView.as_view(),
         name='create_price_alert'),
    path('price-alerts/<int:pk>/', views.PriceAlertDetailView.as_view(),
         name='price_alert_detail'),
    path('price-alerts/<int:pk>/update/',
         views.UpdatePriceAlertView.as_view(), name='update_price_alert'),
    path('price-alerts/<int:pk>/delete/',
         views.DeletePriceAlertView.as_view(), name='delete_price_alert'),
    path('price-alerts/<int:pk>/toggle/',
         views.TogglePriceAlertView.as_view(), name='toggle_price_alert'),

    # Wishlist Analytics
    path('wishlists/<int:pk>/analytics/',
         views.WishlistAnalyticsView.as_view(), name='wishlist_analytics'),
    path('wishlists/analytics/summary/', views.WishlistAnalyticsSummaryView.as_view(),
         name='wishlist_analytics_summary'),

    # Quick Actions
    path('wishlists/quick-add/<int:product_id>/',
         views.QuickAddToWishlistView.as_view(), name='quick_add_to_wishlist'),
    path('wishlists/quick-remove/<int:product_id>/',
         views.QuickRemoveFromWishlistView.as_view(), name='quick_remove_from_wishlist'),
]
