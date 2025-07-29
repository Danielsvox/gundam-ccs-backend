from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Checkout and Payment Processing
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('create-payment-intent/', views.CreatePaymentIntentView.as_view(),
         name='create_payment_intent'),
    path('confirm-payment/', views.ConfirmPaymentView.as_view(),
         name='confirm_payment'),
    path('confirm-manual-payment/', views.confirm_manual_payment,
         name='confirm_manual_payment'),

    # Payment Methods
    path('payment-methods/', views.PaymentMethodListView.as_view(),
         name='payment_method_list'),
    path('payment-methods/<int:pk>/',
         views.PaymentMethodDetailView.as_view(), name='payment_method_detail'),
    path('payment-methods/create/', views.create_payment_method,
         name='create_payment_method'),

    # Exchange Rate Endpoints
    path('exchange-rate/', views.ExchangeRateCurrentView.as_view(), name='exchange_rate_current'),
    path('exchange-rate/history/', views.ExchangeRateHistoryView.as_view(), name='exchange_rate_history'),
    path('exchange-rate/at-timestamp/', views.ExchangeRateAtTimestampView.as_view(), name='exchange_rate_at_timestamp'),
    path('exchange-rate/convert/', views.CurrencyConversionView.as_view(), name='currency_conversion'),
    path('exchange-rate/set-manual/', views.ManualRateSetView.as_view(), name='manual_rate_set'),
    path('exchange-rate/refresh/', views.ExchangeRateRefreshView.as_view(), name='exchange_rate_refresh'),
    path('exchange-rate/stats/', views.ExchangeRateStatsView.as_view(), name='exchange_rate_stats'),
    path('exchange-rate/alerts/', views.ExchangeRateAlertsView.as_view(), name='exchange_rate_alerts'),
    path('exchange-rate/alerts/<int:alert_id>/acknowledge/', views.ExchangeRateAlertAcknowledgeView.as_view(), name='exchange_rate_alert_acknowledge'),

    # Stripe Webhook
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),

    # Pago Móvil Endpoints
    path('pagomovil/info/', views.PagoMovilPaymentInfoView.as_view(), name='pagomovil_payment_info'),
    path('pagomovil/verify/', views.PagoMovilVerificationCreateView.as_view(), name='pagomovil_verify'),
    path('pagomovil/status/', views.PagoMovilStatusView.as_view(), name='pagomovil_status'),
    path('pagomovil/admin/', views.PagoMovilAdminListView.as_view(), name='pagomovil_admin_list'),
    path('pagomovil/<int:verification_id>/status/', views.PagoMovilStatusUpdateView.as_view(), name='pagomovil_status_update'),
    path('pagomovil/banks/', views.PagoMovilBankCodeListView.as_view(), name='pagomovil_banks'),
    path('pagomovil/recipients/', views.PagoMovilRecipientListView.as_view(), name='pagomovil_recipients'),
]
