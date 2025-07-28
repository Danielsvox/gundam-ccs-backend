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

    # Stripe Webhook
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
