"""
Middleware do logowania requestów
"""
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Middleware które loguje każdy request"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log przed przetworzeniem requestu
        print(f"🔵 REQUEST: {request.method} {request.path}")
        
        response = self.get_response(request)
        
        # Log po przetworzeniu requestu
        print(f"🟢 RESPONSE: {response.status_code} {request.method} {request.path}")
        
        return response
