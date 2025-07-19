from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Exists, OuterRef
from django.utils import timezone
from datetime import timedelta

from .models import User, Conversation, ConversationParticipant, Message, MessageReadReceipt
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer, MessageReadReceiptCreateSerializer,
    BulkMessageReadSerializer, ConversationStatsSerializer
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    """
    permission_classes = [IsAuthenticated]
    
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


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages
    """
    permission_classes = [IsAuthenticated]
    
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
        
        # Only sender can edit their message
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update edited_at timestamp
        message.edited_at = timezone.now()
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a message (only sender can delete)"""
        message = self.get_object()
        
        # Only sender can delete their message
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    
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
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(unread_messages, many=True)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """List messages with optional conversation filtering"""
        queryset = self.get_queryset()
        
        # Filter by conversation if provided
        conversation_id = request.query_params.get('conversation', None)
        if conversation_id:
            queryset = queryset.filter(conversation__conversation_id=conversation_id)
        
        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)