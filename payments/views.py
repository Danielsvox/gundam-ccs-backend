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
