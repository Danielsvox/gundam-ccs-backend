import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp notifications via Twilio."""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_WHATSAPP_FROM', None)
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not configured")
    
    def send_order_notification(self, order, phone_number=None):
        """Send order notification via WhatsApp."""
        try:
            if not self.client:
                logger.warning("Twilio client not available")
                return False
            
            message = self._create_order_message(order)
            to_number = phone_number or order.user.phone_number
            
            if not to_number:
                logger.warning(f"No phone number available for user {order.user.email}")
                return False
            
            formatted_number = self._format_phone_number(to_number)
            
            # Send via Twilio WhatsApp
            message_obj = self.client.messages.create(
                from_=f'whatsapp:{self.from_number}',
                body=message,
                to=f'whatsapp:{formatted_number}'
            )
            
            logger.info(f"WhatsApp order notification sent: {message_obj.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending order notification: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending order notification: {str(e)}")
            return False
    
    def send_payment_confirmation(self, order, payment, phone_number=None):
        """Send payment confirmation via WhatsApp."""
        try:
            if not self.client:
                logger.warning("Twilio client not available")
                return False
            
            message = self._create_payment_confirmation_message(order, payment)
            to_number = phone_number or order.user.phone_number
            
            if not to_number:
                logger.warning(f"No phone number available for user {order.user.email}")
                return False
            
            formatted_number = self._format_phone_number(to_number)
            
            # Send via Twilio WhatsApp
            message_obj = self.client.messages.create(
                from_=f'whatsapp:{self.from_number}',
                body=message,
                to=f'whatsapp:{formatted_number}'
            )
            
            logger.info(f"WhatsApp payment confirmation sent: {message_obj.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending payment confirmation: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {str(e)}")
            return False
    
    def send_custom_message(self, phone_number, message):
        """Send a custom message via WhatsApp."""
        try:
            if not self.client:
                logger.warning("Twilio client not available")
                return False
            
            if not phone_number:
                logger.warning("No phone number provided")
                return False
            
            formatted_number = self._format_phone_number(phone_number)
            
            # Send via Twilio WhatsApp
            message_obj = self.client.messages.create(
                from_=f'whatsapp:{self.from_number}',
                body=message,
                to=f'whatsapp:{formatted_number}'
            )
            
            logger.info(f"WhatsApp custom message sent: {message_obj.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending custom message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending custom message: {str(e)}")
            return False
    
    def _format_phone_number(self, phone_number):
        """Format phone number for Twilio."""
        # Remove all non-digit characters
        import re
        digits_only = re.sub(r'\D', '', phone_number)
        
        # Add country code if not present (assume Venezuela +58)
        if not digits_only.startswith('58'):
            digits_only = '58' + digits_only
        
        # Add + prefix
        return '+' + digits_only
    
    def _create_order_message(self, order):
        """Create order notification message."""
        items_text = "\n".join([
            f"• {item.product.name} x{item.quantity} - ${item.total_price}"
            for item in order.items.all()
        ])
        
        message = f"""🛒 New Order Received!

Order #{order.id}
Customer: {order.user.email}
Total: ${order.total_amount}

Items:
{items_text}

Status: {order.status.title()}
Payment: {order.payment_status.title()}

Thank you for your order! 🚀"""
        
        return message
    
    def _create_payment_confirmation_message(self, order, payment):
        """Create payment confirmation message."""
        message = f"""💳 Payment Confirmed!

Order #{order.id}
Amount: ${payment.amount}
Method: {payment.payment_method.title()}
Status: {payment.status.title()}

Your order is being processed! 🚀"""
        
        return message


# Singleton instance
whatsapp_service = WhatsAppService() 