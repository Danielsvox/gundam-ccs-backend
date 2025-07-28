from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging

from .models import Cart, CartItem, CartCoupon, AppliedCoupon
from .serializers import (
    CartSerializer, CartItemSerializer, CartItemCreateSerializer,
    CartItemUpdateSerializer, CartCouponSerializer, AppliedCouponSerializer,
    ApplyCouponSerializer, CartSummarySerializer
)

logger = logging.getLogger(__name__)


class CartView(APIView):
    """Cart view for getting and clearing cart."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's cart."""
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        except Exception as e:
            logger.error(
                f"Error fetching cart for user {request.user.id}: {str(e)}")
            return Response({
                'error': 'Failed to fetch cart',
                'message': 'An error occurred while loading your cart.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request):
        """Clear user's cart."""
        try:
            cart = Cart.objects.get(user=request.user)
            cart.clear()
            return Response({'message': 'Cart cleared successfully.'}, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({'message': 'Cart is already empty.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Error clearing cart for user {request.user.id}: {str(e)}")
            return Response({
                'error': 'Failed to clear cart',
                'message': 'An error occurred while clearing your cart.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartSummaryView(APIView):
    """Cart summary view."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get cart summary."""
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSummarySerializer(cart)
        return Response(serializer.data)


class CartItemListView(generics.ListCreateAPIView):
    """Cart item list and create view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartItemSerializer

    def get_queryset(self):
        """Get user's cart items."""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart).select_related('product')

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return CartItemCreateSerializer
        return CartItemSerializer

    def perform_create(self, serializer):
        """Create cart item."""
        cart, created = Cart.objects.get_or_create(user=self.request.user)

        # Check if item already exists in cart
        existing_item = CartItem.objects.filter(
            cart=cart,
            product=serializer.validated_data['product']
        ).first()

        if existing_item:
            # Update quantity
            existing_item.quantity += serializer.validated_data.get(
                'quantity', 1)
            existing_item.save()
        else:
            # Create new item
            serializer.save(cart=cart)


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Cart item detail view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartItemUpdateSerializer

    def get_queryset(self):
        """Get user's cart items."""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return CartItem.objects.filter(cart=cart).select_related('product')

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'GET':
            return CartItemSerializer
        return CartItemUpdateSerializer

    def destroy(self, request, *args, **kwargs):
        """Remove item from cart."""
        instance = self.get_object()
        instance.delete()
        return Response({'message': 'Item removed from cart.'}, status=status.HTTP_200_OK)


class ApplyCouponView(APIView):
    """Apply coupon to cart view."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Apply coupon to cart."""
        serializer = ApplyCouponSerializer(data=request.data)
        if serializer.is_valid():
            coupon_code = serializer.validated_data['coupon_code']

            try:
                coupon = CartCoupon.objects.get(code=coupon_code.upper())
            except CartCoupon.DoesNotExist:
                return Response({'error': 'Invalid coupon code.'}, status=status.HTTP_400_BAD_REQUEST)

            if not coupon.is_valid:
                return Response({'error': 'Coupon is not valid.'}, status=status.HTTP_400_BAD_REQUEST)

            cart, created = Cart.objects.get_or_create(user=request.user)

            # Check if coupon is already applied
            if AppliedCoupon.objects.filter(cart=cart, coupon=coupon).exists():
                return Response({'error': 'Coupon is already applied.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check minimum purchase requirement
            if cart.total_price < coupon.minimum_purchase:
                return Response({
                    'error': f'Minimum purchase of ${coupon.minimum_purchase} required.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate discount
            discount_amount = coupon.calculate_discount(cart.total_price)

            # Apply coupon
            AppliedCoupon.objects.create(
                cart=cart,
                coupon=coupon,
                discount_amount=discount_amount
            )

            # Update coupon usage count
            coupon.used_count += 1
            coupon.save()

            return Response({
                'message': 'Coupon applied successfully.',
                'discount_amount': discount_amount
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveCouponView(APIView):
    """Remove coupon from cart view."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, coupon_id):
        """Remove coupon from cart."""
        cart, created = Cart.objects.get_or_create(user=request.user)

        try:
            applied_coupon = AppliedCoupon.objects.get(cart=cart, id=coupon_id)
            applied_coupon.delete()

            return Response({'message': 'Coupon removed successfully.'}, status=status.HTTP_200_OK)
        except AppliedCoupon.DoesNotExist:
            return Response({'error': 'Coupon not found in cart.'}, status=status.HTTP_404_NOT_FOUND)


class CartCouponListView(generics.ListAPIView):
    """Cart coupon list view (admin only)."""

    permission_classes = [permissions.IsAdminUser]
    serializer_class = CartCouponSerializer
    queryset = CartCoupon.objects.all()


class AppliedCouponListView(generics.ListAPIView):
    """Applied coupon list view."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppliedCouponSerializer

    def get_queryset(self):
        """Get applied coupons for user's cart."""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return AppliedCoupon.objects.filter(cart=cart).select_related('coupon')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_cart_item_quantity(request, item_id):
    """Update cart item quantity."""
    try:
        cart_item = CartItem.objects.get(
            id=item_id,
            cart__user=request.user
        )
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

    quantity = request.data.get('quantity')
    if not quantity or quantity <= 0:
        return Response({'error': 'Valid quantity is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Check stock availability
    if quantity > cart_item.product.stock_quantity:
        return Response({
            'error': f'Only {cart_item.product.stock_quantity} items available in stock.'
        }, status=status.HTTP_400_BAD_REQUEST)

    cart_item.quantity = quantity
    cart_item.save()

    serializer = CartItemSerializer(cart_item)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_to_cart(request):
    """Add product to cart."""
    serializer = CartItemCreateSerializer(data=request.data)
    if serializer.is_valid():
        cart, created = Cart.objects.get_or_create(user=request.user)
        product = serializer.validated_data['product']
        quantity = serializer.validated_data.get('quantity', 1)

        # Check if item already exists in cart
        existing_item = CartItem.objects.filter(
            cart=cart,
            product=product
        ).first()

        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + quantity
            if new_quantity > product.stock_quantity:
                return Response({
                    'error': f'Only {product.stock_quantity} items available in stock.'
                }, status=status.HTTP_400_BAD_REQUEST)

            existing_item.quantity = new_quantity
            existing_item.save()
            cart_item = existing_item
        else:
            # Create new item
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )

        serializer = CartItemSerializer(cart_item)
        return Response({
            'message': 'Product added to cart successfully.',
            'cart_item': serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_from_cart(request, item_id):
    """Remove product from cart."""
    try:
        cart_item = CartItem.objects.get(
            id=item_id,
            cart__user=request.user
        )
        cart_item.delete()
        return Response({'message': 'Product removed from cart successfully.'}, status=status.HTTP_200_OK)
    except CartItem.DoesNotExist:
        return Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def cart_count(request):
    """Get cart item count."""
    cart, created = Cart.objects.get_or_create(user=request.user)
    count = cart.total_items
    return Response({'count': count})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def merge_cart(request):
    """Merge guest cart with user cart."""
    guest_cart_data = request.data.get('guest_cart', [])

    if not guest_cart_data:
        return Response({'message': 'No guest cart data provided.'}, status=status.HTTP_200_OK)

    cart, created = Cart.objects.get_or_create(user=request.user)

    with transaction.atomic():
        for item_data in guest_cart_data:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity', 1)

            try:
                from products.models import Product
                product = Product.objects.get(id=product_id, is_active=True)
            except Product.DoesNotExist:
                continue

            # Check if item already exists in cart
            existing_item = CartItem.objects.filter(
                cart=cart,
                product=product
            ).first()

            if existing_item:
                # Update quantity
                new_quantity = existing_item.quantity + quantity
                if new_quantity <= product.stock_quantity:
                    existing_item.quantity = new_quantity
                    existing_item.save()
            else:
                # Create new item
                if quantity <= product.stock_quantity:
                    CartItem.objects.create(
                        cart=cart,
                        product=product,
                        quantity=quantity
                    )

    return Response({'message': 'Cart merged successfully.'}, status=status.HTTP_200_OK)
