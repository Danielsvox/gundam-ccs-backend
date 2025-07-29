# Payments Module Documentation

## Overview

The payments module is the core financial processing system for the Gundam CCS backend, handling multiple payment methods, currency conversion, and real-time notifications. It supports international payments via Stripe and Venezuelan mobile payments via Pago Móvil.

## 🚀 Features

### Payment Methods
- **Stripe Integration**: International credit/debit cards and digital wallets
- **Pago Móvil**: Venezuelan mobile payment system with multi-bank support
- **Manual Payments**: Bank transfers and cash on delivery with admin verification

### Currency Management
- **Real-time Exchange Rates**: Multi-source USD to VES conversion
- **Rate Caching**: 1-hour cache for performance optimization
- **Rate Alerts**: Notifications for significant rate changes (>5%)
- **Manual Rate Override**: Admin can set custom exchange rates

### Payment Verification
- **Admin Workflow**: Manual payment verification system
- **QR Code Support**: Visual payment instructions
- **Status Tracking**: Complete payment lifecycle management
- **Audit Trails**: Comprehensive payment activity logging

### Notifications
- **WhatsApp Integration**: Real-time order and payment notifications
- **Email Notifications**: Payment confirmations and alerts
- **Admin Alerts**: Payment verification requests and system notifications

## 📁 Module Structure

```
payments/
├── models.py                 # Database models
├── views.py                  # API views and endpoints
├── serializers.py           # Data serialization
├── urls.py                  # URL routing
├── admin.py                 # Django admin interface
├── services/
│   ├── exchange_rate_service.py    # Exchange rate management
│   ├── payment_processor.py       # Payment processing logic
│   └── whatsapp_service.py        # WhatsApp notifications
├── management/commands/
│   ├── fetch_exchange_rates.py    # Rate fetching command
│   ├── process_manual_payments.py # Manual payment processing
│   ├── setup_sample_data.py       # Sample data creation
│   ├── setup_production_pagomovil.py # Production setup
│   ├── populate_pagomovil_data.py # Bank data population
│   └── test_whatsapp.py           # WhatsApp testing
└── migrations/              # Database migrations
```

## 🏗️ Database Models

### Core Payment Models

#### Payment
```python
class Payment(models.Model):
    order = models.ForeignKey('orders.Order')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### PaymentMethod
```python
class PaymentMethod(models.Model):
    user = models.ForeignKey('accounts.User')
    type = models.CharField(max_length=20)
    stripe_payment_method_id = models.CharField(max_length=255)
    last_four = models.CharField(max_length=4)
    brand = models.CharField(max_length=20)
    is_default = models.BooleanField(default=False)
```

### Exchange Rate Models

#### ExchangeRateSnapshot
```python
class ExchangeRateSnapshot(models.Model):
    usd_to_ves = models.DecimalField(max_digits=10, decimal_places=4)
    source = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_manual = models.BooleanField(default=False)
```

#### ExchangeRateLog
```python
class ExchangeRateLog(models.Model):
    previous_rate = models.DecimalField(max_digits=10, decimal_places=4)
    new_rate = models.DecimalField(max_digits=10, decimal_places=4)
    change_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    source = models.CharField(max_length=50)
    fetch_duration = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
```

#### ExchangeRateAlert
```python
class ExchangeRateAlert(models.Model):
    rate_log = models.ForeignKey(ExchangeRateLog)
    alert_type = models.CharField(max_length=20)
    threshold_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_acknowledged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Pago Móvil Models

#### PagoMovilBankCode
```python
class PagoMovilBankCode(models.Model):
    bank_code = models.CharField(max_length=4, unique=True)
    bank_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
```

#### PagoMovilRecipient
```python
class PagoMovilRecipient(models.Model):
    bank_code = models.ForeignKey(PagoMovilBankCode)
    recipient_id = models.CharField(max_length=20)
    recipient_phone = models.CharField(max_length=20)
    recipient_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
```

#### PagoMovilVerificationRequest
```python
class PagoMovilVerificationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey('accounts.User')
    order = models.ForeignKey('orders.Order')
    sender_id = models.CharField(max_length=20)
    sender_phone = models.CharField(max_length=20)
    bank_code = models.ForeignKey(PagoMovilBankCode)
    recipient = models.ForeignKey(PagoMovilRecipient)
    amount_ves = models.DecimalField(max_digits=15, decimal_places=2)
    exchange_rate_used = models.DecimalField(max_digits=10, decimal_places=4)
    usd_equivalent = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reference_number = models.CharField(max_length=50)
```

