import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message, GlobalChatMessage, Call
from .serializers import MessageSerializer, GlobalChatMessageSerializer, CallSerializer
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
            await self.close(code=4001)
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
        if self.user.is_authenticated:
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


class CallConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling audio/video calls with WebRTC signaling
    """
    
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f'call_{self.conversation_id}'
        self.user = self.scope['user']
        self.user_call_group = f'user_call_{self.user.id}'  # Personal group for receiving calls
        self.is_global = self.conversation_id == 'global'  # Check if this is a global listener

        print(f"[CALL] Connection attempt from user: {self.user}, authenticated: {self.user.is_authenticated}, global: {self.is_global}")

        # Check if user is authenticated
        if not self.user.is_authenticated:
            print(f"[CALL] Connection rejected: User not authenticated")
            await self.close()
            return

        # For global connections, skip conversation participant check
        if not self.is_global:
            # Check if user is participant in the conversation
            is_participant = await self.check_participant()
            if not is_participant:
                print(f"[CALL] Connection rejected: User {self.user.profile_name} is not a participant")
                await self.close()
                return

        print(f"[CALL] User {self.user.profile_name} joining call group: {self.conversation_group_name if not self.is_global else 'global listener'}")

        # Join conversation call group (only if not global)
        if not self.is_global:
            await self.channel_layer.group_add(
                self.conversation_group_name,
                self.channel_name
            )
        
        # Always join user's personal call group for receiving calls
        await self.channel_layer.group_add(
            self.user_call_group,
            self.channel_name
        )

        await self.accept()

        print(f"[CALL] Connection accepted for user {self.user.profile_name}")

        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to call signaling server'
        }))

    async def disconnect(self, close_code):
        # Leave conversation call group (only if not global)
        if not self.is_global:
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
        
        # Leave user's personal call group
        if hasattr(self, 'user_call_group'):
            await self.channel_layer.group_discard(
                self.user_call_group,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Handle WebRTC signaling messages and call events
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            print(f"[CALL] Received from {self.user.profile_name}: {message_type}")

            if message_type == 'call_initiate':
                # Initiate a new call
                await self.handle_call_initiate(data)

            elif message_type == 'call_accept':
                # Accept an incoming call
                await self.handle_call_accept(data)

            elif message_type == 'call_reject':
                # Reject an incoming call
                await self.handle_call_reject(data)

            elif message_type == 'call_end':
                # End an active call
                await self.handle_call_end(data)

            elif message_type == 'webrtc_offer':
                # Forward WebRTC offer to the other peer
                await self.handle_webrtc_signal(data, 'webrtc_offer')

            elif message_type == 'webrtc_answer':
                # Forward WebRTC answer to the other peer
                await self.handle_webrtc_signal(data, 'webrtc_answer')

            elif message_type == 'webrtc_ice_candidate':
                # Forward ICE candidate to the other peer
                await self.handle_webrtc_signal(data, 'webrtc_ice_candidate')

            elif message_type == 'ping':
                # Respond to keepalive ping
                await self.send(text_data=json.dumps({'type': 'pong'}))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            print(f"[CALL] Error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_call_initiate(self, data):
        """Handle call initiation"""
        call_type = data.get('call_type', 'audio')  # 'audio' or 'video'
        receiver_id = data.get('receiver_id')
        
        if not receiver_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Receiver ID is required'
            }))
            return
        
        # Create call record in database
        call = await self.create_call(receiver_id, call_type)
        
        if call:
            call_data = await self.serialize_call(call)
            
            # Notify the receiver about the incoming call
            await self.channel_layer.group_send(
                f'user_call_{receiver_id}',
                {
                    'type': 'incoming_call',
                    'call_data': call_data,
                }
            )
            
            # Confirm to caller that call is initiated
            await self.send(text_data=json.dumps({
                'type': 'call_initiated',
                'call_data': call_data,
            }))
            
            print(f"[CALL] Call initiated: {call.id}")
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to create call'
            }))

    async def handle_call_accept(self, data):
        """Handle call acceptance"""
        call_id = data.get('call_id')
        
        if not call_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Call ID is required'
            }))
            return
        
        # Update call status to accepted
        call = await self.accept_call(call_id)
        
        if call:
            call_data = await self.serialize_call(call)
            
            # Notify the caller that call was accepted
            await self.channel_layer.group_send(
                f'user_call_{call.caller.id}',
                {
                    'type': 'call_accepted',
                    'call_data': call_data,
                }
            )
            
            print(f"[CALL] Call accepted: {call_id}")
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to accept call'
            }))

    async def handle_call_reject(self, data):
        """Handle call rejection"""
        call_id = data.get('call_id')
        
        if not call_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Call ID is required'
            }))
            return
        
        # Update call status to rejected
        call = await self.reject_call(call_id)
        
        if call:
            call_data = await self.serialize_call(call)
            
            # Notify the caller that call was rejected
            await self.channel_layer.group_send(
                f'user_call_{call.caller.id}',
                {
                    'type': 'call_rejected',
                    'call_data': call_data,
                }
            )
            
            print(f"[CALL] Call rejected: {call_id}")

    async def handle_call_end(self, data):
        """Handle call end"""
        call_id = data.get('call_id')
        
        if not call_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Call ID is required'
            }))
            return
        
        # Update call status to ended
        call = await self.end_call(call_id)
        
        if call:
            call_data = await self.serialize_call(call)
            
            # Notify both parties that call has ended
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'call_ended',
                    'call_data': call_data,
                }
            )
            
            print(f"[CALL] Call ended: {call_id}")

    async def handle_webrtc_signal(self, data, signal_type):
        """Forward WebRTC signaling messages to the other peer"""
        target_user_id = data.get('target_user_id')
        signal_data = data.get('signal_data')
        
        if not target_user_id or not signal_data:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Target user ID and signal data are required'
            }))
            return
        
        # Forward the signal to the target user
        await self.channel_layer.group_send(
            f'user_call_{target_user_id}',
            {
                'type': signal_type,
                'signal_data': signal_data,
                'from_user_id': str(self.user.id),
            }
        )
        
        print(f"[CALL] {signal_type} forwarded to user {target_user_id}")

    # Event handlers for channel layer messages
    async def incoming_call(self, event):
        """Send incoming call notification to client"""
        call_data = event['call_data']
        conversation_id = call_data.get('conversation')
        
        print(f"[CALL] Sending incoming_call notification")
        print(f"[CALL] conversation_id: {conversation_id}")
        print(f"[CALL] call_data keys: {call_data.keys()}")
        
        await self.send(text_data=json.dumps({
            'type': 'incoming_call',
            'call_data': call_data,
            'conversation_id': conversation_id,
            'caller_id': call_data.get('caller', {}).get('id') if isinstance(call_data.get('caller'), dict) else call_data.get('caller'),
            'caller_name': call_data.get('caller', {}).get('profile_name', 'Unknown') if isinstance(call_data.get('caller'), dict) else 'Unknown',
            'call_type': call_data.get('call_type'),
        }))

    async def call_accepted(self, event):
        """Send call accepted notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'call_accepted',
            'call_data': event['call_data'],
        }))

    async def call_rejected(self, event):
        """Send call rejected notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'call_rejected',
            'call_data': event['call_data'],
        }))

    async def call_ended(self, event):
        """Send call ended notification to client"""
        await self.send(text_data=json.dumps({
            'type': 'call_ended',
            'call_data': event['call_data'],
        }))

    async def webrtc_offer(self, event):
        """Forward WebRTC offer to client"""
        await self.send(text_data=json.dumps({
            'type': 'webrtc_offer',
            'signal_data': event['signal_data'],
            'from_user_id': event['from_user_id'],
        }))

    async def webrtc_answer(self, event):
        """Forward WebRTC answer to client"""
        await self.send(text_data=json.dumps({
            'type': 'webrtc_answer',
            'signal_data': event['signal_data'],
            'from_user_id': event['from_user_id'],
        }))

    async def webrtc_ice_candidate(self, event):
        """Forward ICE candidate to client"""
        await self.send(text_data=json.dumps({
            'type': 'webrtc_ice_candidate',
            'signal_data': event['signal_data'],
            'from_user_id': event['from_user_id'],
        }))

    # Database operations
    @database_sync_to_async
    def check_participant(self):
        """Check if user is a participant in the conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def create_call(self, receiver_id, call_type):
        """Create a new call record"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            receiver = User.objects.get(id=receiver_id)
            
            call = Call.objects.create(
                conversation=conversation,
                caller=self.user,
                receiver=receiver,
                call_type=call_type,
                status='ringing'
            )
            return call
        except Exception as e:
            print(f"[CALL] Error creating call: {e}")
            return None

    @database_sync_to_async
    def accept_call(self, call_id):
        """Mark call as accepted"""
        try:
            call = Call.objects.get(id=call_id)
            call.mark_accepted()
            return call
        except Call.DoesNotExist:
            return None

    @database_sync_to_async
    def reject_call(self, call_id):
        """Mark call as rejected"""
        try:
            call = Call.objects.get(id=call_id)
            call.mark_rejected()
            return call
        except Call.DoesNotExist:
            return None

    @database_sync_to_async
    def end_call(self, call_id):
        """Mark call as ended"""
        try:
            call = Call.objects.get(id=call_id)
            call.mark_ended()
            return call
        except Call.DoesNotExist:
            return None

    @database_sync_to_async
    def serialize_call(self, call):
        """Serialize call object"""
        serializer = CallSerializer(call, context={})
        return convert_uuids_to_strings(serializer.data)
