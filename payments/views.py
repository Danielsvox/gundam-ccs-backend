import stripe
import logging
from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser

from .models import Payment, PaymentMethod, WebhookEvent
from .serializers import (
    PaymentSerializer, PaymentMethodSerializer,
    CreatePaymentIntentSerializer, ConfirmPaymentSerializer
)
from .services import payment_processor, whatsapp_service
from orders.models import Order, OrderItem
from cart.models import Cart
from .services.exchange_rate_service import exchange_rate_service
from .serializers import (
    ExchangeRateSerializer, ExchangeRateCurrentSerializer, ExchangeRateHistorySerializer,
    ManualRateSetSerializer, CurrencyConversionSerializer, CurrencyConversionResponseSerializer,
    ExchangeRateAlertSerializer, ExchangeRateSnapshotSerializer,
    PagoMovilBankCodeSerializer, PagoMovilRecipientSerializer, PagoMovilVerificationRequestSerializer,
    PagoMovilVerificationCreateSerializer, PagoMovilStatusUpdateSerializer, PagoMovilPaymentInfoSerializer
)
from .models import (
    ExchangeRateLog, ExchangeRateAlert, ExchangeRateSnapshot,
    PagoMovilBankCode, PagoMovilRecipient, PagoMovilVerificationRequest
)
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class CreatePaymentIntentView(APIView):
    """Create a Stripe payment intent for checkout."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create payment intent for order checkout."""
        serializer = CreatePaymentIntentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                order_id = serializer.validated_data['order_id']
                order = get_object_or_404(
                    Order, id=order_id, user=request.user)

                # Create payment intent
                intent = stripe.PaymentIntent.create(
                    amount=int(order.total_amount * 100),  # Convert to cents
                    currency='usd',
                    metadata={
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'user_id': request.user.id
                    },
                    description=f"Order {order.order_number} - Gundam CCS"
                )

                # Create payment record
                payment = Payment.objects.create(
                    order=order,
                    user=request.user,
                    amount=order.total_amount,
                    currency='USD',
                    payment_method='stripe',
                    status='pending',
                    stripe_payment_intent_id=intent.id
                )

                # Send initial order notification
                payment_processor.process_new_order(order)

                return Response({
                    'client_secret': intent.client_secret,
                    'payment_intent_id': intent.id,
                    'order_number': order.order_number,
                    'amount': order.total_amount
                })

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error creating payment intent: {str(e)}")
                return Response({
                    'error': 'Payment processing error. Please try again.'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error creating payment intent: {str(e)}")
                return Response({
                    'error': 'An unexpected error occurred.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfirmPaymentView(APIView):
    """Confirm payment and process order."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Confirm payment and update order status."""
        serializer = ConfirmPaymentIntentSerializer(data=request.data)
        if serializer.is_valid():
            try:
                payment_intent_id = serializer.validated_data['payment_intent_id']

                # Retrieve payment intent from Stripe
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)

                if intent.status == 'succeeded':
                    # Get payment record
                    payment = get_object_or_404(
                        Payment,
                        stripe_payment_intent_id=payment_intent_id,
                        user=request.user
                    )

                    # Update payment status
                    payment.status = 'succeeded'
                    payment.stripe_charge_id = intent.latest_charge
                    payment.save()

                    # Process successful payment
                    success = payment_processor.process_successful_payment(
                        payment.order, payment)

                    if success:
                        return Response({
                            'message': 'Payment confirmed successfully!',
                            'order_number': payment.order.order_number,
                            'status': 'success'
                        })
                    else:
                        return Response({
                            'error': 'Payment confirmed but order processing failed.'
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                elif intent.status == 'requires_payment_method':
                    return Response({
                        'error': 'Payment method required.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                elif intent.status == 'requires_confirmation':
                    return Response({
                        'error': 'Payment requires confirmation.'
                    }, status=status.HTTP_400_BAD_REQUEST)

                else:
                    return Response({
                        'error': f'Payment status: {intent.status}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            except stripe.error.StripeError as e:
                logger.error(f"Stripe error confirming payment: {str(e)}")
                return Response({
                    'error': 'Payment confirmation error.'
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error confirming payment: {str(e)}")
                return Response({
                    'error': 'An unexpected error occurred.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckoutView(APIView):
    """Complete checkout process - create order for manual payment."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Process checkout and create order for manual payment."""
        try:
            # Get user's cart
            cart, created = Cart.objects.get_or_create(user=request.user)

            if not cart.items.exists():
                return Response({
                    'error': 'Cart is empty.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Extract checkout data
            shipping_address = request.data.get('shipping_address', {})
            billing_address = request.data.get('billing_address', {})
            customer_notes = request.data.get('customer_notes', '')
            shipping_method_id = request.data.get('shipping_method_id')

            # Validate required fields
            if not shipping_address:
                return Response({
                    'error': 'Shipping address is required.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate totals
            subtotal = cart.total_price
            tax_amount = cart.total_price_with_tax - cart.total_price
            shipping_amount = Decimal('0.00')  # Default free shipping

            # Get shipping method if provided
            if shipping_method_id:
                from orders.models import ShippingMethod
                try:
                    shipping_method = ShippingMethod.objects.get(
                        id=shipping_method_id, is_active=True
                    )
                    shipping_amount = shipping_method.price
                except ShippingMethod.DoesNotExist:
                    return Response({
                        'error': 'Invalid shipping method.'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate discount from applied coupons
            discount_amount = sum(
                coupon.discount_amount for coupon in cart.applied_coupons.all()
            )

            # Calculate total
            total_amount = subtotal + tax_amount + shipping_amount - discount_amount

            # Create order
            order = Order.objects.create(
                user=request.user,
                subtotal=subtotal,
                tax_amount=tax_amount,
                shipping_amount=shipping_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                shipping_address=shipping_address,
                billing_address=billing_address or shipping_address,
                customer_notes=customer_notes,
                status='pending',
                payment_status='pending'
            )

            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    product_sku=cart_item.product.sku,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.product.current_price,
                    total_price=cart_item.total_price
                )

            # Apply coupon if any
            applied_coupons = cart.applied_coupons.all()
            if applied_coupons.exists():
                order.applied_coupon = applied_coupons.first().coupon
                order.save()

            # Create manual payment record (no Stripe integration)
            payment = Payment.objects.create(
                order=order,
                user=request.user,
                amount=total_amount,
                currency='USD',
                payment_method='manual',
                status='pending'
            )

            # Clear cart after successful order creation
            cart.clear()

            # Send WhatsApp notification for new order
            payment_processor.process_new_order(order)

            return Response({
                'order_id': order.id,
                'order_number': order.order_number,
                'amount': total_amount,
                'payment_status': 'pending',
                'payment_method': 'manual',
                'message': 'Order created successfully! Payment will be processed manually.',
                'success': True
            })

        except Exception as e:
            logger.error(f"Error in checkout process: {str(e)}")
            return Response({
                'error': 'An unexpected error occurred during checkout.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentMethodListView(generics.ListCreateAPIView):
    """List and create payment methods."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete payment methods."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhooks."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Store webhook event
    webhook_event = WebhookEvent.objects.create(
        stripe_event_id=event['id'],
        event_type=event['type'],
        api_version=event.get('api_version', ''),
        created=event['created'],
        livemode=event['livemode'],
        data=event['data']
    )

    try:
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            handle_payment_success(event['data']['object'])
        elif event['type'] == 'payment_intent.payment_failed':
            handle_payment_failure(event['data']['object'])
        elif event['type'] == 'charge.refunded':
            handle_refund(event['data']['object'])

        webhook_event.processed = True
        webhook_event.save()

    except Exception as e:
        webhook_event.processing_error = str(e)
        webhook_event.save()
        logger.error(f"Error processing webhook {event['type']}: {str(e)}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)

    return JsonResponse({'status': 'success'})


def handle_payment_success(payment_intent):
    """Handle successful payment."""
    try:
        payment = Payment.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )

        payment.status = 'succeeded'
        payment.stripe_charge_id = payment_intent.get('latest_charge')
        payment.save()

        # Process successful payment
        payment_processor.process_successful_payment(payment.order, payment)

        logger.info(
            f"Payment succeeded for order {payment.order.order_number}")

    except Payment.DoesNotExist:
        logger.error(f"Payment not found for intent {payment_intent['id']}")
    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")


def handle_payment_failure(payment_intent):
    """Handle failed payment."""
    try:
        payment = Payment.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )

        payment.status = 'failed'
        payment.error_message = payment_intent.get(
            'last_payment_error', {}).get('message', '')
        payment.save()

        logger.info(f"Payment failed for order {payment.order.order_number}")

    except Payment.DoesNotExist:
        logger.error(f"Payment not found for intent {payment_intent['id']}")
    except Exception as e:
        logger.error(f"Error handling payment failure: {str(e)}")


def handle_refund(charge):
    """Handle refund."""
    try:
        payment = Payment.objects.get(stripe_charge_id=charge['id'])

        # Create refund record
        from .models import Refund
        Refund.objects.create(
            payment=payment,
            amount=Decimal(charge['amount_refunded']) / 100,
            currency=charge['currency'].upper(),
            status='succeeded',
            stripe_refund_id=charge['refunds']['data'][0]['id'] if charge['refunds']['data'] else ''
        )

        payment.status = 'refunded'
        payment.save()

        logger.info(f"Refund processed for order {payment.order.order_number}")

    except Payment.DoesNotExist:
        logger.error(f"Payment not found for charge {charge['id']}")
    except Exception as e:
        logger.error(f"Error handling refund: {str(e)}")


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_manual_payment(request):
    """Confirm manual payment for an order."""
    try:
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({
                'error': 'Order ID is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get the order and payment
        order = get_object_or_404(Order, id=order_id)
        payment = get_object_or_404(
            Payment, order=order, payment_method='manual')

        # Update payment status
        payment.status = 'succeeded'
        payment.save()

        # Update order status
        order.payment_status = 'paid'
        order.status = 'confirmed'
        order.save()

        # Create status history entry
        from orders.models import OrderStatusHistory
        OrderStatusHistory.objects.create(
            order=order,
            status='confirmed',
            notes='Manual payment confirmed by business owner'
        )

        # Send WhatsApp notification
        payment_processor.process_successful_payment(order, payment)

        return Response({
            'message': 'Manual payment confirmed successfully!',
            'order_number': order.order_number,
            'status': 'success'
        })

    except Exception as e:
        logger.error(f"Error confirming manual payment: {str(e)}")
        return Response({
            'error': 'An unexpected error occurred.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_methods(request):
    """Get user's payment methods."""
    payment_methods = PaymentMethod.objects.filter(user=request.user)
    serializer = PaymentMethodSerializer(payment_methods, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_payment_method(request):
    """Create a new payment method."""
    serializer = PaymentMethodSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExchangeRateCurrentView(APIView):
    """Get current USD to VES exchange rate."""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get current exchange rate."""
        try:
            force_fetch = request.query_params.get('force_fetch', 'false').lower() == 'true'
            rate_data = exchange_rate_service.get_current_rate(force_fetch=force_fetch)
            
            if rate_data:
                return Response(rate_data)
            else:
                return Response({
                    'error': 'Unable to fetch current exchange rate'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
        except Exception as e:
            logger.error(f"Error getting current exchange rate: {str(e)}")
            return Response({
                'error': 'An error occurred while fetching exchange rate'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExchangeRateHistoryView(generics.ListAPIView):
    """Get exchange rate history with filtering and pagination."""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = ExchangeRateHistorySerializer
    pagination_class = None  # Use default pagination
    
    def get_queryset(self):
        """Get filtered exchange rate history."""
        queryset = ExchangeRateLog.objects.all()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = timezone.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = timezone.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_date)
            except ValueError:
                pass
        
        # Filter by source
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)
        
        # Filter by fetch success
        fetch_success = self.request.query_params.get('fetch_success')
        if fetch_success is not None:
            queryset = queryset.filter(fetch_success=fetch_success.lower() == 'true')
        
        return queryset.order_by('-timestamp')


class ExchangeRateAtTimestampView(APIView):
    """Get exchange rate that was active at a specific timestamp."""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get exchange rate at specific timestamp."""
        try:
            timestamp_str = request.query_params.get('timestamp')
            if not timestamp_str:
                return Response({
                    'error': 'timestamp parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                timestamp = timezone.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                return Response({
                    'error': 'Invalid timestamp format. Use ISO format.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            rate_log = ExchangeRateLog.get_rate_at_timestamp(timestamp)
            
            if rate_log:
                serializer = ExchangeRateSerializer(rate_log)
                return Response(serializer.data)
            else:
                return Response({
                    'error': 'No exchange rate found for the specified timestamp'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error getting exchange rate at timestamp: {str(e)}")
            return Response({
                'error': 'An error occurred while fetching historical rate'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CurrencyConversionView(APIView):
    """Convert between USD and VES currencies."""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Convert currency amount."""
        try:
            serializer = CurrencyConversionSerializer(data=request.data)
            if serializer.is_valid():
                data = serializer.validated_data
                
                amount = data['amount']
                from_currency = data['from_currency']
                to_currency = data['to_currency']
                specific_rate = data.get('rate')
                
                # Get current rate if not provided
                if specific_rate:
                    rate = Decimal(str(specific_rate))
                    rate_source = 'manual'
                else:
                    rate_data = exchange_rate_service.get_current_rate()
                    if not rate_data:
                        return Response({
                            'error': 'Unable to fetch current exchange rate'
                        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                    
                    rate = Decimal(str(rate_data['usd_to_ves']))
                    rate_source = rate_data['source']
                
                # Perform conversion
                if from_currency == 'USD' and to_currency == 'VES':
                    converted_amount = exchange_rate_service.convert_usd_to_ves(amount, rate)
                elif from_currency == 'VES' and to_currency == 'USD':
                    converted_amount = exchange_rate_service.convert_ves_to_usd(amount, rate)
                else:
                    return Response({
                        'error': 'Invalid currency combination'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                response_data = {
                    'original_amount': amount,
                    'converted_amount': round(converted_amount, 2),
                    'from_currency': from_currency,
                    'to_currency': to_currency,
                    'exchange_rate': rate,
                    'rate_source': rate_source,
                    'conversion_timestamp': timezone.now()
                }
                
                response_serializer = CurrencyConversionResponseSerializer(response_data)
                return Response(response_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error in currency conversion: {str(e)}")
            return Response({
                'error': 'An error occurred during currency conversion'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ManualRateSetView(APIView):
    """Set manual exchange rate (admin only)."""
    
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def post(self, request):
        """Set manual exchange rate."""
        try:
            serializer = ManualRateSetSerializer(data=request.data)
            if serializer.is_valid():
                rate = serializer.validated_data['rate']
                
                # Set manual rate
                rate_data = exchange_rate_service.set_manual_rate(rate, request.user)
                
                return Response({
                    'message': 'Manual exchange rate set successfully',
                    'rate_data': rate_data
                })
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error setting manual rate: {str(e)}")
            return Response({
                'error': 'An error occurred while setting manual rate'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExchangeRateRefreshView(APIView):
    """Force refresh exchange rate from external sources."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Force refresh exchange rate."""
        try:
            rate_data = exchange_rate_service.fetch_and_store_rate()
            
            if rate_data:
                return Response({
                    'message': 'Exchange rate refreshed successfully',
                    'rate_data': rate_data
                })
            else:
                return Response({
                    'error': 'Failed to refresh exchange rate'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
        except Exception as e:
            logger.error(f"Error refreshing exchange rate: {str(e)}")
            return Response({
                'error': 'An error occurred while refreshing exchange rate'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExchangeRateAlertsView(generics.ListAPIView):
    """List exchange rate alerts."""
    
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = ExchangeRateAlertSerializer
    
    def get_queryset(self):
        """Get filtered alerts."""
        queryset = ExchangeRateAlert.objects.all()
        
        # Filter by acknowledgment status
        acknowledged = self.request.query_params.get('acknowledged')
        if acknowledged is not None:
            queryset = queryset.filter(acknowledged=acknowledged.lower() == 'true')
        
        # Filter by alert type
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        return queryset.order_by('-created_at')


class ExchangeRateAlertAcknowledgeView(APIView):
    """Acknowledge exchange rate alert."""
    
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def post(self, request, alert_id):
        """Acknowledge alert."""
        try:
            alert = ExchangeRateAlert.objects.get(id=alert_id)
            alert.acknowledged = True
            alert.acknowledged_by = request.user
            alert.acknowledged_at = timezone.now()
            alert.save()
            
            serializer = ExchangeRateAlertSerializer(alert)
            return Response({
                'message': 'Alert acknowledged successfully',
                'alert': serializer.data
            })
            
        except ExchangeRateAlert.DoesNotExist:
            return Response({
                'error': 'Alert not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error acknowledging alert: {str(e)}")
            return Response({
                'error': 'An error occurred while acknowledging alert'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExchangeRateStatsView(APIView):
    """Get exchange rate statistics."""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get exchange rate statistics."""
        try:
            # Get date range from query params (default to last 30 days)
            days = int(request.query_params.get('days', 30))
            start_date = timezone.now() - timezone.timedelta(days=days)
            
            rates = ExchangeRateLog.objects.filter(
                timestamp__gte=start_date,
                fetch_success=True
            ).order_by('timestamp')
            
            if not rates.exists():
                return Response({
                    'error': 'No rate data available for the specified period'
                }, status=status.HTTP_404_NOT_FOUND)
            
            rates_values = [float(rate.usd_to_ves) for rate in rates]
            
            stats = {
                'period_days': days,
                'total_updates': rates.count(),
                'current_rate': rates_values[-1] if rates_values else None,
                'highest_rate': max(rates_values) if rates_values else None,
                'lowest_rate': min(rates_values) if rates_values else None,
                'average_rate': sum(rates_values) / len(rates_values) if rates_values else None,
                'total_change': rates_values[-1] - rates_values[0] if len(rates_values) > 1 else 0,
                'total_change_percentage': ((rates_values[-1] - rates_values[0]) / rates_values[0] * 100) if len(rates_values) > 1 else 0,
                'successful_fetches': rates.filter(fetch_success=True).count(),
                'failed_fetches': ExchangeRateLog.objects.filter(
                    timestamp__gte=start_date,
                    fetch_success=False
                ).count(),
                'source_breakdown': {}
            }
            
            # Get source breakdown
            from django.db.models import Count
            source_stats = rates.values('source').annotate(count=Count('source'))
            for stat in source_stats:
                stats['source_breakdown'][stat['source']] = stat['count']
            
            return Response(stats)
            
        except Exception as e:
            logger.error(f"Error getting exchange rate stats: {str(e)}")
            return Response({
                'error': 'An error occurred while fetching statistics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PagoMovilPaymentInfoView(APIView):
    """Get Pago Móvil payment information for checkout."""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Get Pago Móvil payment information."""
        try:
            # Get active bank codes
            bank_codes = PagoMovilBankCode.objects.filter(is_active=True)
            
            # Get active recipients
            recipients = PagoMovilRecipient.objects.filter(is_active=True)
            
            # Get current exchange rate
            from .services.exchange_rate_service import exchange_rate_service
            rate_data = exchange_rate_service.get_current_rate()
            current_rate = rate_data['usd_to_ves'] if rate_data else 38.0
            
            # Payment instructions
            instructions = """
            📱 Pago Móvil Instructions:
            
            1. Select your bank from the list below
            2. Use the recipient information provided
            3. Transfer the amount in Bolívares (VES)
            4. Submit verification form after transfer
            5. Wait for admin approval (usually within 24 hours)
            
            💡 Tip: Keep your transfer receipt for reference
            """
            
            data = {
                'bank_codes': PagoMovilBankCodeSerializer(bank_codes, many=True).data,
                'recipients': PagoMovilRecipientSerializer(recipients, many=True).data,
                'current_exchange_rate': current_rate,
                'instructions': instructions.strip()
            }
            
            return Response(data)
            
        except Exception as e:
            logger.error(f"Error getting Pago Móvil payment info: {str(e)}")
            return Response({
                'error': 'An error occurred while fetching payment information'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PagoMovilVerificationCreateView(APIView):
    """Create a Pago Móvil verification request."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Create verification request."""
        try:
            serializer = PagoMovilVerificationCreateSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                # Get current exchange rate
                from .services.exchange_rate_service import exchange_rate_service
                try:
                    rate_data = exchange_rate_service.get_current_rate()
                    exchange_rate = Decimal(str(rate_data['usd_to_ves'])) if rate_data else Decimal('38.0')
                except Exception as e:
                    logger.warning(f"Failed to get current exchange rate: {str(e)}")
                    exchange_rate = Decimal('38.0')
                
                # Create verification request
                verification_request = serializer.save(
                    user=request.user,
                    exchange_rate_used=exchange_rate
                )
                
                # Send WhatsApp notification to admin (non-blocking)
                try:
                    self._send_admin_notification(verification_request)
                except Exception as e:
                    logger.warning(f"WhatsApp notification failed but continuing: {str(e)}")
                
                # Return the created request
                response_serializer = PagoMovilVerificationRequestSerializer(verification_request)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error creating Pago Móvil verification: {str(e)}")
            return Response({
                'error': 'An error occurred while creating verification request'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _send_admin_notification(self, verification_request):
        """Send WhatsApp notification to admin."""
        try:
            from .services.whatsapp_service import whatsapp_service
            
            # Get admin phone number from settings
            admin_phone = getattr(settings, 'ADMIN_WHATSAPP_PHONE', None)
            if not admin_phone:
                logger.warning("Admin WhatsApp phone not configured")
                return
            
            # Create notification message
            message = f"""📱 Pago Móvil Verification Request

👤 User: {verification_request.user.email}
🆔 Sender ID: {verification_request.formatted_sender_id}
📞 Phone: {verification_request.sender_phone}
💰 Amount: {verification_request.formatted_amount} (≈ {verification_request.formatted_usd_equivalent})
🏦 Bank: {verification_request.bank_code.bank_name}
📅 Timestamp: {verification_request.created_at.strftime('%Y-%m-%d %H:%M')}
📊 Status: Pending

🔗 Review: /admin/payments/pagomovilverificationrequest/{verification_request.id}/"""
            
            # Send notification
            whatsapp_service.send_custom_message(admin_phone, message)
            
        except Exception as e:
            logger.error(f"Error sending admin notification: {str(e)}")


class PagoMovilStatusView(APIView):
    """Get user's latest Pago Móvil verification status."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user's latest verification status."""
        try:
            # Get user's latest verification request
            latest_request = PagoMovilVerificationRequest.objects.filter(
                user=request.user
            ).order_by('-created_at').first()
            
            if latest_request:
                serializer = PagoMovilVerificationRequestSerializer(latest_request)
                return Response(serializer.data)
            else:
                return Response({
                    'message': 'No verification requests found'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Error getting Pago Móvil status: {str(e)}")
            return Response({
                'error': 'An error occurred while fetching status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PagoMovilAdminListView(generics.ListAPIView):
    """Admin view to list and filter Pago Móvil verification requests."""
    
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = PagoMovilVerificationRequestSerializer
    
    def get_queryset(self):
        """Get filtered verification requests."""
        queryset = PagoMovilVerificationRequest.objects.all()
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = timezone.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = timezone.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__lte=end_date)
            except ValueError:
                pass
        
        # Filter by user email
        user_email = self.request.query_params.get('user_email')
        if user_email:
            queryset = queryset.filter(user__email__icontains=user_email)
        
        return queryset.select_related('user', 'bank_code', 'recipient', 'approved_by')


class PagoMovilStatusUpdateView(APIView):
    """Admin view to update Pago Móvil verification status."""
    
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def patch(self, request, verification_id):
        """Update verification status."""
        try:
            verification_request = get_object_or_404(
                PagoMovilVerificationRequest,
                id=verification_id
            )
            
            serializer = PagoMovilStatusUpdateSerializer(data=request.data)
            if serializer.is_valid():
                new_status = serializer.validated_data['status']
                notes = serializer.validated_data.get('notes', '')
                
                if new_status == 'approved':
                    verification_request.approve(request.user)
                    if notes:
                        verification_request.notes = notes
                        verification_request.save()
                elif new_status == 'rejected':
                    verification_request.reject(request.user, notes)
                
                # Send notification to user
                self._send_user_notification(verification_request)
                
                response_serializer = PagoMovilVerificationRequestSerializer(verification_request)
                return Response(response_serializer.data)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error updating Pago Móvil status: {str(e)}")
            return Response({
                'error': 'An error occurred while updating status'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _send_user_notification(self, verification_request):
        """Send notification to user about status update."""
        try:
            from .services.whatsapp_service import whatsapp_service
            
            # Get user's phone number from the verification request
            user_phone = verification_request.sender_phone
            
            # Format phone number for WhatsApp
            if user_phone:
                # Add country code if not present
                if not user_phone.startswith('58'):
                    user_phone = '58' + user_phone.replace('+', '')
                
                status_emoji = "✅" if verification_request.status == 'approved' else "❌"
                status_text = "approved" if verification_request.status == 'approved' else "rejected"
                
                message = f"""{status_emoji} Pago Móvil Payment {status_text.title()}

💰 Amount: {verification_request.formatted_amount}
🆔 Sender ID: {verification_request.formatted_sender_id}
📅 Processed: {verification_request.approved_at.strftime('%Y-%m-%d %H:%M')}

{status_emoji} Status: {status_text.title()}

Thank you for your payment! 🚀"""
                
                # Send notification
                whatsapp_service.send_custom_message(user_phone, message)
                
        except Exception as e:
            logger.error(f"Error sending user notification: {str(e)}")


class PagoMovilBankCodeListView(generics.ListAPIView):
    """List Pago Móvil bank codes."""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = PagoMovilBankCodeSerializer
    
    def get_queryset(self):
        """Get active bank codes."""
        return PagoMovilBankCode.objects.filter(is_active=True)


class PagoMovilRecipientListView(generics.ListAPIView):
    """List Pago Móvil recipients."""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = PagoMovilRecipientSerializer
    
    def get_queryset(self):
        """Get active recipients."""
        return PagoMovilRecipient.objects.filter(is_active=True)
