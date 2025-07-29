# Gundam CCS Backend

A comprehensive Django REST API backend for the Gundam Custom Collection Store - an e-commerce platform specializing in Gundam model kits with advanced payment processing, multi-currency support, and real-time notifications.

## 🚀 Features

### 🛍️ E-commerce Core
- **Product Management**: Complete product catalog with Gundam-specific fields (grade, scale, series)
- **Shopping Cart**: Full cart functionality with item management and coupons
- **Order Processing**: Complete order lifecycle management with status tracking
- **Payment Integration**: Multiple payment methods including Stripe and Pago Móvil
- **Wishlist System**: User wishlists with sharing and price alerts
- **Real-time Notifications**: WhatsApp integration for instant order updates

### 👤 User Management
- **Custom User Model**: Email-based authentication with enhanced security
- **JWT Authentication**: Secure token-based authentication with configurable lifetimes
- **Profile Management**: User profiles with address management
- **Email Verification**: Account verification system
- **Password Reset**: Secure password recovery
- **Anti-Loop Protection**: Advanced middleware to prevent authentication infinite loops

### 💳 Advanced Payment System
- **Multi-Payment Support**: Stripe, Pago Móvil (Venezuelan mobile payment), and manual payments
- **Currency Conversion**: Real-time USD to VES exchange rate management
- **Exchange Rate Service**: Multi-source rate fetching with fallback mechanisms
- **Payment Verification**: Admin-managed payment verification for Pago Móvil
- **Manual Payment Processing**: Complete workflow for bank transfers and cash payments
- **QR Code Integration**: Visual payment instructions for mobile payments

### 🌍 Venezuelan Market Features
- **Pago Móvil Integration**: Complete Venezuelan mobile payment system
- **Multi-Bank Support**: Support for all major Venezuelan banks
- **Real-time Exchange Rates**: Automatic USD/VES conversion with multiple data sources
- **Exchange Rate Alerts**: Notification system for significant rate changes
- **Local Payment Methods**: Tailored for Venezuelan e-commerce needs

### 📱 WhatsApp Business Integration
- **Instant Order Notifications**: Real-time WhatsApp messages to store owner
- **Payment Confirmations**: Automated payment status updates
- **Order Details**: Complete order information via WhatsApp
- **Twilio Integration**: Professional WhatsApp Business API implementation
- **Custom Message Templates**: Branded notification messages

### 🛠️ Technical Features
- **RESTful API**: Complete REST API with proper HTTP methods and status codes
- **API Documentation**: Swagger/OpenAPI documentation with ReDoc
- **Database Optimization**: Efficient queries with proper indexing
- **Caching**: Redis-based caching for performance optimization
- **File Uploads**: Image handling for products with media management
- **Security**: CORS, CSRF protection, rate limiting, and security headers
- **Middleware**: Custom authentication and API middleware
- **Management Commands**: Comprehensive CLI tools for administration

## 🏗️ Tech Stack

### Core Framework
- **Django**: 4.2.7 - Robust web framework
- **Django REST Framework**: 3.14.0 - API development
- **PostgreSQL/SQLite**: Database management
- **Redis**: Caching and session management

### Authentication & Security
- **JWT**: djangorestframework-simplejwt for token authentication
- **CORS**: django-cors-headers for cross-origin requests
- **Rate Limiting**: Built-in DRF throttling
- **Custom Middleware**: Anti-infinite-loop protection

### Payment Processing
- **Stripe**: 7.8.0 - International payment processing
- **Exchange Rate APIs**: Multiple sources for rate fetching
- **Custom Payment Verification**: Admin-managed payment flows

### Communication
- **Twilio**: 9.6.5 - WhatsApp Business API integration
- **Email**: SMTP configuration for notifications
- **Real-time Updates**: WebSocket-ready architecture

### Development Tools
- **API Documentation**: drf-yasg (Swagger/OpenAPI)
- **Filtering**: django-filter for advanced query filtering
- **Image Processing**: Pillow for image handling
- **Configuration**: python-decouple for environment management

## ⚡ Quick Start

### Prerequisites
- Python 3.8+
- Redis Server
- PostgreSQL (production) / SQLite (development)
- Twilio Account (for WhatsApp)
- Stripe Account (for payments)

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/Danielsvox/gundam-ccs-backend.git
   cd gundam-ccs-backend
   ```

2. **Environment Setup**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   # Create .env file (see Environment Variables section)
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Sample Data (Optional)**
   ```bash
   python manage.py setup_sample_data
   python manage.py populate_pagomovil_data
   ```

7. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

### Management Commands

The system includes several management commands for administration:

```bash
# Set up sample data for testing
python manage.py setup_sample_data

