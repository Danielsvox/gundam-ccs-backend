from django.core.management.base import BaseCommand
from payments.models import PagoMovilBankCode, PagoMovilRecipient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate Pago Móvil bank codes and sample recipients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        """Populate Pago Móvil data."""
        if options['clear']:
            self.stdout.write("Clearing existing Pago Móvil data...")
            PagoMovilRecipient.objects.all().delete()
            PagoMovilBankCode.objects.all().delete()

        self.stdout.write("Populating Pago Móvil bank codes...")
        
        # Venezuelan bank codes (major banks)
        bank_data = [
            ('0102', 'Banco de Venezuela'),
            ('0104', 'Venezolano de Crédito'),
            ('0105', 'Mercantil'),
            ('0108', 'Provincial'),
            ('0114', 'Bancaribe'),
            ('0115', 'Exterior'),
            ('0128', 'Banco del Tesoro'),
            ('0134', 'Banesco'),
            ('0137', 'Sofitasa'),
            ('0138', 'Banco Plaza'),
            ('0146', 'Banco de la Gente Emprendedora'),
            ('0151', 'BFC Banco Fondo Común'),
            ('0156', '100% Banco'),
            ('0157', 'DelSur'),
            ('0163', 'Banco del Tesoro'),
            ('0166', 'Banco Bicentenario'),
            ('0168', 'Bancrecer'),
            ('0169', 'Mi Banco'),
            ('0171', 'Banco Activo'),
            ('0172', 'Bancamiga'),
            ('0173', 'Banco Internacional de Desarrollo'),
            ('0174', 'Banplus'),
            ('0175', 'Bicentenario Banco Universal'),
            ('0176', 'Banco Exterior'),
            ('0177', 'Banco de Venezuela'),
            ('0190', 'Citibank'),
            ('0191', 'Banco Mercantil'),
        ]

        created_banks = []
        for bank_code, bank_name in bank_data:
            bank, created = PagoMovilBankCode.objects.get_or_create(
                bank_code=bank_code,
                defaults={'bank_name': bank_name, 'is_active': True}
            )
            if created:
                created_banks.append(bank)
                self.stdout.write(f"  Created: {bank_code} - {bank_name}")
            else:
                self.stdout.write(f"  Exists: {bank_code} - {bank_name}")

        self.stdout.write(f"Created {len(created_banks)} new bank codes")

        # Create sample recipients
        self.stdout.write("Creating sample recipients...")
        
        # Get some active banks for recipients
        active_banks = PagoMovilBankCode.objects.filter(is_active=True)[:5]
        
        if active_banks:
            sample_recipients = [
                {
                    'bank_code': active_banks[0],
                    'recipient_id': 'V-12345678',
                    'recipient_phone': '04121234567',
                    'recipient_name': 'Gundam CCS Store'
                },
                {
                    'bank_code': active_banks[1] if len(active_banks) > 1 else active_banks[0],
                    'recipient_id': 'J-87654321-0',
                    'recipient_phone': '04241234567',
                    'recipient_name': 'Gundam CCS Business'
                },
                {
                    'bank_code': active_banks[2] if len(active_banks) > 2 else active_banks[0],
                    'recipient_id': 'V-11223344',
                    'recipient_phone': '04161234567',
                    'recipient_name': 'Gundam CCS Online'
                }
            ]

            created_recipients = []
            for recipient_data in sample_recipients:
                recipient, created = PagoMovilRecipient.objects.get_or_create(
                    bank_code=recipient_data['bank_code'],
                    recipient_id=recipient_data['recipient_id'],
                    recipient_phone=recipient_data['recipient_phone'],
                    defaults={
                        'recipient_name': recipient_data['recipient_name'],
                        'is_active': True
                    }
                )
                if created:
                    created_recipients.append(recipient)
                    self.stdout.write(
                        f"  Created: {recipient.recipient_name} ({recipient.recipient_id}) - {recipient.bank_code.bank_name}"
                    )
                else:
                    self.stdout.write(
                        f"  Exists: {recipient.recipient_name} ({recipient.recipient_id}) - {recipient.bank_code.bank_name}"
                    )

            self.stdout.write(f"Created {len(created_recipients)} new recipients")
        else:
            self.stdout.write(self.style.WARNING("No active banks found for creating recipients"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully populated Pago Móvil data!\n"
                f"Total banks: {PagoMovilBankCode.objects.filter(is_active=True).count()}\n"
                f"Total recipients: {PagoMovilRecipient.objects.filter(is_active=True).count()}"
            )
        ) 