import logging
from django.http import JsonResponse
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class APIHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add API-specific headers for better cross-origin compatibility.
    """
    
    def process_response(self, request, response):
        """Add API headers to all responses."""
        # Add API version header
        response['X-API-Version'] = '1.0'
        
        # Add security headers for API responses
        if request.path.startswith('/api/'):
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # Add JSON content type for API responses if not set
            if not response.get('Content-Type'):
                response['Content-Type'] = 'application/json'
        
        return response


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Custom middleware to handle JWT authentication errors gracefully
    and prevent infinite loops from expired tokens.
    """

    def process_request(self, request):
        """Process request and handle authentication errors."""
        # Skip middleware for certain paths
        if self._should_skip_middleware(request.path):
            return None

        # Check if request has authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        try:
            # Try to authenticate the token
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(
                jwt_auth.get_raw_token(request)
            )
            user = jwt_auth.get_user(validated_token)

            # If we get here, token is valid
            request.user = user
            return None

        except (TokenError, InvalidToken) as e:
            # Token is invalid or expired
            logger.warning(
                f"Invalid JWT token in request to {request.path}: {str(e)}")

            # Return a clear error response to prevent infinite loops
            return JsonResponse({
                'error': 'Authentication failed',
                'message': 'Token is invalid or expired. Please login again.',
                'code': 'TOKEN_EXPIRED'
            }, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            # Other authentication errors
            logger.error(
                f"Authentication error in request to {request.path}: {str(e)}")
            return None

    def _should_skip_middleware(self, path):
        """Check if middleware should be skipped for this path."""
        skip_paths = [
            '/admin/',
            '/api/docs/',
            '/api/redoc/',
            '/api/health/',
            '/api/info/',
            '/api/v1/accounts/login/',
            '/api/v1/accounts/register/',
            '/api/v1/accounts/token/refresh/',
            '/api/v1/accounts/password-reset/',
            '/api/v1/accounts/email-verify/',
            '/api/v1/payments/pagomovil/info/',  # Allow anonymous access
            '/api/v1/payments/pagomovil/banks/',  # Allow anonymous access
            '/api/v1/payments/pagomovil/recipients/',  # Allow anonymous access
            '/api/v1/payments/exchange-rate/',  # Allow anonymous access
            '/media/',
            '/static/',
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)
