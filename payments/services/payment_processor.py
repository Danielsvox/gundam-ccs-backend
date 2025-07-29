import logging
from django.conf import settings
from django.utils import timezone
from orders.models import Order, OrderStatusHistory
from .exchange_rate_service import exchange_rate_service
from payments.models import ExchangeRateSnapshot

logger = logging.getLogger(__name__)


class PaymentProcessor:
    """Service to handle payment processing logic."""
    
    def process_new_order(self, order):
        """Process a new order and send notifications."""
        try:
            logger.info(f"Processing new order: {order.order_number}")
            
            # Create exchange rate snapshot for the order
            self._create_exchange_rate_snapshot(order)
            
            # Send WhatsApp notification
            self._send_order_notification(order)
            
            logger.info(f"Successfully processed order: {order.order_number}")
            
        except Exception as e:
            logger.error(f"Error processing order {order.order_number}: {str(e)}")
            raise
    
    def process_successful_payment(self, order, payment):
        """Process a successful payment."""
        try:
            logger.info(f"Processing successful payment for order: {order.order_number}")
            
            # Update order status
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                status='confirmed',
                notes='Payment confirmed successfully'
            )
            
            # Send confirmation notification
            self._send_payment_confirmation(order, payment)
            
            logger.info(f"Successfully processed payment for order: {order.order_number}")
            
        except Exception as e:
            logger.error(f"Error processing payment for order {order.order_number}: {str(e)}")
            raise
    
    def _create_exchange_rate_snapshot(self, order):
        """Create exchange rate snapshot for the order."""
        try:
            # Get current exchange rate
            rate_data = exchange_rate_service.get_current_rate()
            if rate_data:
                usd_to_ves = rate_data['usd_to_ves']
                amount_ves = order.total_amount * usd_to_ves
                
                # Create snapshot
                ExchangeRateSnapshot.objects.create(
                    order=order,
                    usd_to_ves=usd_to_ves,
                    amount_usd=order.total_amount,
                    amount_ves=amount_ves
                )
                
                logger.info(f"Created exchange rate snapshot for order {order.order_number}")
            else:
                logger.warning(f"Could not create exchange rate snapshot for order {order.order_number}")
                
        except Exception as e:
            logger.error(f"Error creating exchange rate snapshot: {str(e)}")
    
    def _send_order_notification(self, order):
        """Send WhatsApp notification for new order."""
        try:
            # This would integrate with your WhatsApp service
            # For now, just log the notification
            logger.info(f"Would send WhatsApp notification for order: {order.order_number}")
            
        except Exception as e:
            logger.error(f"Error sending order notification: {str(e)}")
    
    def _send_payment_confirmation(self, order, payment):
        """Send payment confirmation notification."""
        try:
            # This would integrate with your WhatsApp service
            # For now, just log the notification
            logger.info(f"Would send payment confirmation for order: {order.order_number}")
            
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {str(e)}")


# Singleton instance
payment_processor = PaymentProcessor() 