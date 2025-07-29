from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json


@method_decorator(csrf_exempt, name='dispatch')
class HealthCheckView(View):
    """
    Simple health check endpoint to test CORS and API connectivity.
    """
    
    def get(self, request):
        """Return API health status."""
        return JsonResponse({
            'status': 'healthy',
            'message': 'Gundam CCS API is running',
            'version': '1.0',
            'cors_enabled': True,
            'timestamp': request.GET.get('timestamp', 'not_provided')
        })
    
    def post(self, request):
        """Test POST request handling."""
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = dict(request.POST)
            
            return JsonResponse({
                'status': 'success',
                'message': 'POST request received',
                'received_data': data,
                'cors_enabled': True
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)


class CORSTestView(View):
    """
    Dedicated CORS test endpoint.
    """
    
    def get(self, request):
        """Test CORS GET request."""
        origin = request.META.get('HTTP_ORIGIN', 'no-origin')
        user_agent = request.META.get('HTTP_USER_AGENT', 'no-user-agent')
        
        return JsonResponse({
            'cors_test': 'success',
            'origin': origin,
            'user_agent': user_agent,
            'headers': dict(request.headers),
            'method': 'GET'
        })
    
    def post(self, request):
        """Test CORS POST request."""
        origin = request.META.get('HTTP_ORIGIN', 'no-origin')
        
        return JsonResponse({
            'cors_test': 'success',
            'origin': origin,
            'method': 'POST',
            'content_type': request.content_type
        })
    
    def options(self, request):
        """Handle CORS preflight requests."""
        response = JsonResponse({'cors_preflight': 'success'})
        return response
