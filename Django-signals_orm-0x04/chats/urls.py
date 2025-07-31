# chats/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import ConversationViewSet, MessageViewSet
from .auth_urls import auth_urlpatterns

# Create main router
router = routers.DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')

# Create nested router for messages within conversations
conversations_router = routers.NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', MessageViewSet, basename='conversation-messages')

# Main URL patterns
urlpatterns = [
    # Authentication endpoints
    path('auth/', include(auth_urlpatterns)),
    
    # Main API endpoints
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),
    
    # DRF Auth (for browsable API)
    path('api-auth/', include('rest_framework.urls')),
]
