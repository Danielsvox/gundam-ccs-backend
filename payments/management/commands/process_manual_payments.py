from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.models import Payment
from orders.models import OrderStatusHistory
from payments.services import payment_processor


class Command(BaseCommand):
    help = 'Process manual payments and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm-all',
            action='store_true',
            help='Confirm all pending manual payments',
        )
        parser.add_argument(
            '--order-id',
            type=int,
            help='Confirm payment for specific order ID',
        )
        parser.add_argument(
            '--list-pending',
            action='store_true',
            help='List all pending manual payments',
        )

    def handle(self, *args, **options):
        if options['list_pending']:
            self.list_pending_payments()
        elif options['confirm_all']:
            self.confirm_all_payments()
        elif options['order_id']:
            self.confirm_specific_payment(options['order_id'])
        else:
            self.stdout.write(
                self.style.ERROR(
                    'Please specify an action: --list-pending, --confirm-all, or --order-id')
            )

    def list_pending_payments(self):
        """List all pending manual payments."""
        pending_payments = Payment.objects.filter(
            payment_method='manual', status='pending'
        ).select_related('order', 'user')

        if not pending_payments:
            self.stdout.write(
                self.style.SUCCESS('No pending manual payments found.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Found {pending_payments.count()} pending manual payments:')
        )

        for payment in pending_payments:
            self.stdout.write(
                f'Order #{payment.order.order_number} - '
                f'Customer: {payment.user.email} - '
                f'Amount: ${payment.amount} - '
                f'Created: {payment.created_at.strftime("%Y-%m-%d %H:%M")}'
            )

    def confirm_all_payments(self):
        """Confirm all pending manual payments."""
        pending_payments = Payment.objects.filter(
            payment_method='manual', status='pending'
        )

        if not pending_payments:
            self.stdout.write(
                self.style.SUCCESS('No pending manual payments to confirm.')
            )
            return

        confirmed_count = 0
        for payment in pending_payments:
            try:
                # Update payment status
                payment.status = 'succeeded'
                payment.save()

                # Update order status
                order = payment.order
                order.payment_status = 'paid'
                order.status = 'confirmed'
                order.save()

                # Create status history entry
                OrderStatusHistory.objects.create(
                    order=order,
                    status='confirmed',
                    notes='Manual payment confirmed via management command'
                )

                # Send WhatsApp notification
                payment_processor.process_successful_payment(order, payment)

                confirmed_count += 1
                self.stdout.write(
                    f'Confirmed payment for order #{order.order_number}'
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error confirming payment {payment.id}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully confirmed {confirmed_count} manual payments.')
        )

    def confirm_specific_payment(self, order_id):
        """Confirm payment for a specific order."""
        try:
            payment = Payment.objects.get(
                order_id=order_id, payment_method='manual', status='pending'
            )
        except Payment.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'No pending manual payment found for order {order_id}')
            )
            return

        try:
            # Update payment status
            payment.status = 'succeeded'
            payment.save()

            # Update order status
            order = payment.order
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save()

            # Create status history entry
            OrderStatusHistory.objects.create(
                order=order,
                status='confirmed',
                notes='Manual payment confirmed via management command'
            )

            # Send WhatsApp notification
            payment_processor.process_successful_payment(order, payment)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully confirmed payment for order #{order.order_number}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error confirming payment: {str(e)}')
            )
