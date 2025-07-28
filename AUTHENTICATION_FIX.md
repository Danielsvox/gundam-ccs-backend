# Authentication Infinite Loop Fix

## Problem Description

The backend was experiencing infinite loops when users left the page idle for extended periods (over 60 minutes). This was caused by:

1. **Short JWT Token Lifetime**: Access tokens expired after 60 minutes
2. **Frontend Retry Logic**: When tokens expired, frontend kept retrying requests
3. **401 Unauthorized Responses**: Backend returned 401 for expired tokens
4. **Infinite Loop**: Frontend retry logic created an endless cycle of failed requests

## Symptoms

- Server logs showing repeated 401 Unauthorized requests
- High CPU usage and server overload
- Infinite loop of cart and shipping-methods API calls
- Only solution was server restart

## Root Cause

```python
# Before: Very short token lifetime
'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60)  # 1 hour
'REFRESH_TOKEN_LIFETIME': timedelta(days=1)     # 1 day
```

## Solutions Implemented

### 1. Extended JWT Token Lifetime

```python
# After: Much longer token lifetime
'ACCESS_TOKEN_LIFETIME': timedelta(hours=24)    # 24 hours
'REFRESH_TOKEN_LIFETIME': timedelta(days=7)     # 7 days
```

**Benefits:**
- Reduces frequency of token expiration
- Less likely to trigger infinite loops
- Better user experience

### 2. Rate Limiting

```python
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle'
],
'DEFAULT_THROTTLE_RATES': {
    'anon': '100/hour',
    'user': '1000/hour',
}
```

**Benefits:**
- Prevents abuse and infinite loops
- Protects server from overload
- Graceful degradation under load

### 3. Custom Authentication Middleware

Created `gundam_ccs.middleware.JWTAuthenticationMiddleware` to:

- Handle token expiration gracefully
- Return clear error messages
- Prevent infinite loops
- Log authentication issues

**Features:**
- Early token validation
- Clear error responses
- Path-based exclusions
- Comprehensive logging

### 4. Enhanced Error Handling

Added better error handling to cart views:

```python
try:
    cart, created = Cart.objects.get_or_create(user=request.user)
    serializer = CartSerializer(cart)
    return Response(serializer.data)
except Exception as e:
    logger.error(f"Error fetching cart for user {request.user.id}: {str(e)}")
    return Response({
        'error': 'Failed to fetch cart',
        'message': 'An error occurred while loading your cart.'
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

### 5. Authentication Health Check

Added `/api/auth-health/` endpoint to:

- Diagnose authentication issues
- Check token validity
- Provide debugging information
- Help frontend handle auth errors

## Configuration Changes

### Environment Variables

Update your `.env` file:

```env
# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=24    # Hours
JWT_REFRESH_TOKEN_LIFETIME=7    # Days
JWT_SECRET_KEY=your-jwt-secret-key
```

### Middleware Stack

Added custom middleware to `settings.py`:

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'gundam_ccs.middleware.JWTAuthenticationMiddleware',
]
```

## Testing the Fix

### 1. Test Token Expiration

```bash
# Check current token status
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/auth-health/
```

### 2. Test Rate Limiting

```bash
# Make multiple requests to test rate limiting
for i in {1..10}; do
  curl -H "Authorization: Bearer YOUR_TOKEN" \
       http://localhost:8000/api/v1/cart/
done
```

### 3. Test Error Handling

```bash
# Test with invalid token
curl -H "Authorization: Bearer INVALID_TOKEN" \
     http://localhost:8000/api/v1/cart/
```

## Frontend Recommendations

### 1. Implement Token Refresh Logic

```javascript
// Example token refresh logic
const refreshToken = async () => {
  try {
    const response = await fetch('/api/v1/accounts/token/refresh/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh: localStorage.getItem('refresh_token')
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      return data.access;
    }
  } catch (error) {
    // Redirect to login
    window.location.href = '/login';
  }
};
```

### 2. Add Request Interceptors

```javascript
// Example axios interceptor
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const newToken = await refreshToken();
      if (newToken) {
        // Retry original request
        error.config.headers.Authorization = `Bearer ${newToken}`;
        return axios.request(error.config);
      }
    }
    return Promise.reject(error);
  }
);
```

### 3. Handle Authentication Errors Gracefully

```javascript
// Example error handling
const handleAuthError = (error) => {
  if (error.response?.status === 401) {
    // Clear tokens and redirect to login
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  }
};
```

## Monitoring and Logging

### 1. Check Authentication Logs

```bash
# Monitor authentication errors
tail -f logs/django.log | grep "Invalid JWT token"
```

### 2. Monitor Rate Limiting

```bash
# Check for rate limit violations
tail -f logs/django.log | grep "throttle"
```

### 3. Health Check Monitoring

```bash
# Regular health checks
curl http://localhost:8000/api/health/
curl http://localhost:8000/api/auth-health/
```

## Future Improvements

### 1. Implement Token Refresh Endpoint

Consider implementing a more robust token refresh mechanism:

```python
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def refresh_token_view(request):
    """Custom token refresh with additional validation."""
    # Add custom logic here
    pass
```

### 2. Add Session Management

Consider implementing session-based authentication as a fallback:

```python
# Add session authentication as backup
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}
```

### 3. Implement Circuit Breaker

Consider adding circuit breaker pattern to prevent cascading failures:

```python
# Example circuit breaker implementation
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
```

## Conclusion

These changes should significantly reduce the likelihood of authentication-related infinite loops while improving the overall user experience and system stability.

The key improvements are:
- ✅ Extended token lifetime (24 hours vs 1 hour)
- ✅ Rate limiting to prevent abuse
- ✅ Graceful error handling
- ✅ Better logging and monitoring
- ✅ Authentication health checks
- ✅ Custom middleware for token validation

Monitor the system after deployment to ensure the issue is resolved. 