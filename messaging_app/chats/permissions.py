# chats/permissions.py
from rest_framework import permissions

BasePermission = permissions.BasePermission

class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an 'owner' or 'user' attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Instance must have an attribute named `owner` or similar.
        return getattr(obj, 'owner', getattr(obj, 'user', None)) == request.user


class IsMessageSender(BasePermission):
    """
    Permission to only allow message senders to edit/delete their messages.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions for authenticated users
        if request.method in ['GET', 'PUT', 'PATCH', 'HEAD', 'OPTIONS']:
            return True

        # Write permissions only to the sender of the message
        return obj.sender == request.user


class IsConversationParticipant(BasePermission):
    """
    Permission to only allow conversation participants to access conversation data.
    """

    def has_object_permission(self, request, view, obj):
        # Check if user is a participant in the conversation
        return obj.participants.filter(user_id=request.user.user_id).exists()


class IsAdminOrHost(BasePermission):
    """
    Permission to only allow admin or host users.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'host']
        )


class IsAdmin(BasePermission):
    """
    Permission to only allow admin users.
    """

    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class CanManageUsers(BasePermission):
    """
    Permission for user management - only admins can manage users.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin can do everything
        if request.user.role == 'admin':
            return True

        # Host can only read user data
        if request.user.role == 'host' and request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        # Users can always access their own data
        if obj == request.user:
            return True

        # Admin can access any user
        if request.user.role == 'admin':
            return True

        # Host can only read other user data
        if request.user.role == 'host' and request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        return False
