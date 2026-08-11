# chat/consumers.py
import json
import logging
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def history_cleared(self, event):
        await self.send(text_data=json.dumps({
            'type': 'history_cleared'
        }))

    async def typing_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_start',
            'user_id': event['user_id'],
            'display_name': event['display_name']
        }))

    async def typing_stop(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_stop',
            'user_id': event['user_id']
        }))

    async def reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'action': event.get('action', 'added'),
            'emoji': event['emoji'],
            'message_id': event.get('message_id'),
            'user_id': event['user_id'],
            'display_name': event['display_name']
        }))
    # Diccionario de usuarios conectados por sala (en memoria, por proceso)
    connected_users = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_name = None
        self.room_group_name = None
        self.user = None

    async def connect(self):
        try:
            # Get room name and validate
            self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
            logger.info(f"WebSocket connection attempt for room: {self.room_name}")

            # Validate room name more thoroughly
            if not self.room_name or not str(self.room_name).strip():
                logger.error(f"Empty room name received")
                raise ValueError("Room name cannot be empty")

            if not str(self.room_name).isalnum():
                logger.error(f"Invalid room name format: {self.room_name}")
                raise ValueError("Invalid room name format")

            self.room_group_name = f"chat_{self.room_name}"
            self.user = self.scope["user"]

            # Authentication check
            if isinstance(self.user, AnonymousUser):
                logger.warning("Anonymous user attempted to connect")
                raise PermissionDenied("Authentication required")

            # Verify room access (implement your own logic)
            if not await self.verify_room_access():
                logger.warning(f"User {self.user} denied access to room {self.room_name}")
                raise PermissionDenied("No access to this room")

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # Añadir usuario a la lista de conectados
            await self.add_connected_user()

            await self.accept()
            logger.info(f"User {self.user} successfully connected to room {self.room_name}")

            # Notificar a todos los usuarios la lista actualizada
            await self.broadcast_connected_users()

        except PermissionDenied as e:
            logger.warning(f"Connection refused: {str(e)}")
            await self.close(code=4001)  # Custom close code for permission denied
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            await self.close(code=4002)  # Custom close code for validation errors
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await self.close(code=4000)  # Custom close code for other errors

    async def disconnect(self, close_code):
        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            await self.remove_connected_user()
            await self.broadcast_connected_users()
        except:
            pass
        raise StopConsumer()
    @database_sync_to_async
    def get_user_info(self):
        return {
            'id': str(self.user.id),
            'username': self.user.username,
            'display_name': f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        }

    async def add_connected_user(self):
        room = self.room_group_name
        if room not in self.connected_users:
            self.connected_users[room] = set()
        self.connected_users[room].add((str(self.user.id), self.user.username, f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username))

    async def remove_connected_user(self):
        room = self.room_group_name
        if room in self.connected_users:
            self.connected_users[room] = set(u for u in self.connected_users[room] if u[0] != str(self.user.id))
            if not self.connected_users[room]:
                del self.connected_users[room]

    async def broadcast_connected_users(self):
        room = self.room_group_name
        users = []
        if room in self.connected_users:
            for user_id, username, display_name in self.connected_users[room]:
                users.append({'id': user_id, 'username': username, 'display_name': display_name})
        await self.channel_layer.group_send(
            room,
            {
                'type': 'users_list',
                'users': users
            }
        )

    async def users_list(self, event):
        await self.send(text_data=json.dumps({
            'type': 'users',
            'users': event['users']
        }))

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                text_data_json = json.loads(text_data)
                event_type = text_data_json.get("type", "message")

                if event_type == "typing_start":
                    user_full_name = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "typing_start",
                            "user_id": str(self.user.id),
                            "display_name": user_full_name
                        }
                    )
                elif event_type == "typing_stop":
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "typing_stop",
                            "user_id": str(self.user.id)
                        }
                    )
                elif event_type == "reaction":
                    emoji = text_data_json.get("emoji")
                    message_id = text_data_json.get("message_id")
                    action, emoji_result, message_id_result = await self.handle_reaction(emoji, message_id)

                    if action:
                        user_full_name = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "reaction",
                                "action": action,
                                "emoji": emoji_result,
                                "message_id": message_id_result,
                                "user_id": str(self.user.id),
                                "display_name": user_full_name
                            }
                        )
                elif event_type == "message":
                    message = text_data_json.get("message", "").strip()

                    if not message:
                        raise ValueError("Empty message")

                    # Validate and process message
                    processed_message = await self.process_message(message)
                    user_full_name = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

                    # Guardar mensaje en la base de datos
                    message_obj = await self.save_message(self.room_name, self.user, processed_message)

                    # Create notifications for other room members using hardcoded system
                    logger.info(f"Creating notifications for message in room {self.room_name} from user {self.user.username}")
                    await self.create_room_notifications_hardcoded(processed_message, self.user, self.room_name)

                    # Note: We don't automatically mark messages as read for the sender
                    # Read receipts should only happen when the user actually views the message

                    # Send message to room group
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "chat_message",
                            "message": processed_message,
                            "sender": str(self.user),
                            "user_id": str(self.user.id),
                            "display_name": user_full_name
                        }
                    )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "error": "Invalid JSON format"
            }))
        except ValueError as e:
            await self.send(text_data=json.dumps({
                "error": str(e)
            }))
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send(text_data=json.dumps({
                "error": "Internal server error"
            }))

    @database_sync_to_async
    def save_message(self, room_id, user, content):
        from rooms.models import Cell, Message
        try:
            room = Cell.objects.get(id=room_id, cell_type='ROOM')
            message = Message.objects.create(room=room, user=user, content=content)
            return message
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None

    @database_sync_to_async
    def mark_message_read_for_sender(self, message, user):
        from rooms.models import MessageRead
        if message:
            try:
                MessageRead.objects.get_or_create(user=user, message=message)
                logger.info(f"Auto-marked message {message.id} as read for sender {user.username}")
            except Exception as e:
                logger.error(f"Error auto-marking message as read: {str(e)}")

    async def chat_message(self, event):
        try:
            # Send message to WebSocket with additional metadata
            message_data = {
                "message": event["message"],
                "sender": event["sender"],
                "user_id": event["user_id"],
                "display_name": event.get("display_name", "Usuario"),
                "timestamp": str(datetime.datetime.now().isoformat()),
                "room_id": self.room_name
            }
            await self.send(text_data=json.dumps(message_data))

            # Note: User-specific notification groups are not used
            # All notifications go through the general "notifications" group
            # which is properly filtered in NotificationConsumer

            # Create notifications for other room members
            # await self.create_room_notifications(event)  # This method doesn't exist
            # Notifications are already created in the receive method via create_room_notifications_hardcoded

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")

    @database_sync_to_async
    def create_room_notifications_hardcoded(self, message, sender, room_id):
        """Create notifications for room members using hybrid system (cache + database fallback)"""
        from .models import HardcodedNotificationManager
        from rooms.models import Cell
        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            room = Cell.objects.get(id=room_id, cell_type='ROOM')
            logger.info(f"Creating notifications for room {room.name} (ID: {room_id})")

            recipients = []
            if room.owner_id and room.owner_id != sender.id:
                try:
                    recipients.append(room.owner)
                except User.DoesNotExist:
                    pass
            if sender.is_staff:
                staff_users = User.objects.filter(is_staff=True).exclude(id=sender.id)
                recipients.extend(staff_users)

            logger.info(f"Found {len(recipients)} recipients (owner + staff, excluding sender)")

            notification_count = 0
            for recipient in recipients:
                logger.info(f"Creating notification for user {recipient.username} (ID: {recipient.id})")
                notification = HardcodedNotificationManager.create_chat_notification(
                    user=recipient,
                    room=room,
                    message=message,
                    sender=sender
                )
                if notification:
                    notification_count += 1
                    logger.info(f"Created notification for user {recipient.username}")
                else:
                    logger.error(f"Failed to create notification for user {recipient.username}")

            if notification_count > 0:
                logger.info(f"Created {notification_count} notifications for room {room.name}")
            else:
                logger.warning(f"No notifications created for room {room.name}")

        except Exception as e:
            logger.error(f"Error creating room notifications: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    @database_sync_to_async
    def verify_room_access(self):
        """Verifica si el usuario tiene acceso a la sala (owner o staff)"""
        from rooms.models import Cell
        try:
            cell = Cell.objects.get(id=self.room_name, cell_type='ROOM')
            is_owner = cell.owner_id == self.user.id
            is_staff = self.user.is_staff
            is_public = cell.permissions == 'public'
            return is_owner or is_staff or is_public
        except Cell.DoesNotExist:
            return False

    async def process_message(self, raw_message):
        """Process and sanitize incoming messages"""
        # Add any message processing logic here
        return raw_message[:500]  # Simple length limit example

    @database_sync_to_async
    def update_typing_status(self, is_typing):
        """Update user's typing status in database"""
        from .models import TypingStatus
        from rooms.models import Cell

        try:
            room = Cell.objects.get(id=self.room_name, cell_type='ROOM')
            status, created = TypingStatus.objects.get_or_create(
                user=self.user,
                room=room,
                defaults={'is_typing': is_typing}
            )
            if not created:
                status.is_typing = is_typing
                status.save()
        except Exception as e:
            logger.error(f"Error updating typing status: {str(e)}")

    @database_sync_to_async
    def handle_reaction(self, emoji, message_id):
        """Handle message reaction"""
        from .models import MessageReaction
        from rooms.models import Message

        try:
            message = Message.objects.get(id=message_id)
            # Check if reaction already exists
            reaction, created = MessageReaction.objects.get_or_create(
                message=message,
                user=self.user,
                emoji=emoji
            )

            if not created:
                # Remove reaction if it already exists
                reaction.delete()
                action = 'removed'
            else:
                action = 'added'

            return action, emoji, message_id
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} not found for reaction")
            return None, None, None
        except Exception as e:
            logger.error(f"Error handling reaction: {str(e)}")
            return None, None, None