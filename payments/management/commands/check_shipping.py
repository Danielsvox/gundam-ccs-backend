from django.core.management.base import BaseCommand
from orders.models import ShippingMethod


class Command(BaseCommand):
    help = 'Check and create default shipping methods'

    def handle(self, *args, **options):
        self.stdout.write("Available shipping methods:")
        self.stdout.write("=" * 50)

        methods = ShippingMethod.objects.filter(is_active=True)
        if methods.exists():
            for method in methods:
                self.stdout.write(f"ID: {method.id}")
                self.stdout.write(f"Name: {method.name}")
                self.stdout.write(f"Price: ${method.price}")
                self.stdout.write(f"Estimated Days: {method.estimated_days}")
                self.stdout.write(f"Description: {method.description}")
                self.stdout.write("-" * 30)
        else:
            self.stdout.write(
                "No shipping methods found. Creating default ones...")

            # Create default shipping methods
            ShippingMethod.objects.create(
                name="Standard Shipping",
                description="Standard ground shipping",
                price=5.99,
                estimated_days="3-5 business days",
                is_active=True
            )

            ShippingMethod.objects.create(
                name="Express Shipping",
                description="Fast express shipping",
                price=12.99,
                estimated_days="1-2 business days",
                is_active=True
            )

            ShippingMethod.objects.create(
                name="Free Shipping",
                description="Free shipping on orders over $50",
                price=0.00,
                estimated_days="5-7 business days",
                is_active=True
            )

            self.stdout.write(
                self.style.SUCCESS("Default shipping methods created!")
            )
            self.stdout.write("\nAvailable shipping methods:")
            self.stdout.write("=" * 50)

            for method in ShippingMethod.objects.filter(is_active=True):
                self.stdout.write(f"ID: {method.id}")
                self.stdout.write(f"Name: {method.name}")
                self.stdout.write(f"Price: ${method.price}")
                self.stdout.write(f"Estimated Days: {method.estimated_days}")
                self.stdout.write(f"Description: {method.description}")
                self.stdout.write("-" * 30)
