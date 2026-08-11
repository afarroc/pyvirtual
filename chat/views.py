from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.conf import settings
from django.contrib.auth import get_user_model

import os

User = get_user_model()
import asyncio
import json
import re
from .ollama_api import generate_response
from rooms.models import Cell, Message, MessageRead
from .functions import parse_command, function_registry, logged_functions
from datetime import datetime
import csv
import logging

logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
def mark_messages_read_api(request):
    """Marca como leídos los mensajes indicados por el usuario en una sala."""
    if request.method == 'POST':
        user = request.user
        data = json.loads(request.body)
        room_id = data.get('room_id')
        message_ids = data.get('message_ids', [])
        if not room_id or not message_ids:
            return JsonResponse({'error': 'room_id y message_ids requeridos'}, status=400)
        for msg_id in message_ids:
            MessageRead.objects.get_or_create(user=user, message_id=msg_id)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
@csrf_exempt
def unread_count_api(request):
    """Devuelve el número de mensajes no leídos por sala para el usuario actual."""
    user = request.user
    room_id = request.GET.get('room_id')
    if room_id:
        total_msgs = Message.objects.filter(room_id=room_id).count()
        read_msgs = MessageRead.objects.filter(user=user, message__room_id=room_id).count()
        unread = max(total_msgs - read_msgs, 0)
        return JsonResponse({'unread_count': unread})
    else:
        # Total unread across all rooms
        total_unread = 0
        rooms = Cell.objects.filter(cell_type='ROOM', is_active=True)
        for room in rooms:
            total_msgs = Message.objects.filter(room=room).count()
            read_msgs = MessageRead.objects.filter(user=user, message__room=room).count()
            total_unread += max(total_msgs - read_msgs, 0)
        return JsonResponse({'unread_count': total_unread})


