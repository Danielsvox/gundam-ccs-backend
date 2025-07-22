# 📱 WhatsApp Notification System Setup Guide

This guide will help you set up the WhatsApp notification system for your Gundam CCS store.

## 🚀 Quick Setup (For Testing)

### Step 1: Create Twilio Account
1. Go to [Twilio Console](https://console.twilio.com/)
2. Sign up for a free account
3. Verify your email and phone number

### Step 2: Get Your Credentials
1. In Twilio Console, go to **Dashboard**
2. Copy your **Account SID** and **Auth Token**
3. Go to **Messaging** → **Try it out** → **Send a WhatsApp message**
4. Note the sandbox number (usually +14155238886)

### Step 3: Join WhatsApp Sandbox
1. Open WhatsApp on your phone (+584242263633)
2. Send the provided code to the Twilio sandbox number
3. You'll receive a confirmation message

### Step 4: Configure Environment Variables
Create a `.env` file in your project root:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=AC_your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=+14155238886
STORE_OWNER_WHATSAPP=+584242263633
```

### Step 5: Test the System
Run the test script:

```bash
# Test basic configuration
python test_simple_whatsapp.py

# Test full system (requires Django)
python test_whatsapp.py
```

## 🔧 Production Setup

### Step 1: WhatsApp Business API
1. Apply for WhatsApp Business API through Twilio
2. Provide business documentation
3. Wait for approval (usually 1-2 weeks)

### Step 2: Business Verification
1. Verify your business phone number
2. Complete business profile
3. Set up message templates

### Step 3: Update Configuration
```bash
# Production Twilio Configuration
TWILIO_ACCOUNT_SID=AC_your_production_sid
TWILIO_AUTH_TOKEN=your_production_token
TWILIO_WHATSAPP_FROM=+1234567890  # Your verified business number
STORE_OWNER_WHATSAPP=+584242263633
```

## 📋 Message Templates

### Order Notification Template
```
🛒 NEW ORDER RECEIVED

📋 Order Details:
Order #: {order_number}
Customer: {customer_name}
Date: {order_date}

📦 Items:
{items_list}

💰 Pricing:
Subtotal: ${subtotal}
Tax: ${tax_amount}
Shipping: ${shipping_amount}
Total: ${total_amount}

📍 Shipping Address:
{shipping_address}

Please process this order as soon as possible! 🚀
```

### Payment Confirmation Template
```
💳 PAYMENT CONFIRMED

📋 Order Details:
Order #: {order_number}
Customer: {customer_name}

💰 Payment Information:
Amount: ${amount}
Method: {payment_method}
Status: {payment_status}

✅ Order Status:
Order Status: {order_status}
Payment Status: {payment_status}

The customer has successfully paid for their order. You can now proceed with processing and shipping! 📦
```

## 🧪 Testing

### Test 1: Basic Configuration
```bash
python test_simple_whatsapp.py
```

### Test 2: Full System Test
```bash
python test_whatsapp.py
```

### Test 3: API Integration Test
```bash
# Start Django server
python manage.py runserver

# Create test order via API
curl -X POST http://localhost:8000/api/v1/payments/checkout/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": {
      "name": "Test User",
      "line1": "123 Test St",
      "city": "Test City",
      "state": "TS",
      "postal_code": "12345",
      "country": "US",
      "phone": "+1234567890"
    }
  }'
```

## 🔍 Troubleshooting

### Issue: "Account SID Missing"
**Solution:** Set the `TWILIO_ACCOUNT_SID` environment variable

### Issue: "Auth Token Missing"
**Solution:** Set the `TWILIO_AUTH_TOKEN` environment variable

### Issue: "WhatsApp number not verified"
**Solution:** 
1. Join the Twilio WhatsApp sandbox
2. Send the provided code to the sandbox number

### Issue: "Message not delivered"
**Solution:**
1. Check if the recipient number is correct
2. Ensure the number has joined the sandbox
3. Verify your Twilio account has sufficient credits

### Issue: "Invalid phone number format"
**Solution:** Ensure phone numbers are in international format (+1234567890)

## 📞 Support

- **Twilio Support:** [Twilio Help Center](https://support.twilio.com/)
- **WhatsApp Business API:** [WhatsApp Business Documentation](https://developers.facebook.com/docs/whatsapp)
- **Project Issues:** Create an issue in this repository

## 💰 Costs

### Twilio Pricing (as of 2025):
- **WhatsApp Sandbox:** Free (for testing)
- **WhatsApp Business API:** $0.005 per message
- **Account Setup:** Free
- **Monthly Fee:** $1 (for active accounts)

### Cost Estimation:
- 100 orders/month = $0.50
- 1000 orders/month = $5.00
- 10000 orders/month = $50.00

## 🔒 Security

- Store Twilio credentials in environment variables
- Never commit credentials to version control
- Use HTTPS in production
- Implement rate limiting for webhooks
- Monitor for suspicious activity

## 📈 Monitoring

### Logs to Monitor:
- WhatsApp message delivery status
- Failed message attempts
- Webhook processing errors
- Payment confirmation success rate

### Metrics to Track:
- Message delivery rate
- Response time
- Error rates
- Cost per notification 