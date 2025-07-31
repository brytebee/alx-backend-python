from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Notification, Message

@receiver(post_save, sender=Message)
def create_notification(sender, instance, created, **kwargs):
  """Create a notification when a message is created"""
  if created:
    Notification.objects.create(sender=User, receiver=User)