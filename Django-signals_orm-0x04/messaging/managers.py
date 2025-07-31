from .models import Message, Conversation

class UnreadMessagesManager:
    """Manages user unread messages"""
    
    def __init__(self, user):
        self.user = user
    
    def get_unread_messages(self):
        """Get all unread messages for current user"""
        return Message.objects.filter(
            receiver=self.user,
            unread=True
        ).select_related(
            'sender', 'conversation', 'parent_message'
        ).order_by('-timestamp')
    
    def get_unread_count(self):
        """Get count of unread messages"""
        return Message.objects.filter(
            receiver=self.user,
            unread=True
        ).count()
    
    def get_unread_by_conversation(self):
        """Get unread messages grouped by conversation"""
        unread_messages = self.get_unread_messages()
        
        conversations = {}
        for message in unread_messages:
            conv_id = str(message.conversation.conversation_id)
            if conv_id not in conversations:
                conversations[conv_id] = {
                    'conversation': message.conversation,
                    'messages': [],
                    'count': 0
                }
            conversations[conv_id]['messages'].append(message)
            conversations[conv_id]['count'] += 1
        
        return conversations
    
    def mark_as_read(self, message_ids):
        """Mark specific messages as read"""
        updated_count = Message.objects.filter(
            message_id__in=message_ids,
            receiver=self.user,
            unread=True
        ).update(unread=False)
        
        return updated_count
    
    def mark_conversation_as_read(self, conversation_id):
        """Mark all messages in a conversation as read"""
        updated_count = Message.objects.filter(
            conversation_id=conversation_id,
            receiver=self.user,
            unread=True
        ).update(unread=False)
        
        return updated_count
    
    def get_unread_conversations(self):
        """Get conversations that have unread messages"""
        return Conversation.objects.filter(
            messages__receiver=self.user,
            messages__unread=True
        ).distinct().select_related().prefetch_related(
            'participants'
        )