## 🔌 API Endpoints

### Payment Processing
```
POST /api/v1/payments/checkout/                    # Complete checkout process
POST /api/v1/payments/create-payment-intent/       # Create Stripe payment intent
POST /api/v1/payments/confirm-payment/             # Confirm payment completion
POST /api/v1/payments/confirm-manual-payment/      # Confirm manual payment
GET  /api/v1/payments/payment-methods/             # List user payment methods
POST /api/v1/payments/payment-methods/create/      # Add new payment method
PUT  /api/v1/payments/payment-methods/{id}/        # Update payment method
DELETE /api/v1/payments/payment-methods/{id}/      # Remove payment method
```

### Pago Móvil Endpoints
```
GET  /api/v1/payments/pagomovil/info/              # Get payment information
POST /api/v1/payments/pagomovil/verify/            # Submit verification request
GET  /api/v1/payments/pagomovil/status/            # Check verification status
GET  /api/v1/payments/pagomovil/banks/             # List available banks
GET  /api/v1/payments/pagomovil/recipients/        # List payment recipients
GET  /api/v1/payments/pagomovil/admin/             # Admin verification list
PUT  /api/v1/payments/pagomovil/{id}/status/       # Update verification status
```

### Exchange Rate Endpoints
```
GET  /api/v1/payments/exchange-rate/               # Current exchange rate
GET  /api/v1/payments/exchange-rate/history/       # Historical rates
GET  /api/v1/payments/exchange-rate/at-timestamp/  # Rate at specific time
POST /api/v1/payments/exchange-rate/convert/       # Currency conversion
POST /api/v1/payments/exchange-rate/set-manual/    # Set manual rate
POST /api/v1/payments/exchange-rate/refresh/       # Force rate refresh
GET  /api/v1/payments/exchange-rate/stats/         # Rate statistics
GET  /api/v1/payments/exchange-rate/alerts/        # Rate change alerts
POST /api/v1/payments/exchange-rate/alerts/{id}/acknowledge/ # Acknowledge alert
```

### Webhook Endpoints
```
POST /api/v1/payments/webhook/stripe/              # Stripe webhook handler
```

## ⚙️ Services

### ExchangeRateService

The exchange rate service manages USD to VES conversion with multiple data sources.

#### Key Features
- **Multi-source Fetching**: Primary and fallback rate sources
- **Intelligent Caching**: 1-hour cache with fallback mechanisms
- **Rate Change Detection**: Automatic alerts for significant changes
- **Manual Override**: Admin can set custom rates

#### Usage Example
```python
from payments.services.exchange_rate_service import exchange_rate_service

# Get current rate
rate_data = exchange_rate_service.get_current_rate()
print(f"Current rate: {rate_data['usd_to_ves']}")

# Convert currencies
usd_amount = Decimal('100.00')
ves_amount = exchange_rate_service.convert_usd_to_ves(usd_amount)

# Force refresh rate
success = exchange_rate_service.fetch_and_store_rate(force=True)
```

#### Rate Sources
1. **ExchangeRate-API**: Primary free API source
2. **Google Finance**: Web scraping fallback
3. **Open Exchange Rates**: Premium API option
4. **Manual Override**: Admin-set rates

### PaymentProcessor

Handles payment processing logic and workflow management.

#### Key Features
- **Multi-method Support**: Stripe, Pago Móvil, manual payments
- **Status Management**: Complete payment lifecycle tracking
- **Error Handling**: Robust error handling and logging
- **Notification Integration**: Automatic WhatsApp notifications

### WhatsAppService

Manages WhatsApp notifications for payments and orders.

#### Key Features
- **Order Notifications**: New order alerts to store owner
- **Payment Confirmations**: Payment status updates
- **Admin Alerts**: Verification requests and system alerts
- **Template Management**: Customizable message templates

#### Usage Example
```python
from payments.services.whatsapp_service import whatsapp_service

# Send order notification
success = whatsapp_service.send_order_notification(order)

# Send payment confirmation
success = whatsapp_service.send_payment_confirmation(payment)

# Send admin alert
success = whatsapp_service.send_admin_alert("Payment verification needed", details)
```

