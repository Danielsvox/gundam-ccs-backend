#!/usr/bin/env python3
"""
Test script for WhatsApp notification system
"""

# Setup Django environment first
from payments.services import whatsapp_service, payment_processor
from payments.models import Payment
from products.models import Product, Category
from orders.models import Order, OrderItem
from django.contrib.auth import get_user_model
from decimal import Decimal
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gundam_ccs.settings')

# Configure Django
django.setup()

# Now import Django modules


User = get_user_model()


def create_test_order():
    """Create a test order for notification testing."""

    # Get or create test user
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )

    # Get or create test category
    category, created = Category.objects.get_or_create(
        name='Test Category',
        defaults={
            'slug': 'test-category',
            'description': 'Test category for notifications'
        }
    )

    # Get or create test product
    product, created = Product.objects.get_or_create(
        name='Test Gundam Model',
        defaults={
            'slug': 'test-gundam-model',
            'description': 'A test Gundam model for notification testing',
            'short_description': 'Test model',
            'price': Decimal('150.00'),
            'category': category,
            'grade': 'MG',
            'manufacturer': 'Bandai',
            'stock_quantity': 10,
            'sku': 'TEST-001'
        }
    )

    # Create test order
    order = Order.objects.create(
        user=user,
        subtotal=Decimal('150.00'),
        tax_amount=Decimal('12.75'),
        shipping_amount=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        total_amount=Decimal('162.75'),
        shipping_address={
            'name': 'Test User',
            'line1': '123 Test Street',
            'line2': 'Apt 4B',
            'city': 'Test City',
            'state': 'TS',
            'postal_code': '12345',
            'country': 'US',
            'phone': '+1234567890'
        },
        billing_address={
            'name': 'Test User',
            'line1': '123 Test Street',
            'line2': 'Apt 4B',
            'city': 'Test City',
            'state': 'TS',
            'postal_code': '12345',
            'country': 'US'
        },
        customer_notes='This is a test order for WhatsApp notifications',
        status='pending',
        payment_status='pending'
    )

    # Create order item
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        product_sku=product.sku,
        quantity=1,
        unit_price=product.current_price,
        total_price=product.current_price
    )

    return order


def create_test_payment(order):
    """Create a test payment for the order."""

    payment = Payment.objects.create(
        order=order,
        user=order.user,
        amount=order.total_amount,
        currency='USD',
        payment_method='stripe',
        status='succeeded',
        stripe_payment_intent_id='pi_test_123456789',
        stripe_charge_id='ch_test_123456789'
    )

    return payment


def test_whatsapp_configuration():
    """Test WhatsApp configuration."""
    print("🔧 Testing WhatsApp Configuration...")

    # Check if Twilio is configured
    if not whatsapp_service.enabled:
        print("❌ WhatsApp notifications are disabled!")
        print("   Please configure the following environment variables:")
        print("   - TWILIO_ACCOUNT_SID")
        print("   - TWILIO_AUTH_TOKEN")
        print("   - TWILIO_WHATSAPP_FROM")
        print("   - STORE_OWNER_WHATSAPP")
        return False

    print("✅ WhatsApp service is enabled")
    print(f"   From number: {whatsapp_service.from_number}")
    print(f"   To number: {whatsapp_service.store_owner_number}")
    return True


def test_order_notification():
    """Test order notification."""
    print("\n📦 Testing Order Notification...")

    try:
        # Create test order
        order = create_test_order()
        print(f"✅ Created test order: {order.order_number}")

        # Send order notification
        success = whatsapp_service.send_order_notification(order)

        if success:
            print("✅ Order notification sent successfully!")
            print(f"   Order #: {order.order_number}")
            print(
                f"   Customer: {order.user.get_full_name() or order.user.email}")
            print(f"   Total: ${order.total_amount}")
        else:
            print("❌ Failed to send order notification")

        return order

    except Exception as e:
        print(f"❌ Error testing order notification: {str(e)}")
        return None


def test_payment_confirmation(order):
    """Test payment confirmation notification."""
    print("\n💳 Testing Payment Confirmation...")

    try:
        # Create test payment
        payment = create_test_payment(order)
        print(f"✅ Created test payment: ${payment.amount}")

        # Send payment confirmation
        success = whatsapp_service.send_payment_confirmation(order, payment)

        if success:
            print("✅ Payment confirmation sent successfully!")
            print(f"   Payment ID: {payment.id}")
            print(f"   Amount: ${payment.amount}")
            print(f"   Method: {payment.get_payment_method_display()}")
        else:
            print("❌ Failed to send payment confirmation")

        return payment

    except Exception as e:
        print(f"❌ Error testing payment confirmation: {str(e)}")
        return None


def test_payment_processor():
    """Test payment processor integration."""
    print("\n⚙️ Testing Payment Processor...")

    try:
        # Create test order
        order = create_test_order()
        payment = create_test_payment(order)

        # Test payment processing
        success = payment_processor.process_successful_payment(order, payment)

        if success:
            print("✅ Payment processor test successful!")
            print(f"   Order status: {order.status}")
            print(f"   Payment status: {order.payment_status}")
        else:
            print("❌ Payment processor test failed")

    except Exception as e:
        print(f"❌ Error testing payment processor: {str(e)}")


def main():
    """Main test function."""
    print("🧪 WhatsApp Notification System Test")
    print("=" * 50)

    # Test configuration
    if not test_whatsapp_configuration():
        print("\n❌ Cannot proceed with tests - WhatsApp not configured")
        return

    # Test order notification
    order = test_order_notification()

    if order:
        # Test payment confirmation
        payment = test_payment_confirmation(order)

        if payment:
            # Test payment processor
            test_payment_processor()

    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\n📱 Check your WhatsApp for notifications:")
    print(f"   Number: {whatsapp_service.store_owner_number}")


if __name__ == "__main__":
    main()
