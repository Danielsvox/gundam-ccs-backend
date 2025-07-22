# Gundam CCS Backend

A comprehensive Django REST API backend for the Gundam Custom Collection Store - an e-commerce platform specializing in Gundam model kits.

## Features

### 🛍️ E-commerce Core
- **Product Management**: Complete product catalog with Gundam-specific fields (grade, scale, series)
- **Shopping Cart**: Full cart functionality with item management
- **Order Processing**: Complete order lifecycle management
- **Payment Integration**: Stripe payment processing with webhooks
- **Wishlist System**: User wishlists with sharing and price alerts

### 👤 User Management
- **Custom User Model**: Email-based authentication
- **JWT Authentication**: Secure token-based authentication
- **Profile Management**: User profiles with address management
- **Email Verification**: Account verification system
- **Password Reset**: Secure password recovery

### 🎯 Gundam-Specific Features
- **Product Categories**: Organized by series, grade, scale
- **Product Specifications**: Detailed model kit specifications
- **Reviews & Ratings**: User-generated content
- **Price Alerts**: Notifications for price drops
- **Wishlist Sharing**: Share wishlists with friends

### 🛠️ Technical Features
- **RESTful API**: Complete REST API with proper HTTP methods
- **API Documentation**: Swagger/OpenAPI documentation
- **Database Optimization**: Efficient queries with proper indexing
- **Caching**: Redis-based caching for performance
- **File Uploads**: Image handling for products
- **Security**: CORS, CSRF protection, and security headers

## Tech Stack

- **Framework**: Django 4.2.7
- **API**: Django REST Framework 3.14.0
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Payment**: Stripe
- **Caching**: Redis
- **Documentation**: drf-yasg (Swagger/OpenAPI)
- **CORS**: django-cors-headers
- **Environment**: python-decouple

## Installation

### Prerequisites
- Python 3.8+
- pip
- Redis (for caching)
- PostgreSQL (for production)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Danielsvox/gundam-ccs-backend.git
   cd gundam-ccs-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Authentication
- `POST /api/v1/accounts/register/` - User registration
- `POST /api/v1/accounts/login/` - User login
- `POST /api/v1/accounts/logout/` - User logout
- `POST /api/v1/accounts/token/refresh/` - Refresh JWT token

### Products
- `GET /api/v1/products/products/` - List all products
- `GET /api/v1/products/products/{id}/` - Product details
- `GET /api/v1/products/products/search/` - Search products
- `GET /api/v1/products/categories/` - List categories

### Cart
- `GET /api/v1/cart/cart/` - Get user's cart
- `POST /api/v1/cart/cart/items/add/` - Add item to cart
- `PUT /api/v1/cart/cart/items/{id}/update/` - Update cart item
- `DELETE /api/v1/cart/cart/items/{id}/remove/` - Remove from cart

### Orders
- `GET /api/v1/orders/orders/` - List user's orders
- `POST /api/v1/orders/orders/create/` - Create new order
- `GET /api/v1/orders/orders/{id}/` - Order details
- `POST /api/v1/orders/orders/{id}/cancel/` - Cancel order

### Payments
- `POST /api/v1/payments/payments/create/` - Create payment
- `POST /api/v1/payments/payment-intent/create/` - Create payment intent
- `POST /api/v1/payments/webhooks/stripe/` - Stripe webhook

### Wishlist
- `GET /api/v1/wishlist/wishlists/` - List user's wishlists
- `POST /api/v1/wishlist/wishlists/create/` - Create wishlist
- `POST /api/v1/wishlist/wishlists/{id}/items/add/` - Add to wishlist
- `DELETE /api/v1/wishlist/wishlists/{id}/items/{item_id}/remove/` - Remove from wishlist

### Documentation
- `GET /api/docs/` - Swagger UI documentation
- `GET /api/redoc/` - ReDoc documentation
- `GET /api/health/` - Health check
- `GET /api/info/` - API information

## Environment Variables

