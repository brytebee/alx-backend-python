# chats/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils import timezone
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend

from .models import User, Conversation, ConversationParticipant, Message, MessageReadReceipt
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer, MessageReadReceiptCreateSerializer,
    BulkMessageReadSerializer, ConversationStatsSerializer
)
from .permissions import (
    IsConversationParticipant, IsMessageSender, IsAdminOrHost
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations with enhanced permissions and filters
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['conversation_type', 'created_at']
    search_fields = ['title']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    @method_decorator(cache_page(60))
    def get_queryset(self):
        """Return conversations where current user is a participant"""
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related(
            'participants',
            'messages__sender',
            'messages__read_receipts'
        ).distinct().order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'list':
            return ConversationListSerializer
        else:
            return ConversationDetailSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action in ['retrieve', 'update', 'partial_update', 'mark_all_read', 'leave']:
            # Only participants can access specific conversation
            permission_classes = [IsAuthenticated, IsConversationParticipant]
        elif self.action == 'add_participant':
            # Only admin or host can add participants to any conversation
            # Or participants can add to their own conversations
            permission_classes = [IsAuthenticated]  # Custom logic in the action
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Create a new conversation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        
        # Return detailed conversation data
        detail_serializer = ConversationDetailSerializer(
            conversation, context={'request': request}
        )
        return Response(
            detail_serializer.data, 
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def mark_all_read(self, request, pk=None):
        """Mark all messages in a conversation as read"""
        conversation = self.get_object()
        
        # Get all unread messages in this conversation for current user
        unread_messages = conversation.messages.exclude(
            read_receipts__user=request.user
        )
        
        # Create read receipts for unread messages
        receipts_to_create = []
        for message in unread_messages:
            receipts_to_create.append(
                MessageReadReceipt(message=message, user=request.user)
            )
        
        MessageReadReceipt.objects.bulk_create(receipts_to_create)
        
        return Response({
            'message': f'Marked {len(receipts_to_create)} messages as read',
            'marked_count': len(receipts_to_create)
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get conversation statistics for current user"""
        user = request.user
        
        # Get conversations where user is participant
        user_conversations = Conversation.objects.filter(participants=user)
        
        # Total conversations
        total_conversations = user_conversations.count()
        
        # Total messages in user's conversations
        total_messages = Message.objects.filter(
            conversation__in=user_conversations
        ).count()
        
        # Unread messages for current user
        unread_messages = Message.objects.filter(
            conversation__in=user_conversations
        ).exclude(read_receipts__user=user).count()
        
        # Active conversations (with messages in last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_conversations = user_conversations.filter(
            messages__sent_at__gte=thirty_days_ago
        ).distinct().count()
        
        stats_data = {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'unread_messages': unread_messages,
            'active_conversations': active_conversations
        }
        
        serializer = ConversationStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a conversation"""
        conversation = self.get_object()
        
        try:
            participant = ConversationParticipant.objects.get(
                conversation=conversation,
                user=request.user,
                left_at__isnull=True
            )
            participant.left_at = timezone.now()
            participant.save()
            
            return Response({
                'message': 'Successfully left the conversation'
            })
        except ConversationParticipant.DoesNotExist:
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a new participant to conversation"""
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permissions - admin/host can add to any conversation,
        # participants can add to their own conversations
        is_participant = conversation.participants.filter(user_id=request.user.user_id).exists()
        is_admin_or_host = request.user.role in ['admin', 'host']
        
        if not (is_participant or is_admin_or_host):
            return Response(
                {'error': 'You do not have permission to add participants to this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user_to_add = User.objects.get(user_id=user_id)
            
            # Check if user is already a participant
            if ConversationParticipant.objects.filter(
                conversation=conversation,
                user=user_to_add,
                left_at__isnull=True
            ).exists():
                return Response(
                    {'error': 'User is already a participant'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add participant
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=user_to_add
            )
            
            return Response({
                'message': f'Added {user_to_add.full_name} to the conversation'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrHost])
    def all_conversations(self, request):
        """Admin and Host can view all conversations"""
        all_conversations = Conversation.objects.all().prefetch_related(
            'participants',
            'messages__sender'
        ).order_by('-created_at')
        
        # Apply pagination
        page = self.paginate_queryset(all_conversations)
        if page is not None:
            serializer = ConversationListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ConversationListSerializer(all_conversations, many=True, context={'request': request})
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages with enhanced permissions and filters
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['conversation', 'sender', 'sent_at', 'message_type']
    search_fields = ['content']
    ordering_fields = ['sent_at', 'edited_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        """Return messages from conversations where current user is a participant"""
        user_conversations = Conversation.objects.filter(
            participants=self.request.user
        )
        
        return Message.objects.filter(
            conversation__in=user_conversations
        ).select_related(
            'sender', 'conversation'
        ).prefetch_related(
            'read_receipts__user'
        ).order_by('-sent_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return MessageCreateSerializer
        else:
            return MessageSerializer
    
    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            # Only message sender can edit/delete
            permission_classes = [IsAuthenticated, IsMessageSender]
        elif self.action == 'all_messages':
            # Only admin and host can view all messages
            permission_classes = [IsAuthenticated, IsAdminOrHost]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Send a new message"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verify user is participant in the conversation
        conversation_id = serializer.validated_data.get('conversation').conversation_id
        if not Conversation.objects.filter(
            conversation_id=conversation_id,
            participants=request.user
        ).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message = serializer.save()
        
        # Return detailed message data
        detail_serializer = MessageSerializer(
            message, context={'request': request}
        )
        return Response(
            detail_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update a message (only sender can edit)"""
        message = self.get_object()
        
        # Update edited_at timestamp
        message.edited_at = timezone.now()
        
        return super().update(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a specific message as read"""
        message = self.get_object()
        
        serializer = MessageReadReceiptCreateSerializer(
            data={'message': message.message_id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Message marked as read',
            'message_id': message.message_id
        })
    
    @action(detail=False, methods=['post'])
    def mark_multiple_read(self, request):
        """Mark multiple messages as read"""
        serializer = BulkMessageReadSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        
        return Response({
            'message': f'Marked {result["marked_as_read"]} messages as read',
            'marked_count': result['marked_as_read'],
            'message_ids': result['message_ids']
        })
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get all unread messages for current user"""
        unread_messages = self.get_queryset().exclude(
            read_receipts__user=request.user
        )
        
        # Apply pagination
        page = self.paginate_queryset(unread_messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(unread_messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrHost])
    def all_messages(self, request):
        """Admin and Host can view all messages"""
        all_messages = Message.objects.all().select_related(
            'sender', 'conversation'
        ).prefetch_related(
            'read_receipts__user'
        ).order_by('-sent_at')
        
        # Apply filtering by conversation if provided
        conversation_id = request.query_params.get('conversation_id')
        if conversation_id:
            all_messages = all_messages.filter(conversation__conversation_id=conversation_id)
        
        # Apply date filtering
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        if from_date:
            try:
                from_date_parsed = timezone.datetime.fromisoformat(from_date.replace('Z', '+00:00'))
                all_messages = all_messages.filter(sent_at__gte=from_date_parsed)
            except ValueError:
                return Response(
                    {'error': 'Invalid from_date format. Use ISO format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if to_date:
            try:
                to_date_parsed = timezone.datetime.fromisoformat(to_date.replace('Z', '+00:00'))
                all_messages = all_messages.filter(sent_at__lte=to_date_parsed)
            except ValueError:
                return Response(
                    {'error': 'Invalid to_date format. Use ISO format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Apply sender filtering
        sender_id = request.query_params.get('sender_id')
        if sender_id:
            all_messages = all_messages.filter(sender__user_id=sender_id)
        
        # Apply search filtering
        search = request.query_params.get('search')
        if search:
            all_messages = all_messages.filter(content__icontains=search)
        
        # Apply pagination
        page = self.paginate_queryset(all_messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(all_messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search messages in user's conversations"""
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {'error': 'Search query (q) parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search in user's accessible messages
        messages = self.get_queryset().filter(
            content__icontains=query
        )
        
        # Apply conversation filtering if specified
        conversation_id = request.query_params.get('conversation_id')
        if conversation_id:
            messages = messages.filter(conversation__conversation_id=conversation_id)
        
        # Apply pagination
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent messages from user's conversations"""
        # Get messages from last 7 days by default
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)
        
        recent_messages = self.get_queryset().filter(sent_at__gte=since)
        
        # Apply pagination
        page = self.paginate_queryset(recent_messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recent_messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def read_receipts(self, request, pk=None):
        """Get read receipts for a specific message"""
        message = self.get_object()
        
        # Verify user can access this message
        if not message.conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You do not have permission to view this message'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        receipts = message.read_receipts.select_related('user').all()
        
        receipt_data = []
        for receipt in receipts:
            receipt_data.append({
                'user_id': receipt.user.user_id,
                'user_name': receipt.user.full_name,
                'read_at': receipt.read_at
            })
        
        return Response({
            'message_id': message.message_id,
            'read_by': receipt_data,
            'total_reads': len(receipt_data)
        })


# Helper mixin for nested message viewset
class NestedMessageViewSet(MessageViewSet):
    """
    ViewSet for messages nested under conversations
    """
    
    def get_queryset(self):
        """Return messages from a specific conversation where user is a participant"""
        conversation_pk = self.kwargs.get('conversation_pk')
        
        # Verify user is participant in the conversation
        if not Conversation.objects.filter(
            pk=conversation_pk,
            participants=self.request.user
        ).exists():
            return Message.objects.none()
        
        return Message.objects.filter(
            conversation_id=conversation_pk
        ).select_related(
            'sender', 'conversation'
        ).prefetch_related(
            'read_receipts__user'
        ).order_by('-sent_at')
    
    def create(self, request, *args, **kwargs):
        """Send a new message in a specific conversation"""
        conversation_pk = self.kwargs.get('conversation_pk')
        
        # Verify conversation exists and user is participant
        try:
            conversation = Conversation.objects.get(pk=conversation_pk)
            if not conversation.participants.filter(user_id=request.user.user_id).exists():
                return Response(
                    {'error': 'You are not a participant in this conversation'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Add conversation to request data
        data = request.data.copy()
        data['conversation'] = conversation.conversation_id
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        # Return detailed message data
        detail_serializer = MessageSerializer(
            message, context={'request': request}
        )
        return Response(
            detail_serializer.data,
            status=status.HTTP_201_CREATED
        )