# Populate Pago Móvil bank data
python manage.py populate_pagomovil_data

# Set up production Pago Móvil recipients
python manage.py setup_production_pagomovil

# Fetch current exchange rates
python manage.py fetch_exchange_rates --force

# Process manual payments
python manage.py process_manual_payments --list-pending
python manage.py process_manual_payments --confirm-all
python manage.py process_manual_payments --order-id 123

# Test WhatsApp integration
python manage.py test_whatsapp

# Check shipping methods
python manage.py check_shipping
```

## 🔧 Environment Variables

Create a `.env` file with the following configuration:

```env
# Django Configuration
DEBUG=True
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration (Development - SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# Database Configuration (Production - PostgreSQL)
# DB_NAME=gundam_ccs_db
# DB_USER=postgres
# DB_PASSWORD=your-password
# DB_HOST=localhost
# DB_PORT=5432

# JWT Authentication
JWT_ACCESS_TOKEN_LIFETIME=24    # Hours
JWT_REFRESH_TOKEN_LIFETIME=7    # Days
JWT_SECRET_KEY=your-jwt-secret-key

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# WhatsApp/Twilio Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_FROM=+14155238886
STORE_OWNER_WHATSAPP=+1234567890

# CORS Configuration
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Media and Static Files
MEDIA_URL=/media/
MEDIA_ROOT=media
STATIC_URL=/static/
STATIC_ROOT=staticfiles
```

## 📚 API Documentation

### Base URL
- Development: `http://localhost:8000/api/v1/`
- Production: `https://yourdomain.com/api/v1/`

### Interactive Documentation
- **Swagger UI**: `/api/docs/` - Interactive API explorer
- **ReDoc**: `/api/redoc/` - Alternative documentation view
- **Health Check**: `/api/health/` - System health status
- **API Info**: `/api/info/` - API version and information

### Core Endpoints

#### Authentication
```
POST /api/v1/accounts/register/          # User registration
POST /api/v1/accounts/login/             # User login
POST /api/v1/accounts/logout/            # User logout
POST /api/v1/accounts/token/refresh/     # Refresh JWT token
POST /api/v1/accounts/password-reset/    # Password reset request
POST /api/v1/accounts/email-verify/      # Email verification
```

#### Products
```
GET    /api/v1/products/products/        # List all products
GET    /api/v1/products/products/{id}/   # Product details
GET    /api/v1/products/products/search/ # Search products
GET    /api/v1/products/categories/      # List categories
POST   /api/v1/products/products/        # Create product (admin)
PUT    /api/v1/products/products/{id}/   # Update product (admin)
DELETE /api/v1/products/products/{id}/   # Delete product (admin)
```

#### Shopping Cart
```
GET    /api/v1/cart/cart/                # Get user's cart
POST   /api/v1/cart/cart/items/add/      # Add item to cart
PUT    /api/v1/cart/cart/items/{id}/     # Update cart item
DELETE /api/v1/cart/cart/items/{id}/     # Remove from cart
POST   /api/v1/cart/cart/coupons/apply/ # Apply coupon
DELETE /api/v1/cart/cart/coupons/{id}/   # Remove coupon
```

#### Orders
```
GET  /api/v1/orders/orders/              # List user's orders
POST /api/v1/orders/orders/create/       # Create new order
GET  /api/v1/orders/orders/{id}/         # Order details
POST /api/v1/orders/orders/{id}/cancel/  # Cancel order
GET  /api/v1/orders/orders/{id}/status/  # Order status history
```

#### Payment Processing
```
POST /api/v1/payments/checkout/                    # Complete checkout
POST /api/v1/payments/create-payment-intent/       # Create Stripe payment intent
POST /api/v1/payments/confirm-payment/             # Confirm payment
POST /api/v1/payments/confirm-manual-payment/      # Confirm manual payment
GET  /api/v1/payments/payment-methods/             # List payment methods
POST /api/v1/payments/payment-methods/create/      # Add payment method
```

#### Pago Móvil (Venezuelan Mobile Payments)
```
GET  /api/v1/payments/pagomovil/info/              # Payment information
POST /api/v1/payments/pagomovil/verify/            # Submit verification
GET  /api/v1/payments/pagomovil/status/            # Check status
GET  /api/v1/payments/pagomovil/banks/             # List banks
GET  /api/v1/payments/pagomovil/recipients/        # List recipients
GET  /api/v1/payments/pagomovil/admin/             # Admin verification list
PUT  /api/v1/payments/pagomovil/{id}/status/       # Update verification status
```

#### Exchange Rate Management
```
GET  /api/v1/payments/exchange-rate/               # Current exchange rate
GET  /api/v1/payments/exchange-rate/history/       # Rate history
GET  /api/v1/payments/exchange-rate/at-timestamp/  # Rate at specific time
POST /api/v1/payments/exchange-rate/convert/       # Currency conversion
POST /api/v1/payments/exchange-rate/set-manual/    # Set manual rate
POST /api/v1/payments/exchange-rate/refresh/       # Force rate refresh
GET  /api/v1/payments/exchange-rate/stats/         # Rate statistics
GET  /api/v1/payments/exchange-rate/alerts/        # Rate change alerts
POST /api/v1/payments/exchange-rate/alerts/{id}/acknowledge/ # Acknowledge alert
```

#### Wishlist
```
GET    /api/v1/wishlist/wishlists/                 # List user's wishlists
POST   /api/v1/wishlist/wishlists/create/          # Create wishlist
GET    /api/v1/wishlist/wishlists/{id}/            # Wishlist details
PUT    /api/v1/wishlist/wishlists/{id}/            # Update wishlist
DELETE /api/v1/wishlist/wishlists/{id}/            # Delete wishlist
POST   /api/v1/wishlist/wishlists/{id}/items/add/  # Add to wishlist
DELETE /api/v1/wishlist/wishlists/{id}/items/{item_id}/ # Remove from wishlist
GET    /api/v1/wishlist/wishlists/{id}/share/      # Get share link
```

## 💳 Payment System

### Supported Payment Methods

1. **Stripe** - International credit/debit cards and digital wallets
2. **Pago Móvil** - Venezuelan mobile payment system
3. **Manual Payments** - Bank transfers, cash on delivery

### Pago Móvil Workflow

1. **Customer Checkout**: Selects Pago Móvil payment method
2. **Payment Information**: System provides bank details and QR code
3. **Customer Transfer**: Customer makes transfer via mobile banking
4. **Verification Submission**: Customer submits transfer details
5. **Admin Verification**: Store admin verifies payment
6. **Order Confirmation**: System confirms payment and processes order

### Exchange Rate Management

The system automatically fetches USD to VES exchange rates from multiple sources:

- **Primary Sources**: ExchangeRate-API, Google Finance, Open Exchange Rates
- **Fallback Rate**: Conservative rate when all sources fail
- **Rate Caching**: 1-hour cache to improve performance
- **Rate Alerts**: Notifications for significant rate changes (>5%)
- **Manual Override**: Admin can set custom rates when needed

## 📱 WhatsApp Integration

### Notification Types

1. **New Order Notifications**
   - Sent immediately when order is created
   - Includes complete order details
   - Customer contact information
   - Payment method information

2. **Payment Confirmations**
   - Sent when payment is verified
   - Payment amount and method
   - Order status updates

3. **Admin Alerts**
   - Pago Móvil verification requests
   - Exchange rate significant changes
   - System alerts and errors

### Setup Requirements

1. **Twilio Account**: Create account at console.twilio.com
2. **WhatsApp Business API**: Apply for business verification
3. **Environment Configuration**: Set Twilio credentials
4. **Phone Verification**: Verify business phone number

See [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) for detailed setup instructions.

## 🏛️ Database Models

### Core Models

#### Accounts App
- **User**: Custom user model with email authentication
- **Address**: User shipping/billing addresses
- **EmailVerification**: Email verification tokens
- **PasswordReset**: Password reset tokens

#### Products App
- **Category**: Product categories (series, grade, scale)
- **Product**: Main product model with Gundam-specific fields
- **ProductImage**: Product images with metadata
- **Review**: User reviews and ratings
- **ProductSpecification**: Detailed technical specifications

#### Cart App
- **Cart**: User shopping cart with session management
- **CartItem**: Items in cart with quantity and options
- **CartCoupon**: Available discount coupons
- **AppliedCoupon**: Coupons applied to specific carts

#### Orders App
- **Order**: Main order model with comprehensive tracking
- **OrderItem**: Items in order with pricing snapshots
- **OrderStatusHistory**: Complete order status tracking
- **ShippingMethod**: Available shipping options
- **TaxRate**: Tax rates by location and product type

#### Payments App
- **Payment**: Payment records with detailed tracking
- **PaymentMethod**: Saved user payment methods
- **Refund**: Refund records and processing
- **WebhookEvent**: Payment webhook logs
- **ExchangeRateSnapshot**: Historical exchange rate data
- **ExchangeRateLog**: Rate fetching and update logs
- **ExchangeRateAlert**: Rate change notifications
- **PagoMovilBankCode**: Venezuelan bank information
- **PagoMovilRecipient**: Payment recipient details
- **PagoMovilVerificationRequest**: Payment verification workflow

#### Wishlist App
- **Wishlist**: User wishlists with privacy settings
- **WishlistItem**: Items in wishlist with notes
- **WishlistShare**: Shared wishlist access links
- **PriceAlert**: Price drop alert subscriptions
- **WishlistAnalytics**: Usage analytics and insights

## 🛡️ Security Features

### Authentication Security
- **JWT Tokens**: Secure token-based authentication
- **Extended Token Lifetime**: 24-hour access tokens to prevent loops
- **Custom Middleware**: Anti-infinite-loop protection
- **Rate Limiting**: Request throttling to prevent abuse
- **Password Validation**: Strong password requirements

### API Security
- **CORS Configuration**: Properly configured cross-origin requests
- **CSRF Protection**: Cross-site request forgery prevention
- **Security Headers**: Comprehensive security header implementation
- **Input Validation**: Thorough input sanitization and validation
- **Error Handling**: Secure error responses without information leakage

### Payment Security
- **Stripe Integration**: PCI-compliant payment processing
- **Payment Verification**: Multi-step verification for manual payments
- **Webhook Validation**: Secure webhook signature verification
- **Audit Trails**: Complete payment activity logging

## 🔧 Development

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test accounts
python manage.py test payments
python manage.py test orders

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Code Quality
```bash
# Install development dependencies
pip install black flake8 isort

# Format code
black .
isort .

# Check code style
flake8 .
```

### Database Management
```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (development only)
python manage.py flush

# Load initial data
python manage.py loaddata fixtures/initial_data.json
```

### Development Tools
```bash
# Start Django shell with project context
python manage.py shell

# Collect static files
python manage.py collectstatic

# Create translation files
python manage.py makemessages -l es
python manage.py compilemessages
```

## 🚀 Production Deployment

### Database Configuration
```python
# Use PostgreSQL in production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
```

### Security Settings
```python
# Production security settings
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Performance Optimization
```python
# Redis caching configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60
```

### Monitoring and Logging
```python
# Production logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/gundam-ccs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'payments': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## 📖 Additional Documentation

- [WhatsApp Setup Guide](WHATSAPP_SETUP.md) - Complete WhatsApp integration setup
- [Manual Payment Workflow](MANUAL_PAYMENT_WORKFLOW.md) - Manual payment processing guide
- [Authentication Fix](AUTHENTICATION_FIX.md) - Authentication improvements and troubleshooting
- [API Documentation](http://localhost:8000/api/docs/) - Interactive Swagger documentation

## 🤝 Contributing

1. **Fork the Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make Changes and Test**
   ```bash
   python manage.py test
   black .
   flake8 .
   ```
4. **Commit Changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
5. **Push to Branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Create Pull Request**

### Contribution Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Include docstrings for all functions and classes
- Ensure backwards compatibility when possible

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Email**: support@gundamccs.com
- **Documentation**: [API Docs](http://localhost:8000/api/docs/)
- **Issues**: [GitHub Issues](https://github.com/Danielsvox/gundam-ccs-backend/issues)
- **WhatsApp Setup**: See [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md)
- **Payment Issues**: See [MANUAL_PAYMENT_WORKFLOW.md](MANUAL_PAYMENT_WORKFLOW.md)

## 🎯 Roadmap

### Upcoming Features
- [ ] PayPal integration
- [ ] Cryptocurrency payment support
- [ ] Advanced inventory management
- [ ] Multi-language support
- [ ] Mobile app API enhancements
- [ ] Advanced analytics dashboard
- [ ] Subscription-based products
- [ ] Social features and product sharing

### Recent Updates
- ✅ Pago Móvil Venezuelan payment integration
- ✅ Multi-source exchange rate management
- ✅ WhatsApp Business API integration
- ✅ Authentication infinite loop prevention
- ✅ Advanced payment verification system
- ✅ Comprehensive admin interface
- ✅ Enhanced security middleware
- ✅ Production-ready deployment configuration 