Create a `.env` file with the following variables:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=gundam_ccs_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# JWT
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1
JWT_SECRET_KEY=your-jwt-secret

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Media & Static
MEDIA_URL=/media/
MEDIA_ROOT=media
STATIC_URL=/static/
STATIC_ROOT=staticfiles
```

## Database Models

### Accounts
- **User**: Custom user model with email authentication
- **Address**: User shipping/billing addresses
- **EmailVerification**: Email verification tokens
- **PasswordReset**: Password reset tokens

### Products
- **Category**: Product categories (series, grade, etc.)
- **Product**: Main product model with Gundam-specific fields
- **ProductImage**: Product images
- **Review**: User reviews and ratings
- **ProductSpecification**: Detailed product specifications

### Cart
- **Cart**: User shopping cart
- **CartItem**: Items in cart
- **CartCoupon**: Available coupons
- **AppliedCoupon**: Coupons applied to cart

### Orders
- **Order**: Main order model
- **OrderItem**: Items in order
- **OrderStatusHistory**: Order status tracking
- **ShippingMethod**: Available shipping methods
- **TaxRate**: Tax rates by location

### Payments
- **Payment**: Payment records
- **Refund**: Refund records
- **PaymentMethod**: Saved payment methods
- **WebhookEvent**: Webhook event logs
- **Subscription**: Subscription management

## 💳 Checkout & Payment System

### Payment Methods Supported:
- **Stripe** - Credit/Debit cards, digital wallets
- **PayPal** - PayPal accounts (future implementation)
- **Manual** - Bank transfers, cash on delivery

### Checkout Flow:
1. **Cart Review** - User reviews items and applies coupons
2. **Shipping Information** - User provides delivery address
3. **Payment Method** - User selects payment method
4. **Payment Processing** - Secure payment via Stripe
5. **Order Confirmation** - Order created and payment confirmed
6. **WhatsApp Notification** - Store owner receives instant notification

### WhatsApp Integration:
- **Instant Notifications** - Store owners receive WhatsApp messages for new orders
- **Payment Confirmations** - Real-time payment status updates
- **Order Details** - Complete order information including customer details
- **Business Account** - Uses Twilio WhatsApp Business API

### API Endpoints:

#### Checkout Process:
```
POST /api/v1/payments/checkout/          # Complete checkout
POST /api/v1/payments/create-payment-intent/  # Create payment intent
POST /api/v1/payments/confirm-payment/   # Confirm payment
```

#### Payment Methods:
```
GET    /api/v1/payments/payment-methods/     # List payment methods
POST   /api/v1/payments/payment-methods/create/  # Add payment method
PUT    /api/v1/payments/payment-methods/{id}/    # Update payment method
DELETE /api/v1/payments/payment-methods/{id}/    # Remove payment method
```

#### Webhooks:
```
POST /api/v1/payments/webhook/stripe/    # Stripe webhook handler
```

### Environment Variables Required:
```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# WhatsApp/Twilio Configuration
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=+14155238886  # Twilio WhatsApp number
STORE_OWNER_WHATSAPP=+1234567890   # Store owner's WhatsApp number
```

### Frontend Integration Example:
```javascript
// Complete checkout process
const checkout = async (checkoutData) => {
  const response = await fetch('/api/v1/payments/checkout/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      shipping_address: {
        name: 'John Doe',
        line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'US',
        phone: '+1234567890'
      },
      customer_notes: 'Please deliver after 6 PM'
    })
  });
  
  const result = await response.json();
  return result; // Contains client_secret for Stripe
};

// Confirm payment with Stripe
const confirmPayment = async (paymentIntentId) => {
  const response = await fetch('/api/v1/payments/confirm-payment/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      payment_intent_id: paymentIntentId
    })
  });
  
  return await response.json();
};
```

### Wishlist
- **Wishlist**: User wishlists
- **WishlistItem**: Items in wishlist
- **WishlistShare**: Shared wishlist links
- **PriceAlert**: Price drop alerts
- **WishlistAnalytics**: Wishlist analytics

## Development

### Running Tests
```bash
python manage.py test
```

### Code Formatting
```bash
# Install black for code formatting
pip install black
black .
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating Superuser
```bash
python manage.py createsuperuser
```

## Production Deployment

### Database
- Use PostgreSQL for production
- Configure connection pooling
- Set up regular backups

### Security
- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure HTTPS
- Set up proper CORS origins
- Use environment variables for sensitive data

### Performance
- Configure Redis for caching
- Set up CDN for static/media files
- Use database connection pooling
- Enable database query optimization

### Monitoring
- Set up logging
- Monitor application performance
- Set up error tracking
- Configure health checks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, email support@gundamccs.com or create an issue in the repository. 