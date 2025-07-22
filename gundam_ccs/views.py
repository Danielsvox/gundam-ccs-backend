from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import os
from django.conf import settings


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint to verify the API is running
    """
    return Response({
        'status': 'healthy',
        'message': 'Gundam CCS API is running',
        'version': '1.0.0',
        'environment': 'development' if settings.DEBUG else 'production'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_info(request):
    """
    API information endpoint
    """
    return Response({
        'name': 'Gundam CCS API',
        'description': 'E-commerce platform for Gundam model kits',
        'version': '1.0.0',
        'endpoints': {
            'accounts': '/api/v1/accounts/',
            'products': '/api/v1/products/',
            'cart': '/api/v1/cart/',
            'orders': '/api/v1/orders/',
            'payments': '/api/v1/payments/',
            'wishlist': '/api/v1/wishlist/',
            'docs': '/api/docs/',
            'redoc': '/api/redoc/'
        }
    }, status=status.HTTP_200_OK)