## 🛠️ Management Commands

### fetch_exchange_rates
Fetch and store current exchange rates from external sources.

```bash
# Fetch current rates
python manage.py fetch_exchange_rates

# Force refresh ignoring cache
python manage.py fetch_exchange_rates --force

# Use specific source
python manage.py fetch_exchange_rates --source exchangerate_host

# Verbose output
python manage.py fetch_exchange_rates --verbose
```

### process_manual_payments
Manage manual payment processing and confirmation.

```bash
# List pending manual payments
python manage.py process_manual_payments --list-pending

# Confirm all pending payments
python manage.py process_manual_payments --confirm-all

# Confirm specific order payment
python manage.py process_manual_payments --order-id 123
```

### setup_production_pagomovil
Set up production Pago Móvil recipient data.

```bash
# Set up production recipients
python manage.py setup_production_pagomovil

# Clear existing and create new
python manage.py setup_production_pagomovil --clear
```

### populate_pagomovil_data
Populate Venezuelan bank codes and sample data.

```bash
# Populate bank data
python manage.py populate_pagomovil_data
```

### test_whatsapp
Test WhatsApp integration and message delivery.

```bash
# Test WhatsApp configuration
python manage.py test_whatsapp
```

## 📱 Pago Móvil Integration

### Payment Flow

1. **Customer Selection**: Customer chooses Pago Móvil at checkout
2. **Rate Calculation**: System fetches current USD to VES rate
3. **Payment Info Display**: Customer receives bank details and QR code
4. **Customer Transfer**: Customer makes transfer via mobile banking
5. **Verification Submission**: Customer submits transfer details
6. **Admin Review**: Store admin verifies payment in admin panel
7. **Order Confirmation**: System processes order upon verification

### Verification Process

#### Customer Submission
```json
{
  "sender_id": "V-12345678",
  "sender_phone": "+584241234567",
  "bank_code": "0134",
  "recipient_id": "V-24760431",
  "amount_ves": "3800.00",
  "reference_number": "123456789"
}
```

#### Admin Actions
- **Approve**: Confirms payment and processes order
- **Reject**: Rejects payment with reason
- **Request Info**: Requests additional information from customer

### QR Code Integration

The system generates QR codes for easy mobile payment access:

```python
# QR code contains payment information
qr_data = {
    "bank": "0134",
    "recipient": "V-24760431",
    "phone": "+584242263633",
    "amount": "3800.00"
}
```

## 💱 Exchange Rate Management

### Rate Fetching Strategy

1. **Primary Source**: ExchangeRate-API (free, reliable)
2. **Secondary Source**: Google Finance (web scraping)
3. **Tertiary Source**: Open Exchange Rates (premium)
4. **Fallback Rate**: Conservative default rate (38.0 VES/USD)

### Rate Change Alerts

The system monitors rate changes and sends alerts when:
- Rate changes by more than 5% (configurable threshold)
- Rate fetching fails multiple times
- Manual rate override is applied

### Caching Strategy

- **Cache Duration**: 1 hour for performance optimization
- **Cache Keys**: Structured keys for rate data and metadata
- **Cache Invalidation**: Automatic on manual rate updates
- **Fallback Mechanism**: Uses cached rate if fetching fails

## 🔒 Security Features

### Payment Security
- **PCI Compliance**: Stripe integration for secure card processing
- **Webhook Validation**: Secure webhook signature verification
- **Input Sanitization**: Thorough validation of all payment data
- **Audit Trails**: Complete logging of payment activities

### API Security
- **Authentication**: JWT token-based authentication
- **Rate Limiting**: Request throttling to prevent abuse
- **CORS Configuration**: Proper cross-origin request handling
- **Error Handling**: Secure error responses without data leakage

### Data Protection
- **Sensitive Data**: No card data stored locally
- **Encryption**: Sensitive fields encrypted at rest
- **Access Control**: Role-based access to payment data
- **Audit Logging**: Complete activity tracking

## 🧪 Testing

### Unit Tests
```bash
# Run payment module tests
python manage.py test payments

# Run specific test class
python manage.py test payments.tests.PaymentModelTest

# Run with coverage
coverage run --source='payments' manage.py test payments
coverage report
```

