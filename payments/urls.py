from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payments
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/create/', views.CreatePaymentView.as_view(),
         name='create_payment'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(),
         name='payment_detail'),
    path('payments/<int:pk>/confirm/',
         views.ConfirmPaymentView.as_view(), name='confirm_payment'),
    path('payments/<int:pk>/cancel/',
         views.CancelPaymentView.as_view(), name='cancel_payment'),

    # Payment Methods
    path('payment-methods/', views.PaymentMethodListView.as_view(),
         name='payment_method_list'),
    path('payment-methods/create/', views.CreatePaymentMethodView.as_view(),
         name='create_payment_method'),
    path('payment-methods/<int:pk>/',
         views.PaymentMethodDetailView.as_view(), name='payment_method_detail'),
    path('payment-methods/<int:pk>/update/',
         views.UpdatePaymentMethodView.as_view(), name='update_payment_method'),
    path('payment-methods/<int:pk>/delete/',
         views.DeletePaymentMethodView.as_view(), name='delete_payment_method'),
    path('payment-methods/<int:pk>/set-default/',
         views.SetDefaultPaymentMethodView.as_view(), name='set_default_payment_method'),

    # Refunds
    path('refunds/', views.RefundListView.as_view(), name='refund_list'),
    path('refunds/create/', views.CreateRefundView.as_view(), name='create_refund'),
    path('refunds/<int:pk>/', views.RefundDetailView.as_view(), name='refund_detail'),
    path('refunds/<int:pk>/cancel/',
         views.CancelRefundView.as_view(), name='cancel_refund'),

    # Subscriptions
    path('subscriptions/', views.SubscriptionListView.as_view(),
         name='subscription_list'),
    path('subscriptions/create/', views.CreateSubscriptionView.as_view(),
         name='create_subscription'),
    path('subscriptions/<int:pk>/',
         views.SubscriptionDetailView.as_view(), name='subscription_detail'),
    path('subscriptions/<int:pk>/cancel/',
         views.CancelSubscriptionView.as_view(), name='cancel_subscription'),
    path('subscriptions/<int:pk>/pause/',
         views.PauseSubscriptionView.as_view(), name='pause_subscription'),
    path('subscriptions/<int:pk>/resume/',
         views.ResumeSubscriptionView.as_view(), name='resume_subscription'),

    # Webhooks
    path('webhooks/stripe/', views.StripeWebhookView.as_view(),
         name='stripe_webhook'),
    path('webhooks/events/', views.WebhookEventListView.as_view(),
         name='webhook_events'),
    path('webhooks/events/<int:pk>/',
         views.WebhookEventDetailView.as_view(), name='webhook_event_detail'),

    # Payment Intent
    path('payment-intent/create/', views.CreatePaymentIntentView.as_view(),
         name='create_payment_intent'),
    path('payment-intent/<str:payment_intent_id>/',
         views.PaymentIntentDetailView.as_view(), name='payment_intent_detail'),
    path('payment-intent/<str:payment_intent_id>/confirm/',
         views.ConfirmPaymentIntentView.as_view(), name='confirm_payment_intent'),
]
