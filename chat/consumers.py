import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message, GlobalChatMessage
from .serializers import MessageSerializer, GlobalChatMessageSerializer
from django.utils import timezone

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for private one-on-one chat
    """
    
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        # Check if user is participant in the conversation
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )

        await self.accept()

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

    async def receive(self, text_data):
        """
        Receive message from WebSocket
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')

            if message_type == 'chat_message':
                content = data.get('content', '')
                
                # Save message to database
                message = await self.save_message(content)
                
                if message:
                    # Serialize message
                    message_data = await self.serialize_message(message)
                    
                    # Send message to conversation group
                    await self.channel_layer.group_send(
                        self.conversation_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_data
                        }
                    )

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
        Send message to WebSocket
        """
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))

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

    @database_sync_to_async
    def check_participant(self):
        """Check if user is a participant in the conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content
            )
            # Update conversation's last message
            conversation.last_message = message
            conversation.save()
            return message
        except Exception as e:
            print(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message object"""
        from django.http import HttpRequest
        request = HttpRequest()
        serializer = MessageSerializer(message, context={'request': request})
        return serializer.data

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

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        # Join global chat group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

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

            if message_type == 'chat_message':
                content = data.get('content', '')
                
                # Save message to database
                message = await self.save_message(content)
                
                if message:
                    # Serialize message
                    message_data = await self.serialize_message(message)
                    
                    # Send message to global chat group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_data
                        }
                    )

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
        Send message to WebSocket
        """
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))

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
        from django.http import HttpRequest
        request = HttpRequest()
        serializer = GlobalChatMessageSerializer(message, context={'request': request})
        return serializer.data
