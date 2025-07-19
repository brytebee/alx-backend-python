"""
URL configuration for messaging_app project.
"""
# messaging_app/urls.py (root URLs)
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import JsonResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API authentication (for DRF browsable API)
    path('api-auth/', include('rest_framework.urls')),
    
    # API v1 routes
    path('api/v1/', include('chats.urls')),
    
    # Future API versions
    # path('api/v2/', include('chats.v2_urls')),
    
    # Frontend routes
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Health check endpoint
    path('health/', lambda request: JsonResponse({'status': 'healthy'}), name='health_check'),
]