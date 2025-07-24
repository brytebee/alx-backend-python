import logging
import time
from datetime import datetime, time as dt_time
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Global utility function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Start timing
        start_time = time.time()

        # Log request details
        logger.info(f"Request: {request.method} {request.path}")
        logger.info(f"User: {request.user}")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"IP: {get_client_ip(request)}")
        
        response = self.get_response(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response details
        logger.info(f"Response: {response.status_code}")
        logger.info(f"Processing time: {process_time:.3f}s")

        return response

class RestrictAccessByTimeMiddleware: 
    def __init__(self, get_response):
        self.get_response = get_response
        # Define allowed time ranges (24-hour format)
        self.allowed_start_time = dt_time(18, 0)  # 6:00 PM
        self.allowed_end_time = dt_time(21, 0)    # 9:00 PM

    def __call__(self, request):
        # Check time restriction before processing request
        current_time = datetime.now().time()
        logger.info(f"Current Server Time: {current_time.strftime('%H:%M:%S')}")
        
        # Allow access only between 18:00 and 21:00
        if not (self.allowed_start_time <= current_time <= self.allowed_end_time):
            return JsonResponse(
                {'error': 'Access restricted outside allowed hours (18:00-21:00)'}, 
                status=403
            )
        
        response = self.get_response(request)
        return response

class OffensiveLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = 5  # requests per minute
        self.time_window = 60  # seconds

    def __call__(self, request):
        client_ip = get_client_ip(request)  # Using global function
        cache_key = f"rate_limit:{client_ip}"
        
        # Get current request count
        current_requests = cache.get(cache_key, [])
        now = time.time()
        
        # Filter requests within time window
        current_requests = [
            req_time for req_time in current_requests 
            if now - req_time < self.time_window
        ]
        
        # Check rate limit
        if len(current_requests) >= self.rate_limit:
            return JsonResponse(
                {'error': 'Rate limit exceeded'}, 
                status=429
            )
        
        # Add current request
        current_requests.append(now)
        cache.set(cache_key, current_requests, self.time_window)
        
        response = self.get_response(request)
        return response

class RolepermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_roles = ['admin', 'moderator']

    def __call__(self, request):
        # Check permissions before processing request
        if hasattr(request.user, 'role'):
            user_role = getattr(request.user, 'role', None)
            
            # Check if user has required role
            if user_role not in self.allowed_roles:
                return JsonResponse(
                    {'error': 'Insufficient permissions'}, 
                    status=403
                )
        else:
            # Handle case where user doesn't have role attribute
            return JsonResponse(
                {'error': 'User role not defined'}, 
                status=403
            )
        
        response = self.get_response(request)
        return response