### Integration Tests
```bash
# Test Stripe integration
python manage.py test payments.tests.StripeIntegrationTest

# Test Pago Móvil workflow
python manage.py test payments.tests.PagoMovilWorkflowTest

# Test exchange rate service
python manage.py test payments.tests.ExchangeRateServiceTest
```

### Manual Testing
```bash
# Test WhatsApp notifications
python manage.py test_whatsapp

# Test exchange rate fetching
python manage.py fetch_exchange_rates --verbose

# Test payment processing
curl -X POST http://localhost:8000/api/v1/payments/checkout/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"shipping_address": {...}}'
```

## 📊 Monitoring and Analytics

### Key Metrics
- **Payment Success Rate**: Percentage of successful payments
- **Processing Time**: Average payment processing duration
- **Exchange Rate Accuracy**: Rate source reliability metrics
- **Notification Delivery**: WhatsApp message delivery rates

### Logging
- **Payment Activities**: All payment actions logged
- **Rate Changes**: Exchange rate updates tracked
- **Error Events**: Payment failures and system errors
- **Performance Metrics**: API response times and throughput

### Health Checks
```bash
# Check payment system health
curl http://localhost:8000/api/health/

# Check exchange rate service
curl http://localhost:8000/api/v1/payments/exchange-rate/

# Check WhatsApp service
python manage.py test_whatsapp
```

## 🚀 Production Deployment

### Environment Variables
```env
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_your_live_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_live_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_live_webhook_secret

# Twilio/WhatsApp Configuration
TWILIO_ACCOUNT_SID=your_production_account_sid
TWILIO_AUTH_TOKEN=your_production_auth_token
TWILIO_WHATSAPP_FROM=+1234567890
STORE_OWNER_WHATSAPP=+584242263633

# Exchange Rate API Keys
OPEN_EXCHANGE_RATES_API_KEY=your_api_key
```

### Database Optimization
```sql
-- Add indexes for performance
CREATE INDEX idx_payment_status ON payments_payment(status);
CREATE INDEX idx_payment_method ON payments_payment(payment_method);
CREATE INDEX idx_exchange_rate_timestamp ON payments_exchangeratesnapshot(timestamp);
```

### Monitoring Setup
```python
# Custom logging configuration
LOGGING = {
    'loggers': {
        'payments': {
            'handlers': ['file', 'sentry'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

## 🔧 Configuration

### Django Settings
```python
# Payment settings
PAYMENT_SETTINGS = {
    'STRIPE_ENABLED': True,
    'PAGOMOVIL_ENABLED': True,
    'MANUAL_PAYMENTS_ENABLED': True,
    'DEFAULT_CURRENCY': 'USD',
    'EXCHANGE_RATE_CACHE_TIMEOUT': 3600,
    'EXCHANGE_RATE_ALERT_THRESHOLD': 5.0,
}

# WhatsApp settings
WHATSAPP_SETTINGS = {
    'ENABLED': True,
    'ORDER_NOTIFICATIONS': True,
    'PAYMENT_NOTIFICATIONS': True,
    'ADMIN_ALERTS': True,
}
```

### Celery Tasks (Future Enhancement)
```python
# Asynchronous task suggestions
@celery.task
def fetch_exchange_rates():
    """Periodic exchange rate fetching."""
    pass

@celery.task
def send_whatsapp_notification(message_data):
    """Asynchronous WhatsApp message sending."""
    pass

@celery.task
def process_payment_webhooks(webhook_data):
    """Process payment webhooks asynchronously."""
    pass
```

## 📖 API Documentation

For complete API documentation with request/response examples, visit:
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/

## 🤝 Contributing

When contributing to the payments module:

1. **Follow Security Best Practices**: Never expose sensitive payment data
2. **Test Thoroughly**: Test all payment flows and edge cases
3. **Document Changes**: Update API documentation for endpoint changes
4. **Performance Considerations**: Monitor impact on payment processing speed
5. **Error Handling**: Ensure graceful handling of payment failures

## 📞 Support

For payments module support:
- **Payment Issues**: Check logs in `/logs/payments.log`
- **Exchange Rate Problems**: Verify API key configuration
- **WhatsApp Issues**: Check Twilio account status and credits
- **Stripe Problems**: Verify webhook endpoint configuration 