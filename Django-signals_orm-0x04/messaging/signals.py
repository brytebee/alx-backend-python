from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import User, Notification, Message, MessageHistory, ConversationParticipant, MessageReadReceipt, Conversation

@receiver(post_save, sender=Message)
def create_notification(sender, instance, created, **kwargs):
  """Create a notification when a message is created"""

  if created:
    Notification.objects.create(sender=User, receiver=User)

@receiver(pre_save, sender=Message, dispatch_uid="message_edit_log")
def create_message_history(sender, instance, created, **kwargs):
  """Log current message when edit is triggered"""

  action = "created" if created else instance.edited
  MessageHistory.objects.create(
    model_name="MessageHistory",
    object_id=instance.pk,
    action=action,
    current_message=f"{instance.content}",
    edited_by=User
  )

@receiver(post_delete, sender=User)
def clean_user_resources(sender, instance, **kwargs):
    """Delete all resources associated with user when account is destroyed"""

    models_and_fields = [
        (Message, ['sender', 'receiver']),
        (Notification, ['sender', 'receiver']),
        (Conversation, ['participant']),
        (ConversationParticipant, ['user']),
        (MessageReadReceipt, ['user']),
        (MessageHistory, ['edited_by']),
    ]
    
    for model, fields in models_and_fields:
        try:
            for field in fields:
                # Check if the field exists on the model before filtering
                if hasattr(model, field):
                    deleted_count, _ = model.objects.filter(**{field: instance}).delete()
                    if deleted_count > 0:
                        print(f"Deleted {deleted_count} {model._meta.verbose_name_plural} for {instance.first_name}")
        except Exception as e:
            print(f"{model._meta.verbose_name_plural} associated with {instance.first_name} could not be destroyed: {e}")
    
    # Handle conversations separately due to M2M relationship
    try:
        conversations_to_delete = []
        for conversation in instance.conversations.all():
            if conversation.participants.count() <= 1:  # Only this user left
                conversations_to_delete.append(conversation)
        
        for conversation in conversations_to_delete:
            conversation.delete()
            
        if conversations_to_delete:
            print(f"Deleted {len(conversations_to_delete)} empty conversations for {instance.first_name}")
            
    except Exception as e:
        print(f"Conversations associated with {instance.first_name} could not be cleaned up: {e}")

