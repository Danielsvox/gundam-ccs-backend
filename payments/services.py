import os
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)


class WhatsAppNotificationService:
    """Service for sending WhatsApp notifications via Twilio."""

    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_WHATSAPP_FROM', None)
        self.store_owner_number = getattr(
            settings, 'STORE_OWNER_WHATSAPP', None)

        if all([self.account_sid, self.auth_token, self.from_number, self.store_owner_number]):
            self.client = Client(self.account_sid, self.auth_token)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
            logger.warning(
                "WhatsApp notifications disabled - missing Twilio configuration")

    def send_order_notification(self, order):
        """Send order notification to store owner."""
        if not self.enabled:
            logger.info(
                "WhatsApp notifications disabled, skipping order notification")
            return False

        try:
            message = self._format_order_message(order)

            # Send WhatsApp message
            message_obj = self.client.messages.create(
                from_=f"whatsapp:{self.from_number}",
                body=message,
                to=f"whatsapp:{self.store_owner_number}"
            )

            logger.info(
                f"WhatsApp notification sent for order {order.order_number}: {message_obj.sid}")
            return True

        except TwilioException as e:
            logger.error(
                f"Failed to send WhatsApp notification for order {order.order_number}: {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending WhatsApp notification: {str(e)}")
            return False

    def send_payment_confirmation(self, order, payment):
        """Send payment confirmation notification."""
        if not self.enabled:
            logger.info(
                "WhatsApp notifications disabled, skipping payment confirmation")
            return False

        try:
            message = self._format_payment_message(order, payment)

            # Send WhatsApp message
            message_obj = self.client.messages.create(
                from_=f"whatsapp:{self.from_number}",
                body=message,
                to=f"whatsapp:{self.store_owner_number}"
            )

            logger.info(
                f"Payment confirmation sent for order {order.order_number}: {message_obj.sid}")
            return True

        except TwilioException as e:
            logger.error(
                f"Failed to send payment confirmation for order {order.order_number}: {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending payment confirmation: {str(e)}")
            return False

    def _format_order_message(self, order):
        """Format order notification message."""
        items_text = "\n".join([
            f"• {item.quantity}x {item.product_name} - ${item.total_price}"
            for item in order.items.all()
        ])

        # Check if this is a manual payment order
        payment_method = "Manual Payment" if order.payments.filter(
            payment_method='manual').exists() else "Online Payment"
        payment_status_note = "⚠️ MANUAL PAYMENT REQUIRED" if payment_method == "Manual Payment" else ""

        message = f"""🛒 *NEW ORDER RECEIVED*

📋 *Order Details:*
Order #: {order.order_number}
Customer: {order.user.get_full_name() or order.user.email}
Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}

📦 *Items:*
{items_text}

💰 *Pricing:*
Subtotal: ${order.subtotal}
Tax: ${order.tax_amount}
Shipping: ${order.shipping_amount}
Discount: ${order.discount_amount}
*Total: ${order.total_amount}*

💳 *Payment Method:* {payment_method}
{payment_status_note}

📍 *Shipping Address:*
{self._format_address(order.shipping_address)}

📞 *Customer Contact:*
Email: {order.user.email}
Phone: {order.shipping_address.get('phone', 'Not provided')}

Status: {order.status.title()}
Payment Status: {order.payment_status.title()}

Please process this order as soon as possible! 🚀"""

        return message

    def _format_payment_message(self, order, payment):
        """Format payment confirmation message."""
        if payment.payment_method == 'manual':
            message = f"""💳 *MANUAL PAYMENT RECEIVED*

📋 *Order Details:*
Order #: {order.order_number}
Customer: {order.user.get_full_name() or order.user.email}

💰 *Payment Information:*
Amount: ${payment.amount}
Method: Manual Payment
Status: {payment.get_status_display()}

✅ *Order Status:*
Order Status: {order.status.title()}
Payment Status: {order.payment_status.title()}

The customer has provided manual payment for their order. You can now proceed with processing and shipping! 📦"""
        else:
            message = f"""💳 *PAYMENT CONFIRMED*

📋 *Order Details:*
Order #: {order.order_number}
Customer: {order.user.get_full_name() or order.user.email}

💰 *Payment Information:*
Amount: ${payment.amount}
Method: {payment.get_payment_method_display()}
Status: {payment.get_status_display()}
Transaction ID: {payment.stripe_payment_intent_id or 'N/A'}

✅ *Order Status:*
Order Status: {order.status.title()}
Payment Status: {order.payment_status.title()}

The customer has successfully paid for their order. You can now proceed with processing and shipping! 📦"""

        return message

    def _format_address(self, address_data):
        """Format shipping address for display."""
        if not address_data:
            return "Address not provided"

        address_parts = []

        if address_data.get('name'):
            address_parts.append(address_data['name'])

        if address_data.get('line1'):
            address_parts.append(address_data['line1'])

        if address_data.get('line2'):
            address_parts.append(address_data['line2'])

        city_state = []
        if address_data.get('city'):
            city_state.append(address_data['city'])
        if address_data.get('state'):
            city_state.append(address_data['state'])
        if city_state:
            address_parts.append(", ".join(city_state))

        if address_data.get('postal_code'):
            address_parts.append(address_data['postal_code'])

        if address_data.get('country'):
            address_parts.append(address_data['country'])

        return "\n".join(address_parts)


class PaymentProcessingService:
    """Service for processing payments and managing order flow."""

    def __init__(self):
        self.whatsapp_service = WhatsAppNotificationService()

    def process_successful_payment(self, order, payment):
        """Process a successful payment and send notifications."""
        try:
            # Update order status
            order.payment_status = 'paid'
            order.status = 'confirmed'
            order.save()

            # Create status history entry
            from orders.models import OrderStatusHistory
            OrderStatusHistory.objects.create(
                order=order,
                status='confirmed',
                notes=f'Payment confirmed via {payment.get_payment_method_display()}'
            )

            # Send WhatsApp notification
            self.whatsapp_service.send_payment_confirmation(order, payment)

            logger.info(
                f"Payment processed successfully for order {order.order_number}")
            return True

        except Exception as e:
            logger.error(
                f"Error processing payment for order {order.order_number}: {str(e)}")
            return False

    def process_new_order(self, order):
        """Process a new order and send initial notification."""
        try:
            # Send initial order notification
            self.whatsapp_service.send_order_notification(order)

            logger.info(
                f"New order notification sent for order {order.order_number}")
            return True

        except Exception as e:
            logger.error(
                f"Error processing new order {order.order_number}: {str(e)}")
            return False


# Global instances
whatsapp_service = WhatsAppNotificationService()
payment_processor = PaymentProcessingService()
