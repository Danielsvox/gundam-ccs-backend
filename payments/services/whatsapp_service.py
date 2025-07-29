import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service to handle WhatsApp notifications."""
    
    def __init__(self):
        self.client = None
        self.from_number = None
        
        # Initialize Twilio client if credentials are available
        if hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
            try:
                self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                self.from_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)
                logger.info("WhatsApp service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize WhatsApp service: {str(e)}")
        else:
            logger.warning("Twilio credentials not configured - WhatsApp notifications disabled")
    
    def send_order_notification(self, order, phone_number=None):
        """Send WhatsApp notification for new order."""
        try:
            if not self.client or not self.from_number:
                logger.warning("WhatsApp service not configured - skipping notification")
                return False
            
            # Get customer phone number
            if not phone_number:
                phone_number = order.shipping_address.get('phone') if order.shipping_address else None
            
            if not phone_number:
                logger.warning(f"No phone number available for order {order.order_number}")
                return False
            
            # Format phone number for WhatsApp
            formatted_phone = self._format_phone_number(phone_number)
            
            # Create message
            message = self._create_order_message(order)
            
            # Send message
            message_sid = self.client.messages.create(
                from_=f"whatsapp:{self.from_number}",
                body=message,
                to=f"whatsapp:{formatted_phone}"
            )
            
            logger.info(f"Sent WhatsApp notification for order {order.order_number}: {message_sid.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending WhatsApp notification: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp notification: {str(e)}")
            return False
    
    def send_payment_confirmation(self, order, payment, phone_number=None):
        """Send WhatsApp notification for payment confirmation."""
        try:
            if not self.client or not self.from_number:
                logger.warning("WhatsApp service not configured - skipping notification")
                return False
            
            # Get customer phone number
            if not phone_number:
                phone_number = order.shipping_address.get('phone') if order.shipping_address else None
            
            if not phone_number:
                logger.warning(f"No phone number available for order {order.order_number}")
                return False
            
            # Format phone number for WhatsApp
            formatted_phone = self._format_phone_number(phone_number)
            
            # Create message
            message = self._create_payment_confirmation_message(order, payment)
            
            # Send message
            message_sid = self.client.messages.create(
                from_=f"whatsapp:{self.from_number}",
                body=message,
                to=f"whatsapp:{formatted_phone}"
            )
            
            logger.info(f"Sent payment confirmation for order {order.order_number}: {message_sid.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending payment confirmation: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {str(e)}")
            return False
    
    def _format_phone_number(self, phone_number):
        """Format phone number for WhatsApp."""
        # Remove any non-digit characters
        cleaned = ''.join(filter(str.isdigit, str(phone_number)))
        
        # Add country code if not present (assuming Venezuela +58)
        if not cleaned.startswith('58'):
            cleaned = '58' + cleaned
        
        return cleaned
    
    def _create_order_message(self, order):
        """Create WhatsApp message for new order."""
        items_text = "\n".join([
            f"• {item.product.name} x{item.quantity} - ${item.total_price}"
            for item in order.items.all()
        ])
        
        message = f"""🎉 ¡Nuevo pedido recibido!

📦 Pedido #{order.order_number}
💰 Total: ${order.total_amount}
📅 Fecha: {order.created_at.strftime('%d/%m/%Y %H:%M')}

🛍️ Productos:
{items_text}

📍 Dirección de envío:
{order.shipping_address.get('address_line_1', '')}
{order.shipping_address.get('city', '')}, {order.shipping_address.get('state', '')}

📞 Contacto: {order.shipping_address.get('phone', 'N/A')}

¡Gracias por tu compra! 🚀"""
        
        return message
    
    def _create_payment_confirmation_message(self, order, payment):
        """Create WhatsApp message for payment confirmation."""
        message = f"""✅ ¡Pago confirmado!

📦 Pedido #{order.order_number}
💰 Monto: ${payment.amount}
💳 Método: {payment.get_payment_method_display()}
📅 Confirmado: {payment.updated_at.strftime('%d/%m/%Y %H:%M')}

Tu pedido está siendo procesado y será enviado pronto.

¡Gracias por tu compra! 🚀"""
        
        return message


# Singleton instance
whatsapp_service = WhatsAppService() 