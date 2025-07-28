# Manual Payment Workflow

This document explains how the manual payment system works after disabling Stripe integration.

## Overview

The system now supports only manual payments where:
1. Orders are created with payment status "pending"
2. WhatsApp notifications are sent to the business owner
3. No payment intent is generated
4. Business owner manually confirms payments when received

## Workflow

### 1. Customer Checkout Process

When a customer completes checkout:

1. **Order Creation**: Order is created with:
   - `payment_status = 'pending'`
   - `status = 'pending'`
   - Payment record with `payment_method = 'manual'` and `status = 'pending'`

2. **Cart Clearing**: Customer's cart is cleared

3. **WhatsApp Notification**: Business owner receives a WhatsApp message with:
   - Order details (items, totals, shipping address)
   - Customer contact information
   - Payment method: "Manual Payment"
   - Warning: "⚠️ MANUAL PAYMENT REQUIRED"

4. **Response**: Frontend receives confirmation with:
   ```json
   {
     "order_id": 123,
     "order_number": "ORD-2024-001",
     "amount": 150.00,
     "payment_status": "pending",
     "payment_method": "manual",
     "message": "Order created successfully! Payment will be processed manually.",
     "success": true
   }
   ```

### 2. Business Owner Payment Processing

The business owner can confirm payments through multiple methods:

#### A. Django Admin Interface
1. Go to `/admin/payments/payment/`
2. Filter by `payment_method = 'manual'` and `status = 'pending'`
3. Select payments and use "Confirm selected manual payments" action
4. Or click "Confirm Payment" button for individual payments

#### B. API Endpoint
```bash
POST /payments/confirm-manual-payment/
{
  "order_id": 123
}
```

#### C. Management Command
```bash
# List pending payments
python manage.py process_manual_payments --list-pending

# Confirm all pending payments
python manage.py process_manual_payments --confirm-all

# Confirm specific order
python manage.py process_manual_payments --order-id 123
```

### 3. Payment Confirmation Process

When a payment is confirmed:

1. **Payment Status Update**: Payment status changes to `'succeeded'`
2. **Order Status Update**: Order status changes to `'confirmed'` and payment status to `'paid'`
3. **Status History**: Order status history entry is created
4. **WhatsApp Notification**: Business owner receives payment confirmation message
5. **Order Processing**: Order is ready for fulfillment

## API Endpoints

### Checkout
- **URL**: `POST /payments/checkout/`
- **Purpose**: Create order for manual payment
- **Response**: Order confirmation with manual payment details

### Confirm Manual Payment
- **URL**: `POST /payments/confirm-manual-payment/`
- **Purpose**: Confirm manual payment received
- **Request**: `{"order_id": 123}`
- **Response**: Payment confirmation status

## WhatsApp Notifications

### New Order Notification
- Sent immediately when order is created
- Includes order details, customer info, and payment method
- Highlights that manual payment is required

### Payment Confirmation Notification
- Sent when payment is confirmed
- Includes payment details and order status
- Confirms order is ready for processing

## Admin Features

### Payment Admin Actions
- **Confirm Manual Payments**: Bulk confirm multiple payments
- **Mark Payments Failed**: Mark payments as failed
- **Payment Actions**: Individual payment confirmation buttons

### Filtering and Search
- Filter by payment method, status, currency
- Search by order number, user email
- Sort by creation date

## Re-enabling Stripe Integration

To re-enable Stripe integration in the future:

1. **Restore Stripe Logic**: Uncomment Stripe payment intent creation in `CheckoutView`
2. **Update Payment Method**: Change default from `'manual'` to `'stripe'`
3. **Restore Webhooks**: Re-enable Stripe webhook processing
4. **Update Frontend**: Modify frontend to handle Stripe payment flow

The architecture is designed to make this transition smooth with minimal code changes.

## Configuration

### Required Settings
```python
# WhatsApp/Twilio Configuration
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_WHATSAPP_FROM = 'your_whatsapp_number'
STORE_OWNER_WHATSAPP = 'store_owner_whatsapp_number'

# Stripe Configuration (optional, for future use)
STRIPE_SECRET_KEY = 'your_stripe_secret_key'
STRIPE_WEBHOOK_SECRET = 'your_webhook_secret'
```

### Optional Settings
```python
# Disable Stripe completely
STRIPE_ENABLED = False
```

## Troubleshooting

### Common Issues

1. **WhatsApp Notifications Not Sending**
   - Check Twilio configuration
   - Verify WhatsApp numbers are in correct format
   - Check Twilio account balance

2. **Payment Confirmation Fails**
   - Verify order exists
   - Check payment method is 'manual'
   - Ensure payment status is 'pending'

3. **Admin Actions Not Working**
   - Check user permissions
   - Verify payment records exist
   - Check for database constraints

### Logs
- Check Django logs for payment processing errors
- Monitor Twilio logs for WhatsApp delivery issues
- Review order status history for tracking

## Security Considerations

1. **Payment Confirmation**: Only authenticated users can confirm payments
2. **Order Access**: Users can only access their own orders
3. **Admin Access**: Payment confirmation requires admin privileges
4. **Audit Trail**: All payment status changes are logged in order history 