import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import EmailValidator
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for UUID-based User model"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with UUID primary key"""
    
    ROLE_CHOICES = [
        ('guest', 'Guest'),
        ('host', 'Host'),
        ('admin', 'Admin'),
    ]
    
    user_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        db_index=True
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='guest'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    # Required for Django admin
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'user'
        indexes = [
            models.Index(fields=['email']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['email'], name='unique_user_email'),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Conversation(models.Model):
    """Conversation model to group messages between participants"""
    
    conversation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True
    )
    participants = models.ManyToManyField(
        User,
        related_name='conversations',
        through='ConversationParticipant'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'conversation'
        ordering = ['-created_at']
    
    def __str__(self):
        participant_names = ', '.join([p.full_name for p in self.participants.all()[:3]])
        if self.participants.count() > 3:
            participant_names += f' and {self.participants.count() - 3} more'
        return f"Conversation: {participant_names}"


class ConversationParticipant(models.Model):
    """Through model for Conversation participants with additional metadata"""
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'conversation_participant'
        unique_together = ['conversation', 'user']
        indexes = [
            models.Index(fields=['conversation', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} in {self.conversation}"


class Message(models.Model):
    """Message model for storing individual messages"""
    
    message_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Additional fields that are often useful in messaging systems
    is_read = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'message'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['conversation']),
            models.Index(fields=['sent_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(message_body__isnull=False) & ~models.Q(message_body=''),
                name='message_body_not_empty'
            ),
        ]
    
    def __str__(self):
        preview = self.message_body[:50] + '...' if len(self.message_body) > 50 else self.message_body
        return f"Message from {self.sender.full_name}: {preview}"
    
    def save(self, *args, **kwargs):
        # Ensure the sender is a participant in the conversation
        if self.conversation and self.sender:
            if not self.conversation.participants.filter(user_id=self.sender.user_id).exists():
                raise ValueError("Sender must be a participant in the conversation")
        super().save(*args, **kwargs)


# Additional model for read receipts (optional enhancement)
class MessageReadReceipt(models.Model):
    """Track when messages are read by each participant"""
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_receipts')
    read_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'message_read_receipt'
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} read message {self.message.message_id} at {self.read_at}"