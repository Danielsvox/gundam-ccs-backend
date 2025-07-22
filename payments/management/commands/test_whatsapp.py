from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from orders.models import Order, OrderItem
from products.models import Product, Category
from payments.models import Payment
from payments.services import whatsapp_service, payment_processor

User = get_user_model()


class Command(BaseCommand):
    help = 'Test WhatsApp notification system with complete order flow'

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Complete WhatsApp Notification System")
        self.stdout.write("=" * 60)

        # Test 1: Configuration
        if not self.test_configuration():
            return

        # Test 2: Order Notification
        order = self.test_order_notification()
        if not order:
            return

        # Test 3: Payment Confirmation
        payment = self.test_payment_confirmation(order)
        if not payment:
            return

        # Test 4: Payment Processor
        self.test_payment_processor()

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(
            "✅ All tests completed successfully!"))
        self.stdout.write(
            f"📱 Check your WhatsApp ({whatsapp_service.store_owner_number}) for notifications")

    def test_configuration(self):
        """Test WhatsApp configuration."""
        self.stdout.write("🔧 Testing WhatsApp Configuration...")

        if not whatsapp_service.enabled:
            self.stdout.write(
                self.style.ERROR("❌ WhatsApp notifications are disabled!")
            )
            self.stdout.write(
                "   Please configure the following environment variables:")
            self.stdout.write("   - TWILIO_ACCOUNT_SID")
            self.stdout.write("   - TWILIO_AUTH_TOKEN")
            self.stdout.write("   - TWILIO_WHATSAPP_FROM")
            self.stdout.write("   - STORE_OWNER_WHATSAPP")
            return False

        self.stdout.write(
            self.style.SUCCESS("✅ WhatsApp service is enabled")
        )
        self.stdout.write(f"   From number: {whatsapp_service.from_number}")
        self.stdout.write(
            f"   To number: {whatsapp_service.store_owner_number}")
        return True

    def test_order_notification(self):
        """Test order notification."""
        self.stdout.write("\n📦 Testing Order Notification...")

        try:
            # Create test order
            order = self.create_test_order()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Created test order: {order.order_number}")
            )

            # Send order notification
            success = whatsapp_service.send_order_notification(order)

            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✅ Order notification sent successfully!")
                )
                self.stdout.write(f"   Order #: {order.order_number}")
                self.stdout.write(
                    f"   Customer: {order.user.get_full_name() or order.user.email}")
                self.stdout.write(f"   Total: ${order.total_amount}")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Failed to send order notification")
                )

            return order

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Error testing order notification: {str(e)}")
            )
            return None

    def test_payment_confirmation(self, order):
        """Test payment confirmation notification."""
        self.stdout.write("\n💳 Testing Payment Confirmation...")

        try:
            # Create test payment
            payment = self.create_test_payment(order)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Created test payment: ${payment.amount}")
            )

            # Send payment confirmation
            success = whatsapp_service.send_payment_confirmation(
                order, payment)

            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✅ Payment confirmation sent successfully!")
                )
                self.stdout.write(f"   Payment ID: {payment.id}")
                self.stdout.write(f"   Amount: ${payment.amount}")
                self.stdout.write(
                    f"   Method: {payment.get_payment_method_display()}")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Failed to send payment confirmation")
                )

            return payment

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Error testing payment confirmation: {str(e)}")
            )
            return None

    def test_payment_processor(self):
        """Test payment processor integration."""
        self.stdout.write("\n⚙️ Testing Payment Processor...")

        try:
            # Create test order
            order = self.create_test_order()
            payment = self.create_test_payment(order)

            # Test payment processing
            success = payment_processor.process_successful_payment(
                order, payment)

            if success:
                self.stdout.write(
                    self.style.SUCCESS("✅ Payment processor test successful!")
                )
                self.stdout.write(f"   Order status: {order.status}")
                self.stdout.write(f"   Payment status: {order.payment_status}")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Payment processor test failed")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Error testing payment processor: {str(e)}")
            )

    def create_test_order(self):
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
        import uuid
        unique_slug = f'test-category-{uuid.uuid4().hex[:8]}'
        category, created = Category.objects.get_or_create(
            name='Test Category',
            defaults={
                'slug': unique_slug,
                'description': 'Test category for notifications'
            }
        )

        # Get or create test product
        unique_product_slug = f'test-gundam-model-{uuid.uuid4().hex[:8]}'
        unique_sku = f'TEST-{uuid.uuid4().hex[:6]}'
        product, created = Product.objects.get_or_create(
            name='Test Gundam Model',
            defaults={
                'slug': unique_product_slug,
                'description': 'A test Gundam model for notification testing',
                'short_description': 'Test model',
                'price': Decimal('150.00'),
                'category': category,
                'grade': 'MG',
                'manufacturer': 'Bandai',
                'stock_quantity': 10,
                'sku': unique_sku
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

    def create_test_payment(self, order):
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
