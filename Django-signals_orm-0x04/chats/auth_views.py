# chats/auth_views.py
from rest_framework import status, generics, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from .models import User, Conversation, Message
from .serializers import (
    UserSerializer, UserDetailSerializer, UserLoginSerializer,
    ConversationListSerializer, MessageSerializer
)
from .permissions import (
    IsAdminOrHost, IsAdmin, CanManageUsers, IsOwnerOrReadOnly
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view that returns user data along with tokens
    """
    
    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })


class RegisterView(generics.CreateAPIView):
    """
    User registration endpoint
    """
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User profile view - users can view and update their own profile
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    Change password endpoint
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([old_password, new_password, confirm_password]):
            return Response(
                {'error': 'All password fields are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(old_password):
            return Response(
                {'error': 'Invalid old password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'New passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Password changed successfully'})


class LogoutView(APIView):
    """
    Logout endpoint that blacklists the refresh token
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except Exception as e:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management - Admin and Host permissions
    """
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]
    lookup_field = 'user_id'

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return UserSerializer
        return UserDetailSerializer

    def get_queryset(self):
        """
        Filter users based on role permissions
        """
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        elif user.role == 'host':
            # Host can see all users but limited actions
            return User.objects.all()
        else:
            # Guest users can only see themselves
            return User.objects.filter(user_id=user.user_id)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def change_role(self, request, user_id=None):
        """
        Admin can change user roles
        """
        user = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in ['guest', 'host', 'admin']:
            return Response(
                {'error': 'Invalid role. Must be guest, host, or admin'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.role = new_role
        user.save()
        
        return Response({
            'message': f'User role changed to {new_role}',
            'user': UserSerializer(user).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def deactivate(self, request, user_id=None):
        """
        Admin can deactivate users
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        
        return Response({'message': 'User deactivated successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def activate(self, request, user_id=None):
        """
        Admin can activate users
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response({'message': 'User activated successfully'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrHost])
    def search(self, request):
        """
        Search users by name or email
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Search query is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        users = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrHost])
    def by_role(self, request):
        """
        Get users by role
        """
        role = request.query_params.get('role', '')
        if role not in ['guest', 'host', 'admin']:
            return Response({'error': 'Invalid role parameter'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        users = self.get_queryset().filter(role=role)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class AdminDashboardView(APIView):
    """
    Admin dashboard with system statistics
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        users_by_role = {
            'admin': User.objects.filter(role='admin').count(),
            'host': User.objects.filter(role='host').count(),
            'guest': User.objects.filter(role='guest').count(),
        }

        # Conversation statistics
        total_conversations = Conversation.objects.count()
        total_messages = Message.objects.count()

        return Response({
            'user_stats': {
                'total_users': total_users,
                'active_users': active_users,
                'users_by_role': users_by_role,
            },
            'conversation_stats': {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
            }
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_permissions(request):
    """
    Get current user's permissions and role information
    """
    user = request.user
    permissions = {
        'role': user.role,
        'is_admin': user.role == 'admin',
        'is_host': user.role == 'host',
        'is_guest': user.role == 'guest',
        'can_manage_users': user.role in ['admin', 'host'],
        'can_create_conversations': True,  # All authenticated users
        'can_send_messages': True,  # All authenticated users
    }
    
    return Response(permissions)


# Middleware for role-based access (optional enhancement)
class RoleRequiredMixin:
    """
    Mixin to require specific roles for view access
    """
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if self.required_roles and request.user.role not in self.required_roles:
            return Response(
                {'error': 'Insufficient permissions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().dispatch(request, *args, **kwargs)


class AdminOnlyView(RoleRequiredMixin, APIView):
    """
    Example view that requires admin role
    """
    required_roles = ['admin']
    
    def get(self, request):
        return Response({'message': 'This is admin only content'})


class HostOrAdminView(RoleRequiredMixin, APIView):
    """
    Example view that requires host or admin role
    """
    required_roles = ['host', 'admin']
    
    def get(self, request):
        return Response({'message': 'This is host/admin only content'})
