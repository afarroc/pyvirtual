from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)


class Conversation(models.Model):
    """Modelo para guardar conversaciones completas con la IA"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation_id = models.CharField(max_length=100, unique=True, help_text="ID único de la conversación")
    title = models.CharField(max_length=200, blank=True, help_text="Título auto-generado de la conversación")
    messages = models.JSONField(default=list, help_text="Lista completa de mensajes de la conversación")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Si la conversación está activa")

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"

    def __str__(self):
        return f"{self.user.username}: {self.title or 'Sin título'}"

    def add_message(self, sender, content, sender_name=None, message_type='text'):
        """Agrega un mensaje a la conversación"""
        message = {
            'sender': sender,  # 'user' o 'ai'
            'content': content,
            'timestamp': timezone.now().isoformat(),
            'sender_name': sender_name,
            'type': message_type  # 'text', 'command', 'error', etc.
        }
        self.messages.append(message)
        self.updated_at = timezone.now()
        self.save(update_fields=['messages', 'updated_at'])

    def get_messages_for_ai(self):
        """Obtiene mensajes en formato para enviar a la IA"""
        return [
            {
                'role': 'user' if msg['sender'] == 'user' else 'assistant',
                'content': msg['content']
            }
            for msg in self.messages
            if msg.get('type') != 'error'  # Excluir mensajes de error
        ]

    def generate_title(self):
        """Genera un título automático basado en el primer mensaje del usuario"""
        if not self.title and self.messages:
            first_user_message = next(
                (msg for msg in self.messages if msg['sender'] == 'user'),
                None
            )
            if first_user_message:
                content = first_user_message['content'][:50]
                self.title = f"{content}{'...' if len(first_user_message['content']) > 50 else ''}"
                self.save(update_fields=['title'])

    @classmethod
    def get_or_create_active_conversation(cls, user):
        """Obtiene la conversación activa del usuario o crea una nueva"""
        # Buscar conversación activa más reciente
        active_conversation = cls.objects.filter(
            user=user,
            is_active=True
        ).first()

        if active_conversation:
            return active_conversation

        # Crear nueva conversación
        conversation_id = f"conv_{user.id}_{int(timezone.now().timestamp())}"
        conversation = cls.objects.create(
            user=user,
            conversation_id=conversation_id,
            title="Nueva conversación"
        )
        return conversation

    def get_recent_messages(self, limit=50):
        """Obtiene los mensajes más recientes"""
        return self.messages[-limit:] if self.messages else []


class CommandLog(models.Model):
    """Registro de comandos ejecutados por el asistente"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    command = models.TextField(help_text="Comando original del usuario")
    function_name = models.CharField(max_length=100, help_text="Nombre de la función ejecutada")
    params = models.JSONField(default=dict, help_text="Parámetros pasados a la función")
    result = models.JSONField(null=True, blank=True, help_text="Resultado de la ejecución")
    success = models.BooleanField(default=False, help_text="Si la ejecución fue exitosa")
    execution_time = models.FloatField(default=0.0, help_text="Tiempo de ejecución en segundos")
    executed_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, help_text="Mensaje de error si falló")

    class Meta:
        ordering = ['-executed_at']
        verbose_name = "Registro de Comando"
        verbose_name_plural = "Registros de Comandos"

    def __str__(self):
        return f"{self.user.username}: {self.function_name} ({'OK' if self.success else 'ERROR'})"