@login_required
@csrf_exempt
def reset_unread_count_api(request):
    """Resetea el contador de mensajes no leídos para una sala específica o todas las salas."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        user = request.user
        data = json.loads(request.body)
        room_id = data.get('room_id')

        if room_id:
            # Reset for specific room
            unread_messages = Message.objects.filter(
                room_id=room_id
            ).exclude(
                id__in=MessageRead.objects.filter(
                    user=user,
                    message__room_id=room_id
                ).values_list('message_id', flat=True)
            )
        else:
            # Reset for all accessible rooms (owner or staff)
            unread_messages = Message.objects.filter(
                room__owner=user
            ).exclude(
                id__in=MessageRead.objects.filter(
                    user=user
                ).values_list('message_id', flat=True)
            ).distinct()
            if request.user.is_staff:
                staff_unread = Message.objects.filter(
                    room__cell_type='ROOM'
                ).exclude(
                    id__in=MessageRead.objects.filter(
                        user=user
                    ).values_list('message_id', flat=True)
                ).distinct()
                unread_messages = unread_messages | staff_unread

        # Mark all unread messages as read
        message_reads = []
        for message in unread_messages:
            message_reads.append(MessageRead(user=user, message=message))

        if message_reads:
            MessageRead.objects.bulk_create(message_reads)

        return JsonResponse({
            'success': True,
            'marked_read': len(message_reads),
            'message': f'Marked {len(message_reads)} messages as read'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def mark_notifications_read_api(request):
    """API to mark specific notifications as read"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        notification_ids = data.get('notification_ids', [])

        # Simplified implementation - just return success
        count = len(notification_ids) if notification_ids else 0

        return JsonResponse({
            'success': True,
            'marked_read': count,
            'message': f'Marked {count} notifications as read'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error in mark_notifications_read_api for user {request.user.username}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@csrf_exempt
def room_history_api(request, room_id):
    """Devuelve el historial de mensajes de una sala en formato JSON."""
    try:
        room = Cell.objects.get(id=room_id, cell_type='ROOM')
        chat_history = Message.objects.filter(room=room).select_related('user').order_by('created_at')[:50]
        history = []
        for msg in chat_history:
            user_id = msg.user.id if msg.user else 0
            display_name = f"{msg.user.first_name} {msg.user.last_name}".strip() if msg.user else f"User #{user_id}" if user_id else "Usuario"
            history.append({
                'user_id': user_id,
                'display_name': display_name,
                'content': msg.content,
                'timestamp': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        return JsonResponse({'history': history})
    except Cell.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)

@login_required
@csrf_exempt
def room_list_api(request):
    """Devuelve la lista de salas disponibles en formato JSON."""
    rooms = Cell.objects.filter(cell_type='ROOM', is_active=True).order_by('name')
    rooms_data = [
        {'id': room.id, 'name': room.name}
        for room in rooms
    ]
    return JsonResponse({'rooms': rooms_data})

# All imports are at the top of the file

# Panel flotante para incluir en cualquier página
@login_required
@csrf_exempt
def chat_panel(request):
    rooms = Cell.objects.filter(cell_type='ROOM', is_active=True).order_by('name')
    context = {
        'rooms': rooms,
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'user_email': request.user.email,
        'user_id': request.user.id,
        'user_date_joined': request.user.date_joined,
    }
    return render(request, 'chat/panel.html', context)

# Redirección automática a la sala por defecto
@login_required
def redirect_to_last_room(request):
    last_message = Message.objects.filter(user=request.user).order_by('-created_at').first()
    if last_message:
        room_name = str(last_message.room.id)
    else:
        room_name = 'global'
    return redirect('chat:room', room_name=room_name)

@login_required
def last_room_api(request):
    user = request.user
    last_message = Message.objects.filter(user=user).order_by('-created_at').first()
    if last_message:
        return JsonResponse({'room_name': str(last_message.room.id)})
    # Si no hay historial, usar 'global'
    return JsonResponse({'room_name': 'global'})
# Borra el historial de mensajes de una sala
@login_required
@require_POST
def clear_history_room(request, room_name):
    try:
        room = Cell.objects.get(id=room_name, cell_type='ROOM')
        Message.objects.filter(room=room).delete()
        # Broadcast to all clients in the room
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        group_name = f"chat_{room_name}"
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'history_cleared',
            }
        )
        return JsonResponse({'success': True})
    except Cell.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Room not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
class AIResponseError(Exception):
    """Excepción personalizada para errores en la respuesta de la IA."""
    pass


# Rate limiting function
def check_rate_limit(user_id, limit=5, period=60):
    cache_key = f'chat_rate_{user_id}'
    current = cache.get(cache_key, 0)
    if current >= limit:
        return False
    cache.set(cache_key, current + 1, period)
    return True


def moderate_message(content):
    # Lista básica de palabras prohibidas
    forbidden_words = ['badword1', 'badword2']
    for word in forbidden_words:
        if word in content.lower():
            return False
    return True



@login_required
@csrf_exempt
def chat_view(request):
    from .models import Conversation

    if request.method == "GET":
        return JsonResponse({"status": "ok", "message": "Chat API disponible. Usa POST para interactuar."})
    if request.method == "POST":
        try:
            if not check_rate_limit(request.user.id):
                return JsonResponse({"error": "Rate limit exceeded. Please wait a minute."}, status=429)

            # Get user input safely
            user_input = request.POST.get("user_input", "").strip()

            # Obtener conversación activa
            conversation = Conversation.get_or_create_active_conversation(request.user)
            logger.info(f"Chat message from user {request.user.username} using conversation: {conversation.id} - {conversation.title} (conversation_id: {conversation.conversation_id})")

            # Procesar comandos de funciones
            command_data = parse_command(user_input)
            if command_data:
                logged_func_name = f"{command_data['function_name']}_logged"
                logged_func = logged_functions.get(logged_func_name)

                if logged_func:
                    try:
                        result = logged_func(request.user, user_input, **command_data['params'])

                        # Guardar comando en conversación
                        conversation.add_message(
                            sender='user',
                            content=user_input,
                            sender_name=request.user.get_full_name(),
                            message_type='command'
                        )

                        # Guardar respuesta del comando
                        response_content = f"[OK] Comando ejecutado: {result.get('message', 'Comando completado')}"
                        conversation.add_message(
                            sender='ai',
                            content=response_content,
                            sender_name='Asistente',
                            message_type='command_response'
                        )

                        return JsonResponse({
                            "command_response": {
                                "function": command_data['function_name'],
                                "result": result
                            }
                        })
                    except Exception as e:
                        # Guardar error del comando
                        conversation.add_message(
                            sender='user',
                            content=user_input,
                            sender_name=request.user.get_full_name(),
                            message_type='command'
                        )
                        conversation.add_message(
                            sender='ai',
                            content=f"[ERROR] Error ejecutando comando: {str(e)}",
                            sender_name='Asistente',
                            message_type='error'
                        )

                        return JsonResponse({
                            "command_response": {
                                "function": command_data['function_name'],
                                "error": f"Error ejecutando función: {str(e)}"
                            }
                        })
                else:
                    # Comando no encontrado
                    conversation.add_message(
                        sender='user',
                        content=user_input,
                        sender_name=request.user.get_full_name(),
                        message_type='command'
                    )
                    conversation.add_message(
                        sender='ai',
                        content=f"[ERROR] Función '{command_data['function_name']}' no encontrada",
                        sender_name='Asistente',
                        message_type='error'
                    )

                    return JsonResponse({
                        "command_response": {
                            "error": f"Función '{command_data['function_name']}' no encontrada"
                        }
                    })

            # Moderación
            if not moderate_message(user_input):
                return JsonResponse({"error": "Message contains inappropriate content"}, status=400)

            chat_history_str = request.POST.get("chat_history", "[]")
            chat_history = json.loads(chat_history_str) if chat_history_str else []

            # If no chat_history provided, load from active conversation
            if not chat_history:
                conversation_messages = conversation.get_recent_messages(limit=50)
                chat_history = [
                    {
                        'role': 'user' if msg['sender'] == 'user' else 'assistant',
                        'content': msg['content'],
                        'sender_name': msg.get('sender_name', request.user.get_full_name() if msg['sender'] == 'user' else 'Asistente')
                    }
                    for msg in conversation_messages
                ]

            # Store chat history in cache (para compatibilidad)
            cache_key = f'chat_history_{request.user.id}'
            cache.set(cache_key, chat_history, timeout=3600)  # 1 hour expiry

            # Validate and prepare message history
            user_full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            messages = []
            for msg in chat_history:
                if not isinstance(msg, dict):
                    continue
                role = msg.get('role') or msg.get('sender')
                if role == 'user':
                    messages.append({
                        "role": "user",
                        "content": str(msg.get('content', '')),
                        "sender_name": msg.get('sender_name', user_full_name)
                    })
                elif role == 'assistant':
                    messages.append({
                        "role": "assistant",
                        "content": str(msg.get('content', '')),
                        "sender_name": msg.get('sender_name', 'Asistente')
                    })

            # Validar que haya mensaje del usuario
            if not user_input and not messages:
                return JsonResponse({"error": "No se recibió mensaje del usuario ni historial."}, status=400)

            # Añadir el mensaje actual del usuario solo si no está ya como último mensaje
            if user_input and not (messages and messages[-1]["role"] == "user" and messages[-1]["content"] == user_input):
                messages.append({
                    "role": "user",
                    "content": user_input,
                    "sender_name": user_full_name
                })

            # Guardar mensaje del usuario en conversación
            conversation.add_message(
                sender='user',
                content=user_input,
                sender_name=user_full_name,
                message_type='text'
            )

            # Generar título si es la primera conversación
            if not conversation.title or conversation.title == "Nueva conversación":
                conversation.generate_title()

            ai_response_content = ""

            async def stream_generator():
                nonlocal ai_response_content
                try:
                    async for chunk in generate_response(messages):
                        if not chunk or not isinstance(chunk, dict):
                            continue
                        # Support both formats: {'message': {'content': ...}} and {'content': ...}
                        content = ''
                        if 'message' in chunk:
                            content = chunk['message'].get('content', '')
                        elif 'content' in chunk:
                            content = chunk['content']
                        if 'error' in chunk:
                            raise AIResponseError(chunk['error'])
                        if content:
                            ai_response_content += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                            await asyncio.sleep(0)
                except AIResponseError as ai_err:
                    error_msg = f'AIResponseError: {str(ai_err)}'
                    ai_response_content = error_msg
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                except Exception as e:
                    error_msg = f'InternalError: {str(e)}'
                    ai_response_content = error_msg
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                finally:
                    # Guardar respuesta de IA en conversación
                    if ai_response_content:
                        conversation.add_message(
                            sender='ai',
                            content=ai_response_content,
                            sender_name='Asistente',
                            message_type='text'
                        )
                    yield "data: [DONE]\n\n"

            response = StreamingHttpResponse(
                stream_generator(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid chat history format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    # Si no es GET ni POST, devolver JSON de error
    return JsonResponse({"error": "Método no permitido. Usa POST para interactuar con el chat."}, status=405)


@login_required
@csrf_exempt
def clear_chat(request):
    if request.method == "POST":
        try:
            # Add any server-side cleanup logic here
            return JsonResponse({
                "status": "success",
                "message": "Chat cleared successfully"
            })
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)
    
    return JsonResponse({
        "status": "error",
        "message": "Method not allowed"
    }, status=405)


@login_required
def export_chat_history(request):
    try:
        chat_history = json.loads(request.POST.get("chat_history", "[]"))
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="chat_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Sender', 'Message'])
        
        for msg in chat_history:
            writer.writerow([
                msg.get('timestamp', ''),
                msg.get('sender', ''),
                msg.get('content', '')
            ])
        
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def index(request):
    from rooms.models import Cell

    rooms = Cell.objects.filter(cell_type='ROOM', is_active=True)
    total_rooms = rooms.count()
    total_users = sum(
        1 for cell in rooms
        if cell.owner_id is not None or cell.is_active
    )

    context = {
        'pagetitle': 'Chat Index',
        'is_moderator': request.user.is_staff or request.user.groups.filter(name='Moderators').exists(),
        'total_rooms': total_rooms,
        'total_users': total_users,
    }
    return render(request, "chat/index.html", context)


@login_required
def chatroom(request, room_name):
    if not room_name or not str(room_name).isdigit():
        messages.error(request, "Invalid room ID")
        return redirect('chat:index')
    
    # Add analytics
    cache_key = f'room_visits_{room_name}'
    cache.set(cache_key, cache.get(cache_key, 0) + 1)
    
    rooms = Cell.objects.filter(cell_type='ROOM', is_active=True).order_by('name')
    context = {
        "room_name": room_name,
        "pagetitle": f"Chat Room #{room_name}",
        "current_user": request.user.username,
        "user_id": request.user.id,
        "user_email": request.user.email,
        "user_full_name": f"{request.user.first_name} {request.user.last_name}".strip(),
        "user_date_joined": request.user.date_joined,
        "user_last_login": request.user.last_login,
        "timestamp": timezone.now().isoformat(),
        "is_moderator": request.user.is_staff,
        "is_superuser": request.user.is_superuser,
        "message_format": {
            "date_format": "H:i:s a",
            "timezone": str(timezone.get_current_timezone()),
        },
        "room_stats": {
            "visits": cache.get(f'room_visits_{room_name}', 0),
            "created_at": timezone.now(),
            "last_activity": timezone.now(),
        },
        "chat_settings": {
            "max_length": 1000,
            "rate_limit": 5,
            "rate_period": 60,
        },
        "room_features": {
            "attachments_enabled": True,
            "max_file_size": 5 * 1024 * 1024,
            "allowed_file_types": ['.txt', '.pdf', '.png', '.jpg', '.jpeg'],
            "commands_enabled": True,
            "moderation_enabled": True,
            "search_enabled": True,
        },
        "notifications": {
            "enabled": True,
            "sound_enabled": True,
            "desktop_enabled": True,
        },
        "rooms": rooms
    }
    
    return render(request, "chat/room.html", context)


@login_required
@csrf_exempt
def search_history(request):
    query = request.GET.get('q', '').strip()
    room_id = request.GET.get('room_id')
    user_filter = request.GET.get('user')
    date_filter = request.GET.get('date')

    if not query:
        return JsonResponse({"results": [], "total": 0})

    # Build queryset
    from rooms.models import Message
    messages = Message.objects.select_related('user').order_by('-created_at')

    if room_id:
        messages = messages.filter(room_id=room_id)

    # Apply user filter
    if user_filter:
        messages = messages.filter(user__username__icontains=user_filter)

    # Apply date filter
    if date_filter:
        from datetime import datetime, timedelta
        now = datetime.now()

        if date_filter == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == 'week':
            start_date = now - timedelta(days=7)
        elif date_filter == 'month':
            start_date = now - timedelta(days=30)
        else:
            start_date = None

        if start_date:
            messages = messages.filter(created_at__gte=start_date)

    # Apply content search
    messages = messages.filter(content__icontains=query)[:50]  # Limit results

    # Format results
    results = []
    for msg in messages:
        results.append({
            'id': msg.id,
            'content': msg.content,
            'user': msg.user.username if msg.user else 'Unknown',
            'display_name': f"{msg.user.first_name} {msg.user.last_name}".strip() if msg.user else 'Unknown',
            'timestamp': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'room_id': msg.room.id if msg.room else None,
            'room_name': msg.room.name if msg.room else 'Unknown'
        })

    return JsonResponse({
        "results": results,
        "total": len(results),
        "query": query
    })


@login_required
@csrf_exempt
def upload_attachment(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        # Validar tipo de archivo y tamaño
        if file.size > 5 * 1024 * 1024:  # 5MB limit
            return JsonResponse({"error": "File too large"}, status=400)
            
        allowed_types = ['.txt', '.pdf', '.png', '.jpg', '.jpeg']
        if not any(file.name.lower().endswith(ext) for ext in allowed_types):
            return JsonResponse({"error": "Invalid file type"}, status=400)
            
        # Guardar archivo
        path = default_storage.save(f'chat_attachments/{request.user.id}/{file.name}', file)
        return JsonResponse({"url": default_storage.url(path)})
        
    return JsonResponse({"error": "No file provided"}, status=400)


def process_commands(message):
    commands = {
        '/help': lambda: "Available commands: /help, /clear, /export",
        '/clear': lambda: "Clearing chat history...",
        '/export': lambda: "Exporting chat history..."
    }
    
    if message.startswith('/'):
        command = message.split()[0]
        if command in commands:
            return commands[command]()
    return None


@login_required
def room_list(request):
    from rooms.models import Cell, Message, MessageRead
    from .models import Conversation

    search_query = request.GET.get('search', '').strip()
    show_empty = request.GET.get('show_empty', 'true').lower() == 'true'

    cells = Cell.objects.filter(cell_type='ROOM', is_active=True).order_by('name')

    if search_query:
        cells = cells.filter(
            models.Q(name__icontains=search_query) |
            models.Q(description__icontains=search_query)
        )

    message_counts = {
        cell.id: Message.objects.filter(room=cell).count()
        for cell in cells
    }

    rooms_data = []
    for cell in cells:
        is_member = cell.owner_id == request.user.id or request.user.is_staff
        can_manage = cell.owner_id == request.user.id or request.user.is_staff

        total_messages = message_counts.get(cell.id, 0)
        read_messages = MessageRead.objects.filter(
            user=request.user,
            message__room=cell
        ).count()
        unread_count = max(total_messages - read_messages, 0)

        last_message = Message.objects.filter(room=cell).order_by('-created_at').first()
        last_activity = last_message.created_at if last_message else None

        rooms_data.append({
            'room': cell,
            'is_member': is_member,
            'can_manage': can_manage,
            'unread_count': unread_count,
            'last_activity': last_activity,
            'online_members': 0,
            'member_count': 1 if cell.owner_id else 0,
            'message_count': total_messages,
        })

    if not show_empty:
        rooms_data = [rd for rd in rooms_data if rd['message_count'] > 0]

    user_conversations = Conversation.objects.filter(user=request.user)
    active_conversations = user_conversations.filter(is_active=True).count()
    total_conversations = user_conversations.count()

    context = {
        'pagetitle': 'Chat Rooms - Management Dashboard',
        'rooms_data': rooms_data,
        'search_query': search_query,
        'show_empty': show_empty,
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'user_email': request.user.email,
        'user_id': request.user.id,
        'user_date_joined': request.user.date_joined,
        'stats': {
            'total_rooms': len(rooms_data),
            'user_conversations': total_conversations,
            'active_conversations': active_conversations,
            'total_unread_notifications': 0,
        },
        'can_create_room': True,
    }
    return render(request, 'chat/room_list.html', context)


@login_required
def room(request, room_name):
    user_full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    try:
        room_obj = Cell.objects.get(id=room_name, cell_type='ROOM')
    except Cell.DoesNotExist:
        messages.error(request, "Room not found")
        return redirect('chat:room_list')

    chat_history = Message.objects.filter(room=room_obj).select_related('user').order_by('created_at')[:50]
    history = []
    color_palette = [
        "#007bff", "#28a745", "#dc3545", "#fd7e14", "#6610f2",
        "#20c997", "#6f42c1", "#e83e8c", "#17a2b8", "#ffc107", "#343a40"
    ]
    for msg in chat_history:
        user_id = msg.user.id if msg.user else 0
        color = color_palette[user_id % len(color_palette)]
        if msg.user:
            display_name = f"{msg.user.first_name} {msg.user.last_name}".strip()
            if not display_name:
                display_name = msg.user.username
        else:
            display_name = f"User #{user_id}" if user_id else "Usuario"
        history.append({
            'user_id': user_id,
            'display_name': display_name,
            'content': msg.content,
            'timestamp': msg.created_at,
            'color': color,
        })

    from rooms.models import Cell as CellModel
    all_rooms = CellModel.objects.filter(cell_type='ROOM', is_active=True).order_by('name')
    context = {
        'pagetitle': f'Chat Room: {room_obj.name}',
        'room_name': room_obj.id,
        'current_user': request.user.username,
        'user_full_name': user_full_name,
        'user_email': request.user.email,
        'user_id': request.user.id,
        'user_date_joined': request.user.date_joined,
        'is_moderator': request.user.groups.filter(name='Moderators').exists(),
        'chat_history': history,
        'rooms': all_rooms,
    }
    return render(request, 'chat/room.html', context)


@login_required
def assistant_view(request):
    from .models import Conversation

    # Obtener o crear conversación activa
    conversation = Conversation.get_or_create_active_conversation(request.user)
    logger.info(f"Assistant view loaded for user {request.user.username} with active conversation: {conversation.id} - {conversation.title} (conversation_id: {conversation.conversation_id})")

    # Obtener historial de mensajes (últimos 50 para inicialización)
    recent_messages = conversation.get_recent_messages(limit=50)
    logger.info(f"Loaded {len(recent_messages)} messages for conversation {conversation.id}")

    # Formatear para el template (compatible con el formato existente)
    initial_history = []
    for msg in recent_messages:
        initial_history.append({
            'sender': msg['sender'],
            'content': msg['content'],
            'timestamp': msg['timestamp'],
            'sender_name': msg.get('sender_name', 'Asistente' if msg['sender'] == 'ai' else request.user.get_full_name())
        })

    context = {
        'pagetitle': 'AI Assistant',
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'user_email': request.user.email,
        'user_id': request.user.id,
        'user_date_joined': request.user.date_joined,
        'initial_history': json.dumps(initial_history),
        'conversation_id': conversation.conversation_id,
    }
    return render(request, 'chat/assistant.html', context)


@login_required
def functions_panel(request):
    """Panel de funciones disponibles para el asistente"""
    functions = function_registry.list_functions()

    # Organizar funciones por categorías
    categories = {}
    for name, func_data in functions.items():
        category = 'General'  # Por ahora todas en general
        if category not in categories:
            categories[category] = []
        categories[category].append({
            'name': name,
            'description': func_data['description'],
            'parameters': func_data['parameters'],
            'examples': func_data['examples']
        })

    # Estadísticas de uso
    from .models import CommandLog
    total_commands = CommandLog.objects.filter(user=request.user).count()
    successful_commands = CommandLog.objects.filter(user=request.user, success=True).count()
    failed_commands = total_commands - successful_commands
    success_rate = (successful_commands / total_commands * 100) if total_commands > 0 else 0

    context = {
        'pagetitle': 'Panel de Funciones del Asistente',
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'categories': categories,
        'stats': {
            'total': total_commands,
            'successful': successful_commands,
            'failed': failed_commands,
            'success_rate': success_rate
        },
        'functions': functions
    }
    return render(request, 'chat/functions_panel.html', context)


@login_required
def command_history(request):
    """Historial de comandos ejecutados por el asistente"""
    from .models import CommandLog

    # Obtener comandos del usuario actual
    commands = CommandLog.objects.filter(user=request.user).order_by('-executed_at')[:50]

    # Estadísticas
    total_commands = CommandLog.objects.filter(user=request.user).count()
    successful_commands = CommandLog.objects.filter(user=request.user, success=True).count()
    failed_commands = total_commands - successful_commands

    # Comandos recientes (últimos 10)
    recent_commands = []
    for cmd in commands[:10]:
        recent_commands.append({
            'id': cmd.id,
            'command': cmd.command,
            'function_name': cmd.function_name,
            'success': cmd.success,
            'executed_at': cmd.executed_at,
            'execution_time': cmd.execution_time,
            'result': json.dumps(cmd.result, indent=2, ensure_ascii=False) if cmd.result else None
        })

    context = {
        'pagetitle': 'Historial de Comandos del Asistente',
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'commands': recent_commands,
        'stats': {
            'total': total_commands,
            'successful': successful_commands,
            'failed': failed_commands,
            'success_rate': (successful_commands / total_commands * 100) if total_commands > 0 else 0
        }
    }
    return render(request, 'chat/command_history.html', context)


@login_required
def conversation_history(request):
    """Historial de conversaciones con el asistente IA"""
    from .models import Conversation

    # Obtener conversaciones del usuario
    conversations = Conversation.objects.filter(user=request.user).order_by('-updated_at')

    # Estadísticas
    total_conversations = conversations.count()
    active_conversations = conversations.filter(is_active=True).count()
    total_messages = sum(len(conv.messages) for conv in conversations)

    # Conversaciones recientes
    recent_conversations = []
    for conv in conversations[:20]:  # Últimas 20 conversaciones
        recent_conversations.append({
            'id': conv.id,
            'conversation_id': conv.conversation_id,
            'title': conv.title,
            'created_at': conv.created_at,
            'updated_at': conv.updated_at,
            'is_active': conv.is_active,
            'message_count': len(conv.messages),
            'last_message': conv.messages[-1] if conv.messages else None
        })

    context = {
        'pagetitle': 'Historial de Conversaciones con IA',
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'conversations': recent_conversations,
        'stats': {
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'total_messages': total_messages,
            'avg_messages_per_conversation': total_messages / total_conversations if total_conversations > 0 else 0
        }
    }
    return render(request, 'chat/conversation_history.html', context)


@login_required
def conversation_detail(request, conversation_id):
    """Vista detallada de una conversación específica"""
    from .models import Conversation

    try:
        logger.info(f"Switch conversation request for user {request.user.username} with conversation_id: {conversation_id}")
        conversation = None

        # Try multiple ways to find the conversation
        if conversation_id:
            # First try by conversation_id field
            try:
                conversation = Conversation.objects.get(
                    conversation_id=conversation_id,
                    user=request.user
                )
                logger.info(f"Found conversation by conversation_id field: {conversation.id} - {conversation.title}")
            except Conversation.DoesNotExist:
                logger.info(f"Conversation not found by conversation_id field: {conversation_id}")

        # If not found and conversation_id is numeric, try by id
        if not conversation and conversation_id and conversation_id.isdigit():
            try:
                conversation = Conversation.objects.get(
                    id=int(conversation_id),
                    user=request.user
                )
                logger.info(f"Found conversation by id field: {conversation.id} - {conversation.title}")
            except Conversation.DoesNotExist:
                logger.info(f"Conversation not found by id field: {conversation_id}")

        # If still not found, try by id anyway (in case conversation_id is the pk as string)
        if not conversation:
            try:
                conversation = Conversation.objects.get(
                    id=int(conversation_id) if conversation_id.isdigit() else conversation_id,
                    user=request.user
                )
                logger.info(f"Found conversation by fallback id lookup: {conversation.id} - {conversation.title}")
            except (Conversation.DoesNotExist, ValueError):
                logger.info(f"Conversation not found by fallback lookup: {conversation_id}")

        if not conversation:
            logger.error(f"No conversation found for user {request.user.username} with conversation_id: {conversation_id}")
            raise Conversation.DoesNotExist("Conversation not found")

        # Marcar como activa si no lo está
        if not conversation.is_active:
            # Desactivar otras conversaciones activas
            Conversation.objects.filter(
                user=request.user,
                is_active=True
            ).exclude(id=conversation.id).update(is_active=False)
            # Activar esta conversación
            conversation.is_active = True
            conversation.save()

        context = {
            'pagetitle': f'Conversación: {conversation.title}',
            'user_full_name': f"{request.user.first_name} {request.user.last_name}",
            'conversation': conversation,
            'messages': conversation.messages
        }
        return render(request, 'chat/conversation_detail.html', context)

    except Conversation.DoesNotExist:
        messages.error(request, 'Conversación no encontrada')
        return redirect('chat:conversation_history')


@login_required
def clear_history(request):
    if request.method == 'POST':
        # Add chat clearing logic here
        messages.success(request, 'Chat history cleared successfully')
    return redirect('chat:room_list')

@login_required
@csrf_exempt
def add_reaction(request, message_id):
    """Add or remove a reaction to a message"""
    if request.method == 'POST':
        try:
            from rooms.models import Message
            from .models import MessageReaction

            data = json.loads(request.body)
            emoji = data.get('emoji')

            if not emoji:
                return JsonResponse({'error': 'Emoji is required'}, status=400)

            try:
                message = Message.objects.get(id=message_id)
            except Message.DoesNotExist:
                return JsonResponse({'error': 'Message not found'}, status=404)

            # Check if reaction already exists
            reaction, created = MessageReaction.objects.get_or_create(
                message=message,
                user=request.user,
                emoji=emoji
            )

            if not created:
                # Remove reaction if it already exists
                reaction.delete()
                action = 'removed'
            else:
                action = 'added'

            return JsonResponse({
                'success': True,
                'action': action,
                'emoji': emoji,
                'message_id': message_id
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    
@login_required
def assistant_configurations(request):
    """Vista principal del panel de configuraciones del asistente"""
    from .models import AssistantConfiguration

    configurations = AssistantConfiguration.objects.filter(user=request.user)
    active_config = AssistantConfiguration.get_active_config(request.user)

    context = {
        'pagetitle': 'Configuraciones del Asistente',
        'configurations': configurations,
        'active_config': active_config,
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'user_email': request.user.email,
        'user_id': request.user.id,
        'user_date_joined': request.user.date_joined,
    }
    return render(request, 'chat/assistant_configurations.html', context)
    
    
@login_required
def create_assistant_configuration(request):
        """Crear nueva configuración del asistente"""
        from .models import AssistantConfiguration
    
        if request.method == 'POST':
            try:
                # Obtener datos del formulario
                name = request.POST.get('name', '').strip()
                model_name = request.POST.get('model_name', 'llama2')
                temperature = float(request.POST.get('temperature', 0.7))
                max_tokens = int(request.POST.get('max_tokens', 2048))
                top_p = float(request.POST.get('top_p', 0.9))
                top_k = int(request.POST.get('top_k', 40))
                system_prompt = request.POST.get('system_prompt', '')
                initial_context = request.POST.get('initial_context', '')
                is_active = request.POST.get('is_active') == 'on'
    
                # Validaciones
                if not name:
                    messages.error(request, 'El nombre de la configuración es obligatorio')
                    return redirect('chat:assistant_configurations')
    
                if not (0.0 <= temperature <= 2.0):
                    messages.error(request, 'La temperatura debe estar entre 0.0 y 2.0')
                    return redirect('chat:assistant_configurations')
    
                # Procesar datos adicionales
                additional_data = {}
                if request.POST.get('additional_text'):
                    additional_data['text'] = request.POST.get('additional_text')
    
                # Procesar archivos si los hay
                if request.FILES.getlist('additional_files'):
                    additional_data['files'] = []
                    for file in request.FILES.getlist('additional_files'):
                        # Guardar archivo y agregar referencia
                        file_path = default_storage.save(f'assistant_files/{request.user.id}/{file.name}', file)
                        additional_data['files'].append({
                            'name': file.name,
                            'path': file_path,
                            'url': default_storage.url(file_path)
                        })
    
                # Procesar funciones habilitadas
                enabled_functions = request.POST.getlist('enabled_functions')
    
                # Crear configuración
                config = AssistantConfiguration.objects.create(
                    user=request.user,
                    name=name,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    top_k=top_k,
                    system_prompt=system_prompt,
                    initial_context=initial_context,
                    additional_data=additional_data,
                    enabled_functions=enabled_functions,
                    is_active=is_active
                )
    
                messages.success(request, f'Configuración "{name}" creada exitosamente')
                return redirect('chat:assistant_configurations')
    
            except ValueError as e:
                messages.error(request, f'Error en los datos numéricos: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error al crear configuración: {str(e)}')
    
        return redirect('chat:assistant_configurations')
    
    
@login_required
def edit_assistant_configuration(request, config_id):
    """Editar configuración del asistente"""
    from .models import AssistantConfiguration

    try:
        config = AssistantConfiguration.objects.get(id=config_id, user=request.user)
    except AssistantConfiguration.DoesNotExist:
        messages.error(request, 'Configuración no encontrada')
        return redirect('chat:assistant_configurations')

    if request.method == 'POST':
        try:
            # Actualizar datos
            config.name = request.POST.get('name', config.name).strip()
            config.model_name = request.POST.get('model_name', config.model_name)
            config.temperature = float(request.POST.get('temperature', config.temperature))
            config.max_tokens = int(request.POST.get('max_tokens', config.max_tokens))
            config.top_p = float(request.POST.get('top_p', config.top_p))
            config.top_k = int(request.POST.get('top_k', config.top_k))
            config.system_prompt = request.POST.get('system_prompt', config.system_prompt)
            config.initial_context = request.POST.get('initial_context', config.initial_context)
            config.is_active = request.POST.get('is_active') == 'on'

            # Validaciones
            if not config.name:
                messages.error(request, 'El nombre de la configuración es obligatorio')
                return redirect('chat:edit_assistant_configuration', config_id=config_id)

            if not (0.0 <= config.temperature <= 2.0):
                messages.error(request, 'La temperatura debe estar entre 0.0 y 2.0')
                return redirect('chat:edit_assistant_configuration', config_id=config_id)

            # Actualizar datos adicionales
            additional_data = config.additional_data.copy()
            if request.POST.get('additional_text'):
                additional_data['text'] = request.POST.get('additional_text')
            elif 'text' in additional_data:
                del additional_data['text']

            # Procesar nuevos archivos
            if request.FILES.getlist('additional_files'):
                if 'files' not in additional_data:
                    additional_data['files'] = []
                for file in request.FILES.getlist('additional_files'):
                    file_path = default_storage.save(f'assistant_files/{request.user.id}/{file.name}', file)
                    additional_data['files'].append({
                        'name': file.name,
                        'path': file_path,
                        'url': default_storage.url(file_path)
                    })

            config.additional_data = additional_data
            config.enabled_functions = request.POST.getlist('enabled_functions')
            config.save()

            messages.success(request, f'Configuración "{config.name}" actualizada exitosamente')
            return redirect('chat:assistant_configurations')

        except ValueError as e:
            messages.error(request, f'Error en los datos numéricos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al actualizar configuración: {str(e)}')

    # Para GET, mostrar formulario de edición
    context = {
        'pagetitle': f'Editar Configuración: {config.name}',
        'config': config,
        'user_full_name': f"{request.user.first_name} {request.user.last_name}",
        'user_email': request.user.email,
        'user_id': request.user.id,
        'user_date_joined': request.user.date_joined,
    }
    return render(request, 'chat/edit_assistant_configuration.html', context)
    
    
@login_required
def delete_assistant_configuration(request, config_id):
    """Eliminar configuración del asistente"""
    from .models import AssistantConfiguration

    if request.method == 'POST':
        try:
            config = AssistantConfiguration.objects.get(id=config_id, user=request.user)
            name = config.name
            config.delete()
            messages.success(request, f'Configuración "{name}" eliminada exitosamente')
        except AssistantConfiguration.DoesNotExist:
            messages.error(request, 'Configuración no encontrada')
        except Exception as e:
            messages.error(request, f'Error al eliminar configuración: {str(e)}')

        return redirect('chat:assistant_configurations')
     
    return redirect('chat:assistant_configurations')

# Public AI test endpoint - no authentication required
@csrf_exempt
def ai_test(request):
    """Endpoint público para probar la IA Kilo integrada"""
    if request.method == 'GET':
        return JsonResponse({
            'status': 'ready',
            'backend': 'kilo' if os.getenv('USE_KILO', 'true').lower() == 'true' else 'ollama',
            'message': 'POST a este endpoint con {"message": "tu texto"} para interactuar con la IA',
            'endpoints': {
                'test': '/chat/test/',
                'ai_post': '/chat/ai/ (POST con message)',
                'rooms': '/chat/rooms/ (requiere auth)',
                'websocket': 'ws://127.0.0.1:8000/ws/chat/{room_id}/'
            }
        })
    
    if request.method == 'POST':
        user_message = request.POST.get('message', '') or request.GET.get('message', '')
        if not user_message:
            return JsonResponse({'error': 'message parameter required'}, status=400)
        
        # Usar generate_response_kilo_sync para respuesta inmediata
        from .ollama_api import generate_response_kilo_sync
        try:
            response_text = generate_response_kilo_sync([{'role': 'user', 'content': user_message}])
        except Exception as e:
            response_text = f"Error: {str(e)}"
        
        return JsonResponse({
            'response': response_text,
            'backend': 'kilo',
            'success': True
        })

# Simple synchronous chat endpoint for testing (no auth, no streaming)
@csrf_exempt
def chat_simple(request):
    """Chat simple sin streaming - útil para pruebas rápidas"""
    if request.method == 'GET':
        return JsonResponse({'status': 'ok', 'message': 'POST {"user_input": "texto"}'})
    
    if request.method == 'POST':
        user_input = request.POST.get('user_input', '') or request.GET.get('user_input', '')
        if not user_input:
            return JsonResponse({'error': 'user_input required'}, status=400)
        
        from .ollama_api import generate_response_kilo_sync
        response_text = generate_response_kilo_sync([{'role': 'user', 'content': user_input}])
        
        return JsonResponse({
            'response': response_text,
            'success': True
        })
    
    if request.method == 'POST':
        user_message = request.POST.get('message', request.GET.get('message', ''))
        if not user_message:
            return JsonResponse({'error': 'message parameter required'}, status=400)
        
        # Construir mensajes para la IA
        messages = [{'role': 'user', 'content': user_message}]
        
        # Importar y usar generate_response
        from .ollama_api import generate_response
        import asyncio
        
        # Para GET/POST síncronos, usar respuesta simple
        response_text = f"IA Kilo: Entendido '{user_message[:50]}...'. El sistema está operativo."
        
        return JsonResponse({
            'response': response_text,
            'backend': 'kilo'
        })
    
    
@login_required
@csrf_exempt
def set_active_configuration(request, config_id):
    """Establecer configuración activa"""
    from .models import AssistantConfiguration

    if request.method == 'POST':
        try:
            config = AssistantConfiguration.objects.get(id=config_id, user=request.user)
            config.is_active = True
            config.save()
            return JsonResponse({'success': True, 'message': f'Configuración "{config.name}" activada'})
        except AssistantConfiguration.DoesNotExist:
            return JsonResponse({'error': 'Configuración no encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@csrf_exempt
def conversation_messages_api(request, conversation_id):
    """API para obtener los mensajes de una conversación específica"""
    from .models import Conversation

    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        conversation = Conversation.objects.get(
            conversation_id=conversation_id,
            user=request.user
        )

        messages = conversation.get_recent_messages(limit=50)

        # Format messages for frontend
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'sender': msg['sender'],
                'content': msg['content'],
                'timestamp': msg['timestamp'],
                'sender_name': msg.get('sender_name', 'Asistente' if msg['sender'] == 'ai' else request.user.get_full_name())
            })

        return JsonResponse({
            'messages': formatted_messages,
            'conversation_title': conversation.title,
            'total_messages': len(messages)
        })

    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@login_required
def unread_notifications_api(request):
    """API endpoint for unread notifications"""
    if request.method == 'GET':
        from .models import HardcodedNotificationManager
        notification_manager = HardcodedNotificationManager()
        data = notification_manager.get_notifications_data(request.user)
        return JsonResponse(data)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def room_members_api(request, room_id):
    """API endpoint for room members"""
    try:
        from rooms.models import Cell

        cell = Cell.objects.get(id=room_id, cell_type='ROOM')

        if not (cell.owner_id == request.user.id or request.user.is_staff):
            return JsonResponse({'error': 'Access denied'}, status=403)

        members_data = []
        if cell.owner:
            members_data.append({
                'id': cell.owner.id,
                'username': cell.owner.username,
                'display_name': f"{cell.owner.first_name} {cell.owner.last_name}".strip() or cell.owner.username,
                'email': cell.owner.email,
                'is_online': True,
                'joined_at': cell.created_at.isoformat() if cell.created_at else None
            })

        return JsonResponse({
            'members': members_data,
            'total': len(members_data)
        })

    except Cell.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def room_notifications_api(request, room_id):
    """API endpoint for room notifications"""
    try:
        from rooms.models import Cell
        from .models import HardcodedNotificationManager

        cell = Cell.objects.get(id=room_id, cell_type='ROOM')

        if not (cell.owner_id == request.user.id or request.user.is_staff):
            return JsonResponse({'error': 'Access denied'}, status=403)

        # Get notifications for this room
        notification_manager = HardcodedNotificationManager()
        all_notifications = notification_manager.get_all_notifications(request.user, include_read=True)

        room_notifications = [
            n for n in all_notifications
            if n.get('room_id') == str(room_id)
        ]

        return JsonResponse({
            'notifications': room_notifications,
            'total': len(room_notifications)
        })

    except Cell.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def room_admin(request, room_id):
    """Room administration panel"""
    try:
        from rooms.models import Cell

        cell = Cell.objects.get(id=room_id, cell_type='ROOM')

        if not (cell.owner_id == request.user.id or request.user.is_staff):
            messages.error(request, 'Access denied')
            return redirect('chat:room_list')

        members = [cell.owner] if cell.owner else []

        context = {
            'room': cell,
            'members': members,
            'pagetitle': f'Admin - {cell.name}'
        }

        return render(request, 'chat/room_admin.html', context)

    except Cell.DoesNotExist:
        messages.error(request, 'Room not found')
        return redirect('chat:room_list')

@login_required
@csrf_exempt
def reset_unread_count_api(request):
    """API endpoint to reset unread message count for a room"""
    if request.method == 'POST':
        try:
            import json
            from rooms.models import MessageRead, Message

            data = json.loads(request.body)
            room_id = data.get('room_id')

            if not room_id:
                return JsonResponse({'error': 'room_id is required'}, status=400)

            # Mark all unread messages in this room as read for the current user
            unread_messages = Message.objects.filter(
                room_id=room_id
            ).exclude(
                messageread__user=request.user
            )

            marked_count = 0
            for message in unread_messages:
                MessageRead.objects.get_or_create(
                    user=request.user,
                    message=message
                )
                marked_count += 1

            return JsonResponse({
                'success': True,
                'marked_read': marked_count
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def mark_notifications_read_api(request):
    """API endpoint to mark notifications as read"""
    if request.method == 'POST':
        try:
            from .models import HardcodedNotificationManager
            import json

            data = json.loads(request.body)
            notification_ids = data.get('notification_ids', [])

            notification_manager = HardcodedNotificationManager()
            marked_count = notification_manager.mark_notifications_read(request.user, notification_ids)

            return JsonResponse({
                'success': True,
                'marked_count': marked_count
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def search_messages(request):
    """Search messages with filters"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        user_filter = request.GET.get('user', '').strip()
        date_filter = request.GET.get('date', '').strip()
        room_id = request.GET.get('room_id', '').strip()

        from rooms.models import Message
        from django.db.models import Q

        # Base queryset
        messages = Message.objects.select_related('user', 'room').order_by('-created_at')

        # Apply filters
        if query:
            messages = messages.filter(
                Q(content__icontains=query)
            )

        if user_filter:
            messages = messages.filter(user__username__icontains=user_filter)

        if date_filter:
            from datetime import datetime, timedelta
            now = timezone.now()
            if date_filter == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                messages = messages.filter(created_at__gte=start_date)
            elif date_filter == 'week':
                start_date = now - timedelta(days=7)
                messages = messages.filter(created_at__gte=start_date)
            elif date_filter == 'month':
                start_date = now - timedelta(days=30)
                messages = messages.filter(created_at__gte=start_date)

        if room_id:
            messages = messages.filter(room_id=room_id)

        # Limit results
        messages = messages[:50]

        # Format results
        results = []
        for msg in messages:
            results.append({
                'id': msg.id,
                'content': msg.content,
                'user': msg.user.username,
                'display_name': f"{msg.user.first_name} {msg.user.last_name}".strip() or msg.user.username,
                'room_name': msg.room.name,
                'room_id': msg.room.id,
                'timestamp': msg.created_at.isoformat(),
                'time_display': msg.created_at.strftime('%H:%M %d/%m/%Y')
            })

        return JsonResponse({
            'results': results,
            'total': len(results),
            'query': query
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def update_presence(request):
    """Update user presence status"""
    if request.method == 'POST':
        try:
            from .models import UserPresence
            from rooms.models import Cell

            data = json.loads(request.body)
            status = data.get('status', 'online')
            room_id = data.get('room_id')

            presence, created = UserPresence.objects.get_or_create(
                user=request.user,
                defaults={'status': status}
            )

            room = None
            if room_id:
                try:
                    room = Cell.objects.get(id=room_id, cell_type='ROOM')
                except Cell.DoesNotExist:
                    pass

            presence.update_presence(status, room)

            return JsonResponse({
                'success': True,
                'status': status,
                'room_id': room_id
            })

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def get_presence(request):
    """Get presence status for users in a room"""
    room_id = request.GET.get('room_id')
    if not room_id:
        return JsonResponse({'error': 'room_id is required'}, status=400)

    from .models import UserPresence
    from rooms.models import Cell

    try:
        cell = Cell.objects.get(id=room_id, cell_type='ROOM')

        presence_data = []
        if cell.owner:
            try:
                presence = UserPresence.objects.get(user=cell.owner)
                if presence.is_online:
                    presence_data.append({
                        'user_id': cell.owner.id,
                        'username': cell.owner.username,
                        'display_name': f"{cell.owner.first_name} {cell.owner.last_name}".strip() or cell.owner.username,
                        'status': presence.status,
                        'last_seen': presence.last_seen.isoformat()
                    })
            except UserPresence.DoesNotExist:
                pass

        return JsonResponse({
            'presence': presence_data,
            'room_id': room_id
        })

    except Cell.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def room_members_api(request, room_id):
    """API for managing room members"""
    try:
        from rooms.models import Cell

        cell = Cell.objects.get(id=room_id, cell_type='ROOM')

        if not (cell.owner_id == request.user.id or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        if request.method == 'GET':
            members_data = []
            if cell.owner:
                members_data.append({
                    'id': cell.owner.id,
                    'username': cell.owner.username,
                    'full_name': f"{cell.owner.first_name} {cell.owner.last_name}".strip(),
                    'role': 'owner',
                    'joined_at': cell.created_at.isoformat() if cell.created_at else None,
                    'last_seen': None,
                    'is_online': False
                })
            return JsonResponse({'members': members_data})

        elif request.method == 'POST':
            return JsonResponse({'error': 'Member management no longer supported after Room→Cell migration'}, status=400)

    except Cell.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@csrf_exempt
def unread_notifications_api(request):
    """API to get all unread notifications for the current user with robust caching"""
    try:
        from .models import HardcodedNotificationManager

        # Use the robust hardcoded notification manager
        result = HardcodedNotificationManager.get_notifications_data(request.user, limit=20)

        # Add cache headers for better performance
        response = JsonResponse(result)
        response['Cache-Control'] = 'private, max-age=30'  # Cache for 30 seconds
        return response

    except Exception as e:
        logger.error(f"Error in unread_notifications_api for user {request.user.username}: {str(e)}")
        return JsonResponse({'error': 'Internal server error', 'notifications': []}, status=500)

@login_required
@csrf_exempt
def test_create_notification(request):
    """Test endpoint to create a notification manually"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        from .models import HardcodedNotificationManager
        from rooms.models import Cell

        data = json.loads(request.body)
        message = data.get('message', 'Test notification')
        room_id = data.get('room_id', 1)

        # Get room
        try:
            room = Cell.objects.get(id=room_id, cell_type='ROOM')
        except Cell.DoesNotExist:
            return JsonResponse({'error': 'Room not found'}, status=404)

        # Create test notification
        notification = HardcodedNotificationManager.create_chat_notification(
            user=request.user,
            room=room,
            message=message,
            sender=request.user  # Self-notification for testing
        )

        if notification:
            return JsonResponse({
                'success': True,
                'notification': notification,
                'message': 'Test notification created'
            })
        else:
            return JsonResponse({'error': 'Failed to create notification'}, status=500)

    except Exception as e:
        logger.error(f"Error in test_create_notification: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def room_notifications_api(request, room_id):
    """API for room notifications"""
    try:
        from rooms.models import Cell

        cell = Cell.objects.get(id=room_id, cell_type='ROOM')

        if not (cell.owner_id == request.user.id or request.user.is_staff):
            return JsonResponse({'error': 'Access denied'}, status=403)

        if request.method == 'GET':
            notification_manager = HardcodedNotificationManager()
            all_notifications = notification_manager.get_all_notifications(request.user, include_read=True)

            notifications_data = [
                n for n in all_notifications
                if n.get('room_id') == str(room_id)
            ]

            return JsonResponse({'notifications': notifications_data})

        elif request.method == 'POST':
            data = json.loads(request.body)
            action = data.get('action')

            if action == 'mark_read':
                return JsonResponse({'success': True})

            elif action == 'mark_all_read':
                return JsonResponse({'success': True})

    except Cell.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def room_admin(request, room_id):
    """Room administration panel"""
    try:
        from rooms.models import Cell

        cell = Cell.objects.get(id=room_id, cell_type='ROOM')

        if not (cell.owner_id == request.user.id or request.user.is_staff):
            messages.error(request, 'You do not have permission to manage this room.')
            return redirect('chat:room', room_name=room_id)

        context = {
            'room': cell,
            'members': [cell.owner] if cell.owner else [],
            'can_manage_room': True,
            'pagetitle': f'Manage {cell.name}'
        }

        return render(request, 'chat/room_admin.html', context)

    except Cell.DoesNotExist:
        messages.error(request, 'Room not found.')
        return redirect('chat:room_list')


# APIs para gestión de conversaciones
@login_required
@csrf_exempt
def conversations_api(request):
    """API para obtener la lista de conversaciones del usuario"""
    from .models import Conversation

    conversations = Conversation.objects.filter(user=request.user).order_by('-updated_at')[:20]
    logger.info(f"Conversations API called for user {request.user.username}, found {conversations.count()} conversations")

    conversations_data = []
    for conv in conversations:
        conversations_data.append({
            'id': conv.id,
            'conversation_id': conv.conversation_id,
            'title': conv.title,
            'created_at': conv.created_at.strftime('%d/%m/%Y %H:%M'),
            'updated_at': conv.updated_at.strftime('%d/%m/%Y %H:%M'),
            'is_active': conv.is_active,
            'message_count': len(conv.messages),
            'last_message': conv.messages[-1] if conv.messages else None
        })
        logger.debug(f"Conversation {conv.id}: title='{conv.title}', active={conv.is_active}, messages={len(conv.messages)}")

    return JsonResponse({'conversations': conversations_data})


@login_required
@csrf_exempt
def switch_conversation_api(request, conversation_id):
    """API para cambiar a una conversación específica"""
    from .models import Conversation

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        conversation = Conversation.objects.get(
            conversation_id=conversation_id,
            user=request.user
        )

        # Desactivar todas las conversaciones activas
        Conversation.objects.filter(
            user=request.user,
            is_active=True
        ).exclude(id=conversation.id).update(is_active=False)

        # Activar la conversación seleccionada
        conversation.is_active = True
        conversation.save()

        return JsonResponse({
            'success': True,
            'conversation_id': conversation.conversation_id,
            'title': conversation.title
        })

    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def new_conversation_api(request):
    """API para crear una nueva conversación"""
    from .models import Conversation

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Desactivar conversación actual
        Conversation.objects.filter(
            user=request.user,
            is_active=True
        ).update(is_active=False)

        # Crear nueva conversación
        conversation_id = f"conv_{request.user.id}_{int(timezone.now().timestamp())}"
        conversation = Conversation.objects.create(
            user=request.user,
            conversation_id=conversation_id,
            title="Nueva conversación",
            is_active=True
        )

        return JsonResponse({
            'success': True,
            'conversation_id': conversation.conversation_id,
            'title': conversation.title
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def chat_stats_api(request):
    """API para obtener estadísticas del chat"""
    from rooms.models import Cell
    from .models import Conversation

    cells = Cell.objects.filter(cell_type='ROOM', is_active=True)
    total_rooms = cells.count()
    total_users = 0

    rooms_data = []
    for cell in cells:
        user_count = 1 if cell.owner_id else 0
        total_users = max(total_users, user_count)
        rooms_data.append({
            'id': cell.id,
            'users': user_count
        })

    user_conversations = Conversation.objects.filter(user=request.user).count()

    return JsonResponse({
        'total_users': total_users,
        'active_rooms': total_rooms,
        'user_conversations': user_conversations,
        'rooms': rooms_data
    })


# Public test endpoint - no authentication required
def test_page(request):
    """Página pública de prueba para verificar que el chat está operativo."""
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = True
    except Exception:
        db_ok = False
    
    return JsonResponse({
        'status': 'ok',
        'app': 'chat',
        'message': 'Management360 Chat app is running',
        'db_connected': db_ok,
        'redis_configured': bool(os.environ.get('REDIS_URL', 'redis://192.168.18.59:6379'))
    })