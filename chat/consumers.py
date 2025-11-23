import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message, GlobalChatMessage
from .serializers import MessageSerializer, GlobalChatMessageSerializer
from django.utils import timezone

User = get_user_model()


def convert_uuids_to_strings(data):
    """
    Recursively convert all UUID objects to strings in a dictionary or list
    """
    if isinstance(data, dict):
        return {key: convert_uuids_to_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_uuids_to_strings(item) for item in data]
    elif isinstance(data, uuid.UUID):
        return str(data)
    else:
        return data


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for private one-on-one chat
    """
    
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']
        self.user_group_name = f'user_{self.user.id}'  # Personal group for this user

        print(f"[PRIVATE CHAT] Connection attempt from user: {self.user}, authenticated: {self.user.is_authenticated}")

        # Check if user is authenticated
        if not self.user.is_authenticated:
            print(f"[PRIVATE CHAT] Connection rejected: User not authenticated")
            await self.close()
            return

        # Check if user is participant in the conversation
        is_participant = await self.check_participant()
        if not is_participant:
            print(f"[PRIVATE CHAT] Connection rejected: User {self.user.profile_name} is not a participant in conversation {self.conversation_id}")
            await self.close()
            return

        print(f"[PRIVATE CHAT] User {self.user.profile_name} joining group: {self.conversation_group_name}")

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )
        
        # Join user's personal group for conversation list updates
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        print(f"[PRIVATE CHAT] Connection accepted for user {self.user.profile_name}")

        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat'
        }))

    async def disconnect(self, close_code):
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )
        
        # Leave user's personal group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')
            
            print(f"[PRIVATE CHAT] Received from {self.user.profile_name}: {data}")

            if message_type == 'chat_message':
                content = data.get('content', '')
                
                if not content:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Message content is required'
                    }))
                    return
                
                # Save message to database
                message = await self.save_message(content)
                
                if message:
                    # Serialize message
                    message_data = await self.serialize_message(message)
                    
                    print(f"[PRIVATE CHAT] Broadcasting message: {message_data.get('id')}")
                    
                    # Send message to conversation group
                    await self.channel_layer.group_send(
                        self.conversation_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_data
                        }
                    )
                    
                    # Notify all participants about conversation update
                    await self.notify_conversation_update(message_data)
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Failed to save message'
                    }))

            elif message_type == 'mark_read':
                message_id = data.get('message_id')
                if message_id:
                    await self.mark_message_read(message_id)
                    
                    # Notify other users
                    await self.channel_layer.group_send(
                        self.conversation_group_name,
                        {
                            'type': 'message_read',
                            'message_id': message_id,
                            'user_id': str(self.user.id)
                        }
                    )

            elif message_type == 'typing':
                is_typing = data.get('is_typing', False)
                
                # Notify other users about typing status
                await self.channel_layer.group_send(
                    self.conversation_group_name,
                    {
                        'type': 'typing_indicator',
                        'user_id': str(self.user.id),
                        'is_typing': is_typing
                    }
                )

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def chat_message(self, event):
        """
        Send message to WebSocket - flatten the structure
        """
        message = event['message']
        
        print(f"[PRIVATE CHAT] Sending message to client: {message.get('id')} from {message.get('sender', {}).get('profile_name')}")
        
        # Message data is already serialized and UUIDs converted to strings
        message_data = {
            'type': 'chat_message',
            'id': message.get('id'),
            'content': message.get('content'),
            'sender': message.get('sender'),
            'file_url': message.get('file_url'),
            'file_type': message.get('file_type'),
            'created_at': message.get('created_at'),
            'is_read': message.get('is_read', False),
        }
        
        # Send the message data
        await self.send(text_data=json.dumps(message_data))
        
        print(f"[PRIVATE CHAT] Message sent to client successfully")

    async def message_read(self, event):
        """
        Send message read notification
        """
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))

    async def typing_indicator(self, event):
        """
        Send typing indicator to WebSocket
        """
        # Don't send typing indicator to the user who is typing
        if str(self.user.id) != event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'is_typing': event['is_typing']
            }))

    async def conversation_update(self, event):
        """
        Send conversation list update notification
        """
        await self.send(text_data=json.dumps({
            'type': 'conversation_update',
            'conversation_id': event['conversation_id'],
            'last_message': event['last_message'],
            'timestamp': event['timestamp'],
            'sender_id': event['sender_id'],
        }))

    async def notify_conversation_update(self, message_data):
        """
        Notify all participants about conversation update for their conversation list
        """
        participants = await self.get_conversation_participants()
        
        for participant_id in participants:
            # Send update to each participant's personal group
            await self.channel_layer.group_send(
                f'user_{participant_id}',
                {
                    'type': 'conversation_update',
                    'conversation_id': str(self.conversation_id),
                    'last_message': message_data.get('content', ''),
                    'timestamp': message_data.get('created_at'),
                    'sender_id': str(self.user.id),
                }
            )

    @database_sync_to_async
    def get_conversation_participants(self):
        """Get all participant IDs in the conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return list(conversation.participants.values_list('id', flat=True))
        except Conversation.DoesNotExist:
            return []

    @database_sync_to_async
    def check_participant(self):
        """Check if user is a participant in the conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            is_participant = conversation.participants.filter(id=self.user.id).exists()
            all_participants = list(conversation.participants.values_list('id', 'profile_name'))
            print(f"[PRIVATE CHAT] Conversation {self.conversation_id} participants: {all_participants}")
            print(f"[PRIVATE CHAT] User {self.user.profile_name} (ID: {self.user.id}) is participant: {is_participant}")
            return is_participant
        except Conversation.DoesNotExist:
            print(f"[PRIVATE CHAT] Conversation {self.conversation_id} does not exist")
            return False
        except Exception as e:
            print(f"[PRIVATE CHAT] Error checking participant: {e}")
            return False

    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            print(f"[PRIVATE CHAT] Saving message from {self.user.profile_name} to conversation {self.conversation_id}")
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content
            )
            # Update conversation's last message
            conversation.last_message = message
            conversation.save()
            print(f"[PRIVATE CHAT] Message saved with ID: {message.id}")
            return message
        except Exception as e:
            print(f"[PRIVATE CHAT] Error saving message: {e}")
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message object"""
        # Don't pass request context to avoid SERVER_NAME errors in WebSocket
        serializer = MessageSerializer(message, context={})
        # Convert all UUIDs to strings to make it JSON serializable
        return convert_uuids_to_strings(serializer.data)

    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark message as read"""
        try:
            message = Message.objects.get(id=message_id)
            if message.sender != self.user:
                message.mark_as_read()
        except Message.DoesNotExist:
            pass


class GlobalChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for global chat room
    """
    
    async def connect(self):
        self.room_group_name = 'global_chat'
        self.user = self.scope['user']

        print(f"[GLOBAL CHAT] Connection attempt from user: {self.user}, authenticated: {self.user.is_authenticated}")

        # Check if user is authenticated
        if not self.user.is_authenticated:
            print(f"[GLOBAL CHAT] Connection rejected: User not authenticated")
            await self.close()
            return

        print(f"[GLOBAL CHAT] User {self.user.profile_name} (ID: {self.user.id}) joining global chat")

        # Join global chat group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        print(f"[GLOBAL CHAT] Connection accepted for user {self.user.profile_name}")

        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to global chat'
        }))

        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'username': self.user.profile_name
            }
        )

    async def disconnect(self, close_code):
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': str(self.user.id),
                'username': self.user.profile_name
            }
        )

        # Leave global chat group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')
            
            print(f"[GLOBAL CHAT] Received from {self.user.profile_name} (ID: {self.user.id}): {data}")

            if message_type == 'chat_message':
                content = data.get('content', '')
                
                if not content:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Message content is required'
                    }))
                    return
                
                # Save message to database
                message = await self.save_message(content)
                
                if message:
                    # Serialize message
                    message_data = await self.serialize_message(message)
                    
                    print(f"[GLOBAL CHAT] Broadcasting message: {message_data.get('id')} from {self.user.profile_name}")
                    
                    # Send message to global chat group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_data
                        }
                    )
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Failed to save message'
                    }))

            elif message_type == 'typing':
                is_typing = data.get('is_typing', False)
                
                # Notify other users about typing status
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'user_id': str(self.user.id),
                        'username': self.user.profile_name,
                        'is_typing': is_typing
                    }
                )

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def chat_message(self, event):
        """
        Send message to WebSocket - flatten the structure
        """
        message = event['message']
        
        # Message data is already serialized and UUIDs converted to strings
        message_data = {
            'type': 'chat_message',
            'id': message.get('id'),
            'content': message.get('content'),
            'sender': message.get('sender'),
            'file_url': message.get('file_url'),
            'file_type': message.get('file_type'),
            'created_at': message.get('created_at'),
        }
        
        # Send the message data
        await self.send(text_data=json.dumps(message_data))

    async def user_joined(self, event):
        """
        Send user joined notification
        """
        # Don't send notification to the user who joined
        if str(self.user.id) != event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username']
            }))

    async def user_left(self, event):
        """
        Send user left notification
        """
        # Don't send notification to the user who left
        if str(self.user.id) != event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username']
            }))

    async def typing_indicator(self, event):
        """
        Send typing indicator to WebSocket
        """
        # Don't send typing indicator to the user who is typing
        if str(self.user.id) != event['user_id']:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        try:
            message = GlobalChatMessage.objects.create(
                sender=self.user,
                content=content
            )
            return message
        except Exception as e:
            print(f"Error saving global message: {e}")
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message object"""
        # Don't pass request context to avoid SERVER_NAME errors in WebSocket
        serializer = GlobalChatMessageSerializer(message, context={})
        # Convert all UUIDs to strings to make it JSON serializable
        return convert_uuids_to_strings(serializer.data)