class AssistantConfiguration(models.Model):
    """Configuración personalizable del asistente de IA"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="Nombre de la configuración")
    is_active = models.BooleanField(default=False, help_text="Configuración activa actualmente")

    # Configuración del modelo
    model_name = models.CharField(max_length=100, default='llama2', help_text="Nombre del modelo de IA")
    temperature = models.FloatField(default=0.7, help_text="Temperatura para la generación (0.0-2.0)")
    max_tokens = models.IntegerField(default=2048, help_text="Máximo número de tokens en respuesta")
    top_p = models.FloatField(default=0.9, help_text="Top-p sampling")
    top_k = models.IntegerField(default=40, help_text="Top-k sampling")

    # Prompts y contexto
    system_prompt = models.TextField(
        default="Eres un asistente de IA útil y amigable.",
        help_text="Prompt del sistema que define el comportamiento del asistente"
    )
    initial_context = models.TextField(
        blank=True,
        help_text="Contexto inicial adicional para todas las conversaciones"
    )

    # Datos adicionales
    additional_data = models.JSONField(
        default=dict,
        help_text="Datos adicionales como objetos, archivos, texto, etc."
    )

    # Configuración de funciones
    enabled_functions = models.JSONField(
        default=list,
        help_text="Lista de funciones habilitadas para este asistente"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Configuración del Asistente"
        verbose_name_plural = "Configuraciones del Asistente"

    def __str__(self):
        return f"{self.user.username}: {self.name} ({'Activa' if self.is_active else 'Inactiva'})"

    def save(self, *args, **kwargs):
        # Asegurar que solo haya una configuración activa por usuario
        if self.is_active:
            AssistantConfiguration.objects.filter(
                user=self.user,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_config(cls, user):
        """Obtiene la configuración activa del usuario"""
        return cls.objects.filter(user=user, is_active=True).first()

    @classmethod
    def get_or_create_default(cls, user):
        """Obtiene la configuración activa o crea una por defecto"""
        config = cls.get_active_config(user)
        if not config:
            config = cls.objects.create(
                user=user,
                name="Configuración por defecto",
                is_active=True
            )
        return config


class HardcodedNotificationManager:
    """Manager for hardcoded notifications - simple implementation for testing"""

    @classmethod
    def get_notifications_data(cls, user, limit=20):
        """Get notifications data for a user"""
        try:
            # Return hardcoded notifications for testing
            notifications = [
                {
                    'id': 1,
                    'title': 'Bienvenido al sistema',
                    'message': '¡Bienvenido a Management360! Explora las funciones disponibles.',
                    'type': 'system',
                    'created_at': timezone.now().isoformat(),
                    'is_read': False,
                    'room_id': None,
                    'sender': 'Sistema'
                },
                {
                    'id': 2,
                    'title': 'Actualización disponible',
                    'message': 'Hay nuevas funciones disponibles en el panel de chat.',
                    'type': 'update',
                    'created_at': timezone.now().isoformat(),
                    'is_read': False,
                    'room_id': None,
                    'sender': 'Sistema'
                }
            ]

            unread_count = len([n for n in notifications if not n['is_read']])

            return {
                'notifications': notifications[:limit],
                'unread_count': unread_count,
                'total': len(notifications)
            }

        except Exception as e:
            logger.error(f"Error getting notifications data for user {user.username}: {str(e)}")
            return {
                'notifications': [],
                'unread_count': 0,
                'total': 0
            }

    def get_all_notifications(self, user, include_read=True):
        """Get all notifications for a user"""
        try:
            # Return hardcoded notifications
            notifications = [
                {
                    'id': 1,
                    'title': 'Bienvenido al sistema',
                    'message': '¡Bienvenido a Management360!',
                    'type': 'system',
                    'created_at': timezone.now().isoformat(),
                    'is_read': False,
                    'room_id': None,
                    'sender': 'Sistema'
                },
                {
                    'id': 2,
                    'title': 'Actualización disponible',
                    'message': 'Nuevas funciones en el chat.',
                    'type': 'update',
                    'created_at': timezone.now().isoformat(),
                    'is_read': False,
                    'room_id': None,
                    'sender': 'Sistema'
                }
            ]

            if not include_read:
                notifications = [n for n in notifications if not n['is_read']]

            return notifications

        except Exception as e:
            logger.error(f"Error getting all notifications for user {user.username}: {str(e)}")
            return []

    def mark_notifications_read(self, user, notification_ids):
        """Mark notifications as read"""
        try:
            # Since these are hardcoded, just return the count
            return len(notification_ids) if notification_ids else 0
        except Exception as e:
            logger.error(f"Error marking notifications read for user {user.username}: {str(e)}")
            return 0

    @classmethod
    def create_chat_notification(cls, user, room, message, sender):
        """Create a chat notification"""
        try:
            # For now, just log and return a dummy notification
            logger.info(f"Creating chat notification for user {user.username} in room {room.name}: {message}")
            return {
                'id': 999,
                'title': f'Mensaje en {room.name}',
                'message': message,
                'type': 'chat',
                'created_at': timezone.now().isoformat(),
                'is_read': False,
                'room_id': room.id,
                'sender': sender.username if sender else 'Sistema'
            }
        except Exception as e:
            logger.error(f"Error creating chat notification: {str(e)}")
            return None


class UserPresence(models.Model):
    """Model for tracking user presence status"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10,
        choices=[
            ('online', 'Online'),
            ('away', 'Away'),
            ('offline', 'Offline')
        ],
        default='offline'
    )
    last_seen = models.DateTimeField(default=timezone.now)
    current_room = models.ForeignKey('rooms.Cell', on_delete=models.SET_NULL, null=True, blank=True)

    def is_online(self):
        """Check if user is considered online (last seen within 5 minutes)"""
        return self.status == 'online' and (timezone.now() - self.last_seen).seconds < 300

    def update_presence(self, status, room=None):
        """Update user's presence status"""
        self.status = status
        self.last_seen = timezone.now()
        if room:
            self.current_room = room
        self.save()

    class Meta:
        verbose_name = "User Presence"
        verbose_name_plural = "User Presences"


class MessageReaction(models.Model):
    """Model for message reactions (emojis)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.ForeignKey('rooms.Message', on_delete=models.CASCADE, related_name='reactions')
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('message', 'user', 'emoji')
        verbose_name = "Message Reaction"
        verbose_name_plural = "Message Reactions"

    def __str__(self):
        return f"{self.user.username} reacted {self.emoji} to message {self.message.id}"
