from django.core.management.base import BaseCommand
from payments.models import PagoMovilBankCode, PagoMovilRecipient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Set up production Pago Móvil data with specific recipient details'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing recipients before creating new ones',
        )

    def handle(self, *args, **options):
        """Set up production Pago Móvil data."""
        
        if options['clear']:
            self.stdout.write("Clearing existing recipients...")
            PagoMovilRecipient.objects.all().delete()

        self.stdout.write("Setting up production Pago Móvil recipient...")
        
        # Find or create Banesco bank
        banesco_bank, created = PagoMovilBankCode.objects.get_or_create(
            bank_code='0134',
            defaults={'bank_name': 'Banesco', 'is_active': True}
        )
        
        if created:
            self.stdout.write(f"Created bank: {banesco_bank.bank_code} - {banesco_bank.bank_name}")
        else:
            self.stdout.write(f"Using existing bank: {banesco_bank.bank_code} - {banesco_bank.bank_name}")

        # Create production recipient
        recipient, created = PagoMovilRecipient.objects.get_or_create(
            bank_code=banesco_bank,
            recipient_id='V-24760431',
            recipient_phone='+584242263633',
            defaults={
                'recipient_name': 'Carlos Daniel',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                f"✅ Created production recipient: {recipient.recipient_name} "
                f"({recipient.recipient_id}) - {recipient.bank_code.bank_name}"
            )
        else:
            self.stdout.write(
                f"✅ Production recipient already exists: {recipient.recipient_name} "
                f"({recipient.recipient_id}) - {recipient.bank_code.bank_name}"
            )

        # Deactivate all other recipients
        other_recipients = PagoMovilRecipient.objects.exclude(id=recipient.id)
        deactivated_count = other_recipients.update(is_active=False)
        
        if deactivated_count > 0:
            self.stdout.write(f"Deactivated {deactivated_count} other recipients")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎯 Production setup complete!\n"
                f"Active recipient: {recipient.recipient_name}\n"
                f"ID: {recipient.recipient_id}\n"
                f"Phone: {recipient.recipient_phone}\n"
                f"Bank: {recipient.bank_code.bank_name} ({recipient.bank_code.bank_code})\n"
                f"\nTotal active recipients: {PagoMovilRecipient.objects.filter(is_active=True).count()}"
            )
        ) 