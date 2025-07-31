from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import User, Notification, Message, MessageHistory

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
