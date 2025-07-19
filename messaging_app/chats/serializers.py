from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Conversation, ConversationParticipant, Message, MessageReadReceipt


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for public information"""
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'user_id', 'first_name', 'last_name', 'full_name', 
            'email', 'role', 'created_at'
        ]
        read_only_fields = ['user_id', 'created_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer for profile management"""
    
    full_name = serializers.ReadOnlyField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'user_id', 'first_name', 'last_name', 'full_name',
            'email', 'phone_number', 'role', 'created_at',
            'password', 'confirm_password'
        ]
        read_only_fields = ['user_id', 'created_at']
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def validate(self, attrs):
        # Validate password confirmation
        if 'password' in attrs and 'confirm_password' in attrs:
            if attrs['password'] != attrs['confirm_password']:
                raise serializers.ValidationError("Passwords don't match")
        
        # Validate password strength
        if 'password' in attrs:
            try:
                validate_password(attrs['password'])
            except ValidationError as e:
                raise serializers.ValidationError({'password': e.messages})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user
    
    def update(self, instance, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user authentication"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    user = serializers.SerializerMethodField()
    
    def get_user(self, obj):
        return UserSerializer(obj.get('user')).data
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Email and password are required')


class MessageReadReceiptSerializer(serializers.ModelSerializer):
    """Serializer for message read receipts"""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageReadReceipt
        fields = ['user', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    """Basic message serializer"""
    
    sender = UserSerializer(read_only=True)
    read_receipts = MessageReadReceiptSerializer(many=True, read_only=True)
    is_read_by_current_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'message_body', 'sent_at',
            'is_read', 'edited_at', 'read_receipts', 'is_read_by_current_user'
        ]
        read_only_fields = ['message_id', 'sent_at', 'sender']
    
    def get_is_read_by_current_user(self, obj):
        """Check if current user has read this message"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.read_receipts.filter(user=request.user).exists()
        return False
    
    def create(self, validated_data):
        # Set sender from request user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['sender'] = request.user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = ['conversation', 'message_body']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['sender'] = request.user
        return super().create(validated_data)


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer for conversation participants"""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = ['user', 'joined_at', 'left_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists"""
    
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'participants', 'created_at',
            'last_message', 'unread_count'
        ]
    
    def get_last_message(self, obj):
        """Get the most recent message in the conversation"""
        last_message = obj.messages.first()  # Already ordered by -sent_at
        if last_message:
            return {
                'message_id': last_message.message_id,
                'sender': last_message.sender.full_name,
                'message_body': last_message.message_body[:100] + '...' if len(last_message.message_body) > 100 else last_message.message_body,
                'sent_at': last_message.sent_at
            }
        return None
    
    def get_unread_count(self, obj):
        """Get count of unread messages for current user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.messages.exclude(
                read_receipts__user=request.user
            ).count()
        return 0


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed conversation serializer with all messages"""
    
    participants = UserSerializer(many=True, read_only=True)
    participant_details = ConversationParticipantSerializer(
        source='conversationparticipant_set', 
        many=True, 
        read_only=True
    )
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'participants', 'participant_details',
            'created_at', 'messages', 'message_count'
        ]
    
    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating conversations"""
    
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        help_text="List of user IDs to add as participants"
    )
    
    class Meta:
        model = Conversation
        fields = ['participant_ids']
    
    def validate_participant_ids(self, value):
        """Validate that all participant IDs exist"""
        if not value:
            raise serializers.ValidationError("At least one participant is required")
        
        # Check if all users exist
        existing_users = User.objects.filter(user_id__in=value).count()
        if existing_users != len(value):
            raise serializers.ValidationError("Some participant IDs don't exist")
        
        return value
    
    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        
        # Add current user to participants if not already included
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            current_user_id = str(request.user.user_id)
            if current_user_id not in [str(pid) for pid in participant_ids]:
                participant_ids.append(request.user.user_id)
        
        # Create conversation
        conversation = Conversation.objects.create(**validated_data)
        
        # Add participants
        participants = User.objects.filter(user_id__in=participant_ids)
        for participant in participants:
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=participant
            )
        
        return conversation
    
    def to_representation(self, instance):
        # Return detailed representation after creation
        return ConversationDetailSerializer(
            instance, 
            context=self.context
        ).data


class MessageReadReceiptCreateSerializer(serializers.ModelSerializer):
    """Serializer for marking messages as read"""
    
    class Meta:
        model = MessageReadReceipt
        fields = ['message']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        # Use get_or_create to avoid duplicates
        receipt, created = MessageReadReceipt.objects.get_or_create(
            message=validated_data['message'],
            user=validated_data['user'],
            defaults={'read_at': validated_data.get('read_at')}
        )
        return receipt


class ConversationStatsSerializer(serializers.Serializer):
    """Serializer for conversation statistics"""
    
    total_conversations = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    active_conversations = serializers.IntegerField()  # Conversations with messages in last 30 days


class BulkMessageReadSerializer(serializers.Serializer):
    """Serializer for marking multiple messages as read"""
    
    message_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of message IDs to mark as read"
    )
    
    def validate_message_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one message ID is required")
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        message_ids = validated_data['message_ids']
        
        if request and hasattr(request, 'user'):
            messages = Message.objects.filter(message_id__in=message_ids)
            receipts_to_create = []
            
            for message in messages:
                # Only create if doesn't already exist
                if not MessageReadReceipt.objects.filter(
                    message=message, 
                    user=request.user
                ).exists():
                    receipts_to_create.append(
                        MessageReadReceipt(message=message, user=request.user)
                    )
            
            # Bulk create receipts
            MessageReadReceipt.objects.bulk_create(receipts_to_create)
            
            return {
                'marked_as_read': len(receipts_to_create),
                'message_ids': message_ids
            }
        
        return {'marked_as_read': 0, 'message_ids': []}