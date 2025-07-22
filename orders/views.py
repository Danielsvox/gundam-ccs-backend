from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import Order, OrderItem, OrderStatusHistory, ShippingMethod, TaxRate
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderUpdateSerializer, OrderCancelSerializer, OrderStatusUpdateSerializer,
    OrderTrackingSerializer, OrderSummarySerializer, CheckoutSerializer,
    ShippingMethodSerializer, TaxRateSerializer
)


class OrderListView(generics.ListAPIView):
    """Order list view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderListSerializer

    def get_queryset(self):
        """Get user's orders."""
        return Order.objects.filter(user=self.request.user).select_related('applied_coupon')


class OrderDetailView(generics.RetrieveAPIView):
    """Order detail view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderDetailSerializer

    def get_queryset(self):
        """Get user's orders."""
        return Order.objects.filter(user=self.request.user).select_related('applied_coupon')


class OrderCreateView(APIView):
    """Order create view."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create a new order."""
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                # Get user's cart
                from cart.models import Cart
                try:
                    cart = Cart.objects.get(user=request.user)
                except Cart.DoesNotExist:
                    return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

                if cart.items.count() == 0:
                    return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

                # Calculate order totals
                subtotal = cart.total_price
                shipping_amount = 0  # Will be calculated based on shipping method
                tax_amount = 0  # Will be calculated based on address
                discount_amount = 0

                # Apply coupon if provided
                applied_coupon = None
                coupon_code = serializer.validated_data.get('coupon_code')
                if coupon_code:
                    from cart.models import CartCoupon, AppliedCoupon
                    try:
                        coupon = CartCoupon.objects.get(
                            code=coupon_code.upper())
                        if coupon.is_valid and cart.total_price >= coupon.minimum_purchase:
                            discount_amount = coupon.calculate_discount(
                                cart.total_price)
                            applied_coupon = coupon
                    except CartCoupon.DoesNotExist:
                        pass

                # Calculate tax (simplified - in production, use proper tax calculation)
                tax_rate = 0.085  # 8.5% default tax rate
                tax_amount = (subtotal - discount_amount) * tax_rate

                # Calculate total
                total_amount = subtotal + shipping_amount + tax_amount - discount_amount

                # Create order
                order = Order.objects.create(
                    user=request.user,
                    status='pending',
                    payment_status='pending',
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    shipping_amount=shipping_amount,
                    discount_amount=discount_amount,
                    total_amount=total_amount,
                    shipping_address=serializer.validated_data['shipping_address'],
                    billing_address=serializer.validated_data.get(
                        'billing_address'),
                    customer_notes=serializer.validated_data.get(
                        'customer_notes', ''),
                    applied_coupon=applied_coupon
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

                # Create status history
                OrderStatusHistory.objects.create(
                    order=order,
                    status='pending',
                    notes='Order created'
                )

                # Clear cart
                cart.clear()

                return Response({
                    'message': 'Order created successfully.',
                    'order': OrderDetailSerializer(order).data
                }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderCancelView(APIView):
    """Order cancel view."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        """Cancel an order."""
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not order.can_cancel():
            return Response({'error': 'Order cannot be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Cancel order
            order.cancel()

            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                status='cancelled',
                notes=request.data.get('reason', 'Order cancelled by customer')
            )

            # Restore inventory (if needed)
            for order_item in order.items.all():
                product = order_item.product
                product.stock_quantity += order_item.quantity
                product.save()

        return Response({'message': 'Order cancelled successfully.'}, status=status.HTTP_200_OK)


class OrderTrackingView(APIView):
    """Order tracking view."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_number):
        """Get order tracking information."""
        try:
            order = Order.objects.get(
                order_number=order_number, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderTrackingSerializer(order)
        return Response(serializer.data)


class ShippingMethodListView(generics.ListAPIView):
    """Shipping method list view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = ShippingMethodSerializer
    queryset = ShippingMethod.objects.filter(is_active=True)


class TaxRateListView(generics.ListAPIView):
    """Tax rate list view."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TaxRateSerializer
    queryset = TaxRate.objects.filter(is_active=True)


class CheckoutView(APIView):
    """Checkout view."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Process checkout."""
        serializer = CheckoutSerializer(data=request.data)
        if serializer.is_valid():
            # This would integrate with payment processing
            # For now, just return success
            return Response({
                'message': 'Checkout processed successfully.',
                'redirect_url': '/payment/confirm/'
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_summary(request, order_id):
    """Get order summary."""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = OrderSummarySerializer(order)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_order_status(request, order_id):
    """Update order status (admin only)."""
    if not request.user.is_staff:
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = OrderStatusUpdateSerializer(
        order, data=request.data, partial=True)
    if serializer.is_valid():
        with transaction.atomic():
            old_status = order.status
            serializer.save()

            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                notes=request.data.get(
                    'admin_notes', f'Status changed from {old_status} to {order.status}')
            )

            # Update timestamps for specific statuses
            if order.status == 'shipped':
                order.shipped_at = timezone.now()
                order.save()
            elif order.status == 'delivered':
                order.delivered_at = timezone.now()
                order.save()

        return Response({'message': 'Order status updated successfully.'}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_history(request):
    """Get user's order history."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    serializer = OrderListSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recent_orders(request):
    """Get user's recent orders."""
    orders = Order.objects.filter(
        user=request.user).order_by('-created_at')[:5]
    serializer = OrderListSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_shipping(request):
    """Calculate shipping cost."""
    shipping_method_id = request.data.get('shipping_method_id')
    address = request.data.get('address', {})

    try:
        shipping_method = ShippingMethod.objects.get(
            id=shipping_method_id, is_active=True)
    except ShippingMethod.DoesNotExist:
        return Response({'error': 'Invalid shipping method.'}, status=status.HTTP_400_BAD_REQUEST)

    # In a real application, you would calculate shipping based on address and weight
    shipping_cost = shipping_method.price

    return Response({
        'shipping_method': ShippingMethodSerializer(shipping_method).data,
        'shipping_cost': shipping_cost
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_tax(request):
    """Calculate tax for an address."""
    address = request.data.get('address', {})

    # Get tax rate for the address
    country = address.get('country', 'United States')
    state = address.get('state', '')
    city = address.get('city', '')
    postal_code = address.get('postal_code', '')

    try:
        tax_rate = TaxRate.objects.get(
            country=country,
            state=state,
            city=city,
            postal_code=postal_code,
            is_active=True
        )
    except TaxRate.DoesNotExist:
        # Use default tax rate
        tax_rate = TaxRate.objects.filter(
            country=country,
            is_active=True
        ).first()

    if not tax_rate:
        # Default to 8.5%
        tax_rate_value = 0.085
    else:
        tax_rate_value = tax_rate.rate

    subtotal = request.data.get('subtotal', 0)
    tax_amount = subtotal * tax_rate_value

    return Response({
        'tax_rate': tax_rate_value,
        'tax_amount': tax_amount,
        'tax_percentage': tax_rate_value * 100
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_status_history(request, order_id):
    """Get order status history."""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    from .serializers import OrderStatusHistorySerializer
    history = OrderStatusHistory.objects.filter(
        order=order).order_by('-created_at')
    serializer = OrderStatusHistorySerializer(history, many=True)
    return Response(serializer.data)
