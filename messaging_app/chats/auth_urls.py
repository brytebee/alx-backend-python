# chats/auth_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .auth_views import (
    CustomTokenObtainPairView,
    RegisterView,
    UserProfileView,
    ChangePasswordView,
    LogoutView,
    UserManagementViewSet,
    AdminDashboardView,
    user_permissions,
    AdminOnlyView,
    HostOrAdminView
)

# Create router for user management viewset
auth_router = DefaultRouter()
auth_router.register(r'users', UserManagementViewSet, basename='user-management')

# Authentication URLs
auth_urlpatterns = [
    # Token authentication
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # User profile management
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # User permissions
    path('permissions/', user_permissions, name='user_permissions'),
    
    # Admin dashboard
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Role-based example views
    path('admin-only/', AdminOnlyView.as_view(), name='admin_only'),
    path('host-admin/', HostOrAdminView.as_view(), name='host_admin'),
    
    # User management routes (admin/host only)
    path('', include(auth_router.urls)),
]
