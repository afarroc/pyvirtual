# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from .models import Room, Comment, Evaluation, EntranceExit, Portal, RoomObject, PlayerProfile, Box
from .forms import RoomForm, EvaluationForm, EntranceExitForm, PortalForm, RoomConnectionForm, ObjectCreateForm
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from .exceptions import RoomManagerError
from django.http import Http404
from django.db.models import Q  # Import for search functionality
from django.utils import timezone
from datetime import timedelta
from .transition_manager import get_room_transition_manager

# Ensure Room refers to the model, not overridden
from .models import Room  # Ensure this import is not shadowed

@login_required
def lobby(request):
    # Secciones dinámicas
    sections = [
        {
            'title': 'Recent Rooms',
            'url_name': 'rooms:room_list',
            'detail_url_name': 'rooms:room_detail',
            'icon': 'bi-house',
            'items': Room.objects.all().order_by('-created_at')[:5]
        },
        {
            'title': 'Navigation Test Zone',
            'url_name': 'rooms:create_navigation_test_zone',
            'detail_url_name': None,
            'icon': 'bi-compass',
            'items': [],
            'description': 'Zona de pruebas con estructura jerárquica de 4 niveles para testing de navegación',
            'action_text': 'Crear/Acceder a Zona de Pruebas'
        },
        # Puedes agregar más secciones aquí si lo necesitas
    ]

    # Estadísticas rápidas
    stats = [
        {
            'title': 'Total Rooms',
            'value': Room.objects.count(),
            'icon': 'bi-house-door',
            'trend': 12,
            'trend_color': 'success',
            'period': 'This month'
        },
        # Puedes agregar más estadísticas aquí si lo necesitas
    ]

    # Filtros rápidos para la búsqueda
    quick_filters = ['Available', 'Recently Added', 'Popular']

    # Actividad reciente
    recent_activities = get_recent_activities()

    context = {
        'page_title': 'Lobby',
        'sections': sections,
        'stats': stats,
        'quick_filters': quick_filters,
        'recent_activities': recent_activities,
    }
    return render(request, 'rooms/lobby.html', context)

@login_required
def register_presence(request):
    """Registra la presencia del usuario como disponible y lo ingresa a una habitación inicial"""
    player_profile, created = PlayerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'energy': 100,
            'productivity': 50,
            'social': 50,
            'position_x': 0,
            'position_y': 0
        }
    )

    # Cambiar estado a disponible
    player_profile.state = 'AVAILABLE'
    player_profile.energy = 100  # Resetear energía al registrarse

    # Encontrar habitación inicial (primera habitación pública disponible)
    initial_room = Room.objects.filter(permissions='public').first()
    if not initial_room:
        # Si no hay habitaciones públicas, crear una habitación de lobby por defecto
        initial_room, room_created = Room.objects.get_or_create(
            name='Lobby Principal',
            defaults={
                'description': 'Habitación principal para nuevos usuarios',
                'owner': request.user,
                'permissions': 'public',
                'room_type': 'LOUNGE'
            }
        )

    player_profile.current_room = initial_room
    player_profile.save()

    messages.success(request, f'Te has registrado como disponible y entrado al {initial_room.name}')
    return redirect('rooms:room_detail', pk=initial_room.pk)

# Vista para crear una nueva sala
@login_required
def create_room(request):
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            room = form.save(commit=False)
            room.owner = request.user
            room.creator = request.user
            room.save()
            messages.success(request, 'Sala creada con éxito')
            cache.set('room_{}'.format(room.pk), room)
            return HttpResponseRedirect(reverse_lazy('lobby'))  # Redirect to the lobby
    else:
        form = RoomForm()
    context = {
        'form': form,
        'page_title': 'Crear Nueva Habitación',
        'is_edit': False
    }

    return render(request, 'rooms/room_form.html', context)

# Vista para mostrar los detalles de una sala
def room_detail(request, pk):
    try:
        logger.debug(f"Fetching details for room with ID {pk}.")
        room = get_object_or_404(Room, pk=pk)
        logger.debug(f"Room with ID {pk} found: {room.name}.")

        # Verificar consistencia de posición del jugador
        if hasattr(request.user, 'player_profile') and request.user.player_profile:
            player_profile = request.user.player_profile
            current_physical_room = player_profile.current_room

            # Si el jugador tiene una habitación física asignada y es diferente a la solicitada
            if current_physical_room and current_physical_room.id != room.id:
                # Redirigir automáticamente a la habitación física actual
                return redirect('rooms:room_detail', pk=current_physical_room.id)

        try:
            room_image_url = room.image.url if room.image and room.image.name else None
        except ValueError as e:
            logger.warning(f"Room with ID {pk} has no associated image: {str(e)}")
            room_image_url = None  # Set to None if no image is associated

        # Use a default image if no image is available
        if not room_image_url:
            room_image_url = '/static/images/default-room.jpg'  # Path to the default image

        # Debugging URL generation
        detail_url = reverse_lazy('rooms:room_detail', kwargs={'pk': pk})
        logger.debug(f"Generated URL for room_detail: {detail_url}")

        # Verificar si la sala tiene entradas/salidas y portales asociados
        entrance_exits = room.entrance_exits.all() if hasattr(room, 'entrance_exits') else []  # Manejar caso sin relación
        portals = room.portals.all() if hasattr(room, 'portals') else []  # Updated to use 'portals' attribute

        if request.method == 'POST':
            if 'create_entrance_exit' in request.POST:
                form = EntranceExitForm(request.POST)
                if form.is_valid():
                    entrance_exit = form.save(commit=False)
                    entrance_exit.room = room
                    entrance_exit.save()
                    messages.success(request, 'Entrada/Salida creada con éxito')
                    return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': pk}))
            elif 'create_portal' in request.POST:
                form = PortalForm(request.POST)
                if form.is_valid():
                    portal = form.save(commit=False)
                    portal.room = room
                    portal.save()
                    messages.success(request, 'Portal creado con éxito')
                    return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': pk}))
            elif 'enter_room' in request.POST:
                room_id = request.POST['room_id']
                return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': room_id}))

        entrance_exit_form = EntranceExitForm()
        portal_form = PortalForm()

        logger.debug("Rendering the room_detail view with the prepared context.")
        # Asegurarse de que los datos se pasen correctamente al contexto
        return render(request, 'rooms/room_detail.html', {
            'page_title': 'Room Details',
            'room': room,
            'room_image_url': room_image_url,  # Pass the image URL (default or actual)
            'entrance_exits': entrance_exits,  # Confirmar que contiene datos
            'portals': portals,  # Confirmar que contiene datos
            'entrance_exit_form': entrance_exit_form,
            'portal_form': portal_form
        })
    except Http404:
        logger.warning(f"Room with ID {pk} not found in the database.")
        return JsonResponse({'detail': 'No Room matches the given query.'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in room_detail: {str(e)}", exc_info=True)
        return JsonResponse({'detail': 'An unexpected error occurred.'}, status=500)

# Vista para renderizar habitación en 3D
def room_3d_view(request, pk):
    """
    Vista para mostrar una habitación renderizada en 3D isométrico
    """
    room = get_object_or_404(Room, pk=pk)

    # Generar SVG del renderizado 3D
    svg_content = generate_room_3d_svg(room)

    context = {
        'room': room,
        'svg_content': svg_content,
        'page_title': f'Vista 3D - {room.name}'
    }

    return render(request, 'rooms/room_3d.html', context)


@login_required
def room_3d_interactive_view(request, pk):
    """
    Vista para el entorno 3D interactivo con Three.js
    """
    room = get_object_or_404(Room, pk=pk)

    # Verificar permisos de acceso
    if room.permissions == 'private':
        if not RoomMember.objects.filter(room=room, user=request.user).exists():
            messages.error(request, 'No tienes acceso a esta habitación.')
            return redirect('rooms:room_detail', pk=pk)

    context = {
        'room': room,
        'page_title': f'Entorno 3D Interactivo - {room.name}',
        'room_id': room.id
    }

    return render(request, 'rooms/room_3d_interactive.html', context)


@login_required
def basic_3d_environment(request):
    """
    Entorno 3D básico con player interactivo en habitación 0,0,0
    Incluye puertas que conectan a habitaciones anidadas y salida a calle
    """
    # Obtener o crear habitación base en 0,0,0
    base_room, created = Room.objects.get_or_create(
        name='Habitación Base 3D',
        defaults={
            'description': 'Habitación principal en posición 0,0,0 con conexiones 3D',
            'owner': request.user,
            'creator': request.user,
            'permissions': 'public',
            'room_type': 'OFFICE',
            'x': 0, 'y': 0, 'z': 0,
            'length': 10, 'width': 10, 'height': 3,
            'color_primary': '#4CAF50',
            'color_secondary': '#2196F3'
        }
    )

    # Crear habitaciones conectadas si no existen
    connected_rooms = []

    # Habitación Norte (cocina)
    north_room, _ = Room.objects.get_or_create(
        name='Cocina',
        defaults={
            'description': 'Habitación conectada al norte',
            'owner': request.user,
            'creator': request.user,
            'permissions': 'public',
            'room_type': 'KITCHEN',
            'x': 0, 'y': 10, 'z': 0,
            'length': 8, 'width': 6, 'height': 3,
            'color_primary': '#FF9800',
            'color_secondary': '#795548'
        }
    )
    connected_rooms.append(('north', north_room))

    # Habitación Este (baño)
    east_room, _ = Room.objects.get_or_create(
        name='Baño',
        defaults={
            'description': 'Habitación conectada al este',
            'owner': request.user,
            'creator': request.user,
            'permissions': 'public',
            'room_type': 'BATHROOM',
            'x': 10, 'y': 0, 'z': 0,
            'length': 4, 'width': 6, 'height': 3,
            'color_primary': '#00BCD4',
            'color_secondary': '#607D8B'
        }
    )
    connected_rooms.append(('east', east_room))

    # Habitación Oeste (dormitorio)
    west_room, _ = Room.objects.get_or_create(
        name='Dormitorio',
        defaults={
            'description': 'Habitación conectada al oeste',
            'owner': request.user,
            'creator': request.user,
            'permissions': 'public',
            'room_type': 'SPECIAL',
            'x': -8, 'y': 0, 'z': 0,
            'length': 8, 'width': 6, 'height': 3,
            'color_primary': '#9C27B0',
            'color_secondary': '#673AB7'
        }
    )
    connected_rooms.append(('west', west_room))

    # Crear conexiones si no existen
    for direction, room in connected_rooms:
        # Crear entrada/salida en la habitación base
        entrance, _ = EntranceExit.objects.get_or_create(
            room=base_room,
            face=direction.upper(),
            defaults={
                'name': f'Puerta {direction.title()}',
                'description': f'Conecta a {room.name}',
                'enabled': True,
                'door_type': 'SINGLE',
                'material': 'WOOD',
                'color': '#8B4513'
            }
        )

        # Crear conexión
        connection, _ = RoomConnection.objects.get_or_create(
            from_room=base_room,
            to_room=room,
            entrance=entrance,
            defaults={
                'bidirectional': True,
                'energy_cost': 5
            }
        )

        # Crear entrada correspondiente en la habitación conectada
        opposite_face = {
            'north': 'south',
            'south': 'north',
            'east': 'west',
            'west': 'east'
        }[direction]

        opposite_entrance, _ = EntranceExit.objects.get_or_create(
            room=room,
            face=opposite_face.upper(),
            defaults={
                'name': f'Puerta {opposite_face.title()}',
                'description': f'Conecta desde {base_room.name}',
                'enabled': True,
                'door_type': 'SINGLE',
                'material': 'WOOD',
                'color': '#8B4513'
            }
        )

    # Crear puerta de salida a "calle/afuera"
    exit_entrance, _ = EntranceExit.objects.get_or_create(
        room=base_room,
        face='SOUTH',
        defaults={
            'name': 'Salida a Calle',
            'description': 'Puerta que da a la calle/afuera',
            'enabled': True,
            'door_type': 'DOUBLE',
            'material': 'GLASS',
            'color': '#87CEEB',
            'is_locked': False
        }
    )

    # Obtener perfil del jugador
    player_profile, _ = PlayerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'current_room': base_room,
            'energy': 100,
            'productivity': 50,
            'social': 50,
            'position_x': 5,  # Centro de la habitación
            'position_y': 5,
            'state': 'AVAILABLE'
        }
    )

    # Si el jugador no está en la habitación base, teletransportarlo
    if player_profile.current_room != base_room:
        player_profile.current_room = base_room
        player_profile.position_x = 5
        player_profile.position_y = 5
        player_profile.save()

    context = {
        'page_title': 'Entorno 3D Básico - Habitación Base',
        'base_room': base_room,
        'connected_rooms': connected_rooms,
        'player_profile': player_profile,
        'room_id': base_room.id
    }

    return render(request, 'rooms/basic_3d_environment.html', context)


# Vista para agregar comentarios a una sala
def room_comments(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        comment = request.POST['comment']
        room.comments.create(text=comment, user=request.user)
        messages.success(request, 'Comentario agregado con éxito')
        return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': pk}))
    # Asegurarse de que la plantilla 'rooms/room_comments.html' exista
    return render(request, 'rooms/room_comments.html', {'room': room})

# Vista para agregar evaluaciones a una sala
def room_evaluations(request, pk):
    room = get_object_or_404(Room, pk=pk)
    evaluation_form = EvaluationForm()
    if request.method == 'POST':
        evaluation_form = EvaluationForm(request.POST)
        if evaluation_form.is_valid():
            evaluation = evaluation_form.save(commit=False)
            evaluation.user = request.user
            evaluation.room = room
            evaluation.save()
            messages.success(request, 'Evaluación agregada con éxito')
            return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': pk}))
    # Asegurarse de que la plantilla 'rooms/room_evaluations.html' exista
    return render(request, 'rooms/room_evaluations.html', {'room': room, 'evaluation_form': evaluation_form})

# Vista para crear una nueva entrada/salida
@login_required
def create_entrance_exit(request):
    if request.method == 'POST':
        form = EntranceExitForm(request.POST)
        if form.is_valid():
            entrance_exit = form.save(commit=False)
            entrance_exit.save()
            messages.success(request, 'Entrada/Salida creada con éxito')
            return HttpResponseRedirect(reverse_lazy('entrance_exit_list'))
    else:
        form = EntranceExitForm()
    return render(request, 'create_entrance_exit.html', {'form': form})

# Vista para editar una entrada/salida existente
@login_required
def edit_entrance_exit(request, pk):
    entrance_exit = get_object_or_404(EntranceExit, pk=pk)

    # Verificar permisos - solo el owner de la habitación puede editar
    if not entrance_exit.room.can_user_manage(request.user):
        messages.error(request, 'No tienes permisos para editar esta entrada/salida.')
        return redirect('rooms:room_detail', pk=entrance_exit.room.pk)

    if request.method == 'POST':
        form = EntranceExitForm(request.POST, instance=entrance_exit)
        if form.is_valid():
            # Guardar con valores por defecto para campos faltantes
            entrance = form.save(commit=False)

            # Asegurar valores por defecto para campos requeridos que no están en el formulario
            if entrance.position_x is None:
                entrance.assign_default_position()

            # Campos con valores por defecto del modelo
            entrance.width = entrance.width or 100
            entrance.height = entrance.height or 200
            entrance.door_type = entrance.door_type or 'SINGLE'
            entrance.material = entrance.material or 'WOOD'
            entrance.color = entrance.color or '#8B4513'
            entrance.opacity = entrance.opacity or 1.0
            entrance.is_locked = entrance.is_locked or False
            entrance.auto_close = entrance.auto_close or False
            entrance.close_delay = entrance.close_delay or 5
            entrance.open_speed = entrance.open_speed or 1.0
            entrance.close_speed = entrance.close_speed or 1.0
            entrance.interaction_type = entrance.interaction_type or 'PUSH'
            entrance.animation_type = entrance.animation_type or 'SWING'
            entrance.requires_both_hands = entrance.requires_both_hands or False
            entrance.interaction_distance = entrance.interaction_distance or 150
            entrance.is_open = entrance.is_open or False
            entrance.usage_count = entrance.usage_count or 0
            entrance.health = entrance.health or 100
            entrance.access_level = entrance.access_level or 0
            entrance.security_system = entrance.security_system or 'NONE'
            entrance.alarm_triggered = entrance.alarm_triggered or False
            entrance.seals_air = entrance.seals_air or True
            entrance.seals_sound = entrance.seals_sound or 20
            entrance.temperature_resistance = entrance.temperature_resistance or 50
            entrance.pressure_resistance = entrance.pressure_resistance or 1
            entrance.energy_cost_modifier = entrance.energy_cost_modifier or 0
            entrance.experience_reward = entrance.experience_reward or 1
            entrance.special_effects = entrance.special_effects or {}
            entrance.cooldown = entrance.cooldown or 0
            entrance.max_usage_per_hour = entrance.max_usage_per_hour or 0
            entrance.glow_intensity = entrance.glow_intensity or 0
            entrance.decoration_type = entrance.decoration_type or 'NONE'

            entrance.save()
            messages.success(request, f'Entrada/Salida "{entrance.name}" actualizada exitosamente.')
            return redirect('rooms:room_detail', pk=entrance_exit.room.pk)
    else:
        form = EntranceExitForm(instance=entrance_exit)

    context = {
        'form': form,
        'entrance_exit': entrance_exit,
        'room': entrance_exit.room,
        'page_title': f'Editar Entrada/Salida - {entrance_exit.name}',
        'is_edit': True
    }

    return render(request, 'rooms/entrance_exit_form.html', context)

# Vista para eliminar una entrada/salida
@login_required
def delete_entrance_exit(request, pk):
    entrance_exit = get_object_or_404(EntranceExit, pk=pk)

    # Verificar permisos - solo el owner de la habitación puede eliminar
    if not entrance_exit.room.can_user_manage(request.user):
        messages.error(request, 'No tienes permisos para eliminar esta entrada/salida.')
        return redirect('rooms:room_detail', pk=entrance_exit.room.pk)

    # Verificar que no tenga conexiones activas
    if entrance_exit.connection:
        messages.error(request, 'No se puede eliminar una entrada/salida que tiene conexiones activas.')
        return redirect('rooms:room_detail', pk=entrance_exit.room.pk)

    if request.method == 'POST':
        room_pk = entrance_exit.room.pk
        entrance_name = entrance_exit.name
        entrance_exit.delete()
        messages.success(request, f'Entrada/Salida "{entrance_name}" eliminada exitosamente.')
        return redirect('rooms:room_detail', pk=room_pk)

    context = {
        'entrance_exit': entrance_exit,
        'room': entrance_exit.room,
        'page_title': f'Eliminar Entrada/Salida - {entrance_exit.name}'
    }

    return render(request, 'rooms/entrance_exit_confirm_delete.html', context)

# Vista para mostrar la lista de entradas/salidas
def entrance_exit_list(request):
    entrance_exits = EntranceExit.objects.all()
    return render(request, 'rooms/entrance_exit_list.html', {'entrance_exits': entrance_exits})  # Updated path

# Vista para mostrar los detalles de una entrada/salida
def entrance_exit_detail(request, pk):
    entrance_exit = get_object_or_404(EntranceExit, pk=pk)
    return render(request, 'rooms/entrance_exit_detail.html', {'entrance_exit': entrance_exit})  # Asegúrate de que esta plantilla exista

# Vista para crear un nuevo portal
@login_required
def create_portal(request):
    if request.method == 'POST':
        form = PortalForm(request.POST)
        if form.is_valid():
            portal = form.save(commit=False)
            portal.last_used = timezone.now()  # Establecer la fecha de último uso
            portal.save()
            messages.success(request, 'Portal creado con éxito')
            return HttpResponseRedirect(reverse_lazy('portal_list'))
    else:
        form = PortalForm()
    
    return render(request, 'rooms/portal_create.html', {
        'form': form,
        'page_title': 'Crear Nuevo Portal'
    })

# Vista para mostrar la lista de portales
def portal_list(request):
    portals = Portal.objects.all()
    return render(request, 'rooms/portal_list.html', {'portals': portals})

# Vista para mostrar los detalles de un portal
def portal_detail(request, pk):
    portal = get_object_or_404(Portal, pk=pk)
    return render(request, 'rooms/portal_detail.html', {'portal': portal})

# Vista para mostrar la lista de portales
def portal_list(request):
    portals = Portal.objects.all()
    return render(request, 'rooms/portal_list.html', {'portals': portals})

# Vista para mostrar los detalles de un portal
def portal_detail(request, pk):
    portal = get_object_or_404(Portal, pk=pk)
    return render(request, 'rooms/portal_detail.html', {'portal': portal})

# Vista para crear una nueva conexión de habitación
@login_required
def create_room_connection(request, room_id):
    room = get_object_or_404(Room, pk=room_id)

    # Verificar permisos
    if not room.can_user_manage(request.user):
        messages.error(request, 'No tienes permisos para gestionar conexiones en esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if request.method == 'POST':
        form = RoomConnectionForm(request.POST, room_id=room_id)
        if form.is_valid():
            connection = form.save()
            messages.success(request, f'Conexión creada exitosamente entre {connection.from_room.name} y {connection.to_room.name}')
            return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': room_id}))
    else:
        form = RoomConnectionForm(room_id=room_id)

    context = {
        'form': form,
        'room': room,
        'page_title': f'Crear Conexión - {room.name}',
        'is_create': True
    }

    return render(request, 'rooms/room_connection_form.html', context)

# Vista para editar una conexión existente
@login_required
def edit_room_connection(request, room_id, connection_id):
    room = get_object_or_404(Room, pk=room_id)
    connection = get_object_or_404(RoomConnection, pk=connection_id)

    # Verificar que la conexión pertenezca a la habitación
    if connection.from_room != room and connection.to_room != room:
        messages.error(request, 'Esta conexión no pertenece a esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    # Verificar permisos
    if not room.can_user_manage(request.user):
        messages.error(request, 'No tienes permisos para gestionar conexiones en esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if request.method == 'POST':
        form = RoomConnectionForm(request.POST, instance=connection, room_id=room_id)
        if form.is_valid():
            connection = form.save()
            messages.success(request, f'Conexión actualizada exitosamente entre {connection.from_room.name} y {connection.to_room.name}')
            return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': room_id}))
    else:
        form = RoomConnectionForm(instance=connection, room_id=room_id)

    context = {
        'form': form,
        'room': room,
        'connection': connection,
        'page_title': f'Editar Conexión - {room.name}',
        'is_create': False
    }

    return render(request, 'rooms/room_connection_form.html', context)

# Vista para eliminar una conexión
@login_required
def delete_room_connection(request, room_id, connection_id):
    room = get_object_or_404(Room, pk=room_id)
    connection = get_object_or_404(RoomConnection, pk=connection_id)

    # Verificar que la conexión pertenezca a la habitación
    if connection.from_room != room and connection.to_room != room:
        messages.error(request, 'Esta conexión no pertenece a esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    # Verificar permisos
    if not room.can_user_manage(request.user):
        messages.error(request, 'No tienes permisos para gestionar conexiones en esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if request.method == 'POST':
        from_room_name = connection.from_room.name
        to_room_name = connection.to_room.name
        connection.delete()
        messages.success(request, f'Conexión eliminada entre {from_room_name} y {to_room_name}')
        return redirect('rooms:room_detail', pk=room_id)

    context = {
        'room': room,
        'connection': connection,
        'page_title': f'Eliminar Conexión - {room.name}'
    }

    return render(request, 'rooms/room_connection_confirm_delete.html', context)

# Vista para mostrar la lista de salas
def room_list(request):
    logger.debug("Fetching all rooms from the database.")
    # Verificar si la sesión está activa
    if not request.user.is_authenticated:
        logger.warning("User not authenticated. Redirecting to login.")
        return redirect('login')    
    
    page_title = 'Lista de Salas'
    rooms = Room.objects.all()  # Obtener todas las salas desde la base de datos
    # Verificar si hay salas disponibles
    if not rooms.exists():
        logger.warning("No rooms found in the database.")
        messages.info(request, 'No hay salas disponibles en este momento.')
    else:
        logger.debug(f"Rooms count: {rooms.count()}")
        
    return render(request, 'rooms/room_list.html', {
        'page_title': page_title,
        'rooms': rooms,  # Pasar las salas al contexto
    })

@api_view(['GET'])
def room_search(request):
    query = request.GET.get('q', '')
    rooms = Room.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'rooms/room_search.html', {'rooms': rooms, 'query': query})

import json
import logging
import requests

logger = logging.getLogger(__name__)
import math
from requests.adapters import HTTPAdapter, Retry
from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .models import Message, Room, RoomMember, Outbox, CDC
from .serializers import (
    MessageSerializer, RoomSearchSerializer, RoomSerializer, RoomMemberSerializer,
    RoomCRUDSerializer, EntranceExitCRUDSerializer, PortalCRUDSerializer, RoomConnectionCRUDSerializer
)

logger = logging.getLogger(__name__)

def process_message_command(content, user):
    """Procesa comandos enviados como mensajes"""
    if not content.startswith('/'):
        return None

    command = content[1:].strip().lower().split()
    if not command:
        return None

    cmd = command[0]
    args = command[1:]

    try:
        player = user.player_profile
    except PlayerProfile.DoesNotExist:
        return "No tienes un perfil de jugador. Regístrate primero."

    if cmd == 'work':
        player.state = 'WORKING'
        player.productivity += 5
        player.energy -= 10
        player.save()
        return f"Has empezado a trabajar. Productividad: {player.productivity}, Energía: {player.energy}"

    elif cmd == 'rest':
        player.state = 'RESTING'
        player.energy = min(100, player.energy + 20)
        player.save()
        return f"Estás descansando. Energía: {player.energy}"

    elif cmd == 'social':
        player.state = 'SOCIALIZING'
        player.social += 5
        player.energy -= 5
        player.save()
        return f"Estás socializando. Social: {player.social}, Energía: {player.energy}"

    elif cmd == 'disconnect':
        player.state = 'DISCONNECTED'
        player.save()
        return "Te has desconectado."

    elif cmd == 'move' and args:
        direction = args[0].upper()
        success = player.move_to_room(direction)
        if success:
            return f"Te has movido al {direction} hacia {player.current_room.name}"
        else:
            return "No puedes moverte en esa dirección."

    elif cmd == 'status':
        return f"Estado: {player.get_state_display()}, Energía: {player.energy}, Productividad: {player.productivity}, Social: {player.social}"

    else:
        return f"Comando desconocido: {cmd}. Comandos disponibles: /work, /rest, /social, /disconnect, /move <direction>, /status"


def project_isometric(x, y, z, scale=10):
    """
    Proyecta coordenadas 3D a 2D usando proyección isométrica (perspectiva caballero)
    """
    # Ángulos isométricos: 30 grados
    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))

    # Proyección isométrica
    screen_x = (x - y) * cos30 * scale
    screen_y = ((x + y) * sin30 - z) * scale

    return screen_x, screen_y


def generate_room_3d_svg(room, canvas_width=800, canvas_height=600):
    """
    Genera SVG para renderizar una habitación en 3D isométrico
    """
    scale = 8  # Escala para ajustar el tamaño

    # Calcular el centro del canvas
    center_x = canvas_width // 2
    center_y = canvas_height // 2

    # Proyectar los 8 vértices del cuboide
    vertices = []
    for dx in [0, room.length]:
        for dy in [0, room.width]:
            for dz in [0, room.height]:
                x, y = project_isometric(dx, dy, dz, scale)
                vertices.append((x, y))

    # Ajustar posición al centro del canvas
    min_x = min(v[0] for v in vertices)
    max_x = max(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)

    offset_x = center_x - (min_x + max_x) // 2
    offset_y = center_y - (min_y + max_y) // 2

    # Aplicar offset
    vertices = [(x + offset_x, y + offset_y) for x, y in vertices]

    # Definir las caras del cuboide (índices de vértices)
    faces = [
        # Frente (z=0)
        [0, 1, 3, 2],
        # Derecha (y=width)
        [1, 5, 7, 3],
        # Atrás (x=length)
        [4, 5, 7, 6],
        # Izquierda (y=0)
        [0, 2, 6, 4],
        # Superior (z=height)
        [2, 3, 7, 6],
        # Inferior (z=0, pero desde arriba)
        [0, 1, 5, 4]
    ]

    # Usar colores del objeto habitación con variaciones para cada cara
    base_color = room.color_primary
    accent_color = room.color_secondary

    # Crear variaciones de color para diferentes caras
    colors = [
        base_color,  # Frente
        accent_color,  # Derecha
        base_color,  # Atrás
        accent_color,  # Izquierda
        base_color,  # Superior
        accent_color,  # Inferior
    ]

    svg_parts = []
    svg_parts.append(f'<svg width="{canvas_width}" height="{canvas_height}" xmlns="http://www.w3.org/2000/svg">')

    # Dibujar fondo
    svg_parts.append(f'<rect width="100%" height="100%" fill="#f5f5f5"/>')

    # Dibujar caras (ordenadas por profundidad para efecto 3D)
    for i, face_indices in enumerate(faces):
        points = []
        for idx in face_indices:
            vx, vy = vertices[idx]
            points.append(f"{vx},{vy}")
        points_str = " ".join(points)

        svg_parts.append(f'<polygon points="{points_str}" fill="{colors[i]}" stroke="#1976d2" stroke-width="1"/>')

    # Dibujar aristas
    edges = [
        (0, 1), (1, 3), (3, 2), (2, 0),  # Base inferior
        (4, 5), (5, 7), (7, 6), (6, 4),  # Base superior
        (0, 4), (1, 5), (2, 6), (3, 7)   # Aristas verticales
    ]

    for edge in edges:
        x1, y1 = vertices[edge[0]]
        x2, y2 = vertices[edge[1]]
        svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0d47a1" stroke-width="2"/>')

    # Agregar texto con información de la habitación
    svg_parts.append(f'<text x="20" y="30" font-family="Arial" font-size="16" fill="#000">Habitación: {room.name}</text>')
    svg_parts.append(f'<text x="20" y="50" font-family="Arial" font-size="12" fill="#666">Dimensiones: {room.length}×{room.width}×{room.height}</text>')
    svg_parts.append(f'<text x="20" y="70" font-family="Arial" font-size="12" fill="#666">Posición: ({room.x}, {room.y}, {room.z})</text>')

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)

class RoomListViewSet(ListModelMixin, GenericViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.user.pk
        logger.debug(f"Fetching rooms for user_id: {user_id}")
        queryset = Room.objects.annotate(
            member_count=Count('members__id')  # Changed from 'memberships__id' to 'members__id'
        ).filter(
            members__id=user_id  # Changed from 'memberships__user_id' to 'members__id'
        ).select_related('last_message', 'last_message__user').order_by('-bumped_at')
        logger.debug(f"Queryset: {queryset.query}")
        return queryset


class RoomDetailViewSet(RetrieveModelMixin, GenericViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Room.objects.annotate(
            member_count=Count('members')  # Changed from 'memberships' to 'members'
        ).filter(members__id=self.request.user.pk)  # Changed from 'memberships__user_id' to 'members__id'


class RoomSearchViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSearchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_membership = RoomMember.objects.filter(
            room=OuterRef('pk'),
            user=user
        )
        return Room.objects.annotate(
            is_member=Exists(user_membership)
        ).order_by('name')


class CentrifugoMixin:
    # A helper method to return the list of channels for all current members of specific room.
    # So that the change in the room may be broadcasted to all the members.
    def get_room_member_channels(self, room_id):
        members = RoomMember.objects.filter(room_id=room_id).values_list('user', flat=True)
        return [f'personal:{user_id}' for user_id in members]

    def broadcast_room(self, room_id, broadcast_payload):
        # Using Centrifugo HTTP API is the simplest way to send real-time message, and usually
        # it provides the best latency. The trade-off here is that error here may result in
        # lost real-time event. Depending on the application requirements this may be fine or not.  
        def broadcast():
            session = requests.Session()
            retries = Retry(total=1, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
            session.mount('http://', HTTPAdapter(max_retries=retries))
            try:
                session.post(
                    settings.CENTRIFUGO_HTTP_API_ENDPOINT + '/api/broadcast',
                    data=json.dumps(broadcast_payload),
                    headers={
                        'Content-type': 'application/json', 
                        'X-API-Key': settings.CENTRIFUGO_HTTP_API_KEY,
                        'X-Centrifugo-Error-Mode': 'transport'
                    }
                )
            except requests.exceptions.RequestException as e:
                logging.error(e)

        if settings.CENTRIFUGO_BROADCAST_MODE == 'api':
            # We need to use on_commit here to not send notification to Centrifugo before
            # changes applied to the database. Since we are inside transaction.atomic block
            # broadcast will happen only after successful transaction commit.
            transaction.on_commit(broadcast)

        elif settings.CENTRIFUGO_BROADCAST_MODE == 'outbox':
            # In outbox case we can set partition for parallel processing, but
            # it must be in predefined range and match Centrifugo PostgreSQL
            # consumer configuration.
            partition = hash(room_id)%settings.CENTRIFUGU_OUTBOX_PARTITIONS
            # Creating outbox object inside transaction will guarantee that Centrifugo will
            # process the command at some point. In normal conditions – almost instantly.
            Outbox.objects.create(method='broadcast', payload=broadcast_payload, partition=partition)

        elif settings.CENTRIFUGO_BROADCAST_MODE == 'cdc':
            # In cdc case Debezium will use this field for setting Kafka partition.
            # We should not prepare proper partition ourselves in this case.
            partition = hash(room_id)
            # Creating outbox object inside transaction will guarantee that Centrifugo will
            # process the command at some point. In normal conditions – almost instantly. In this
            # app Debezium will perform CDC and send outbox events to Kafka, event will be then
            # consumed by Centrifugo. The advantages here is that Debezium reads WAL changes and
            # has a negligible overhead on database performance. And most efficient partitioning.
            # The trade-off is that more hops add more real-time event delivery latency. May be
            # still instant enough though.
            CDC.objects.create(method='broadcast', payload=broadcast_payload, partition=partition)

        elif settings.CENTRIFUGO_BROADCAST_MODE == 'api_cdc':
            if len(broadcast_payload['channels']) <= 1000000:
                # We only use low-latency broadcast over API for not too big rooms, it's possible
                # to adjust as required of course.
                transaction.on_commit(broadcast)

            partition = hash(room_id)
            CDC.objects.create(method='broadcast', payload=broadcast_payload, partition=partition)

        else:
            raise ValueError(f'unknown CENTRIFUGO_BROADCAST_MODE: {settings.CENTRIFUGO_BROADCAST_MODE}')


class MessageListCreateAPIView(ListCreateAPIView, CentrifugoMixin):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        get_object_or_404(RoomMember, user=self.request.user, room_id=room_id)
        return Message.objects.filter(
            room_id=room_id).prefetch_related('user', 'room').order_by('-created_at')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        room_id = self.kwargs['room_id']
        room = Room.objects.select_for_update().get(id=room_id)
        room.increment_version()
        channels = self.get_room_member_channels(room_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(room=room, user=request.user)
        room.last_message = obj
        room.bumped_at = timezone.now()
        room.save()

        # Procesar comandos si el mensaje es un comando
        command_response = process_message_command(obj.content, request.user)
        if command_response:
            # Crear mensaje de sistema con la respuesta del comando
            system_message = Message.objects.create(
                room=room,
                content=command_response,
                message_type='system'
            )
            room.last_message = system_message
            room.save()

            # Broadcast del mensaje de comando
            broadcast_payload = {
                'channels': channels,
                'data': {
                    'type': 'message_added',
                    'body': MessageSerializer(system_message).data
                },
                'idempotency_key': f'message_{system_message.id}'
            }
            self.broadcast_room(room_id, broadcast_payload)

        # Broadcast del mensaje original
        broadcast_payload = {
            'channels': channels,
            'data': {
                'type': 'message_added',
                'body': serializer.data
            },
            'idempotency_key': f'message_{serializer.data["id"]}'
        }
        self.broadcast_room(room_id, broadcast_payload)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class JoinRoomView(APIView, CentrifugoMixin):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, room_id):
        room = Room.objects.select_for_update().get(id=room_id)
        room.increment_version()
        if RoomMember.objects.filter(user=request.user, room=room).exists():
            return Response({"message": "already a member"}, status=status.HTTP_409_CONFLICT)
        obj, _ = RoomMember.objects.get_or_create(user=request.user, room=room)
        channels = self.get_room_member_channels(room_id)
        obj.room.member_count = len(channels)
        body = RoomMemberSerializer(obj).data

        broadcast_payload = {
            'channels': channels,
            'data': {
                'type': 'user_joined',
                'body': body
            },
            'idempotency_key': f'user_joined_{obj.pk}'
        }
        self.broadcast_room(room_id, broadcast_payload)
        return Response(body, status=status.HTTP_200_OK)


class LeaveRoomView(APIView, CentrifugoMixin):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, room_id):
        room = Room.objects.select_for_update().get(id=room_id)
        room.increment_version()
        channels = self.get_room_member_channels(room_id)
        obj = get_object_or_404(RoomMember, user=request.user, room=room)
        obj.room.member_count = len(channels) - 1
        pk = obj.pk
        obj.delete()
        body = RoomMemberSerializer(obj).data

        broadcast_payload = {
            'channels': channels,
            'data': {
                'type': 'user_left',
                'body': body
            },
            'idempotency_key': f'user_left_{pk}'
        }
        self.broadcast_room(room_id, broadcast_payload)
        return Response(body, status=status.HTTP_200_OK)
    
@api_view(['POST'])
def player_move(request, direction):
    player = request.user.player_profile
    success = player.move_to_room(direction)
    return Response({"success": success, "current_room": player.current_room.name})

@api_view(['POST'])
def interact_with_object(request, object_id):
    obj = get_object_or_404(RoomObject, pk=object_id)
    result = obj.interact(request.user.player_profile)
    return Response(result)

@api_view(['POST'])
def use_entrance_exit(request, entrance_id):
    """
    API endpoint para usar una EntranceExit (puerta).
    Implementa la arquitectura de separación de responsabilidades.
    """
    try:
        # Obtener la puerta
        entrance = get_object_or_404(EntranceExit, pk=entrance_id)

        # Verificar que el usuario tenga un perfil de jugador
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile

        # Usar el RoomTransitionManager para manejar la transición
        transition_manager = get_room_transition_manager()
        result = transition_manager.attempt_transition(player_profile, entrance)

        if result['success']:
            return Response({
                'success': True,
                'message': result['message'],
                'target_room': {
                    'id': result['target_room'].id,
                    'name': result['target_room'].name,
                    'description': result['target_room'].description
                },
                'energy_cost': result['energy_cost'],
                'experience_gained': result.get('experience_gained', 0),
                'player_stats': {
                    'energy': player_profile.energy,
                    'productivity': player_profile.productivity,
                    'position_x': player_profile.position_x,
                    'position_y': player_profile.position_y
                }
            })
        else:
            return Response({
                'success': False,
                'message': result['message'],
                'reason': result.get('reason', 'UNKNOWN')
            }, status=400)

    except Exception as e:
        logger.error(f"Error en use_entrance_exit: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)

@api_view(['GET'])
def get_entrance_info(request, entrance_id):
    """
    API endpoint para obtener información detallada de una EntranceExit.
    """
    try:
        entrance = get_object_or_404(EntranceExit, pk=entrance_id)

        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile
        transition_info = entrance.get_transition_info(player_profile)
        usage_stats = entrance.get_usage_statistics()

        return Response({
            'success': True,
            'entrance': {
                'id': entrance.id,
                'name': entrance.name,
                'description': entrance.description,
                'face': entrance.face,
                'enabled': entrance.enabled,
                'is_locked': entrance.is_locked,
                'door_type': entrance.door_type,
                'material': entrance.material,
                'width': entrance.width,
                'height': entrance.height,
                'access_level': entrance.access_level,
                'interaction_type': entrance.interaction_type,
                'health': entrance.health
            },
            'transition_info': {
                'can_use': transition_info['can_use'],
                'reason': transition_info['reason'],
                'energy_cost': transition_info['energy_cost'],
                'experience_reward': transition_info['experience_reward'],
                'target_room': {
                    'id': transition_info['target_room'].id,
                    'name': transition_info['target_room'].name,
                    'description': transition_info['target_room'].description
                } if transition_info['target_room'] else None
            },
            'usage_stats': usage_stats,
            'connection': {
                'exists': entrance.connection is not None,
                'bidirectional': entrance.connection.bidirectional if entrance.connection else False,
                'energy_cost': entrance.connection.energy_cost if entrance.connection else 0
            } if entrance.connection else None
        })

    except Exception as e:
        logger.error(f"Error en get_entrance_info: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)

@api_view(['GET'])
def get_available_transitions(request):
    """
    API endpoint para obtener todas las transiciones disponibles para el jugador actual.
    """
    try:
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile
        transition_manager = get_room_transition_manager()
        available_transitions = transition_manager.get_available_transitions(player_profile)

        transitions_data = []
        for transition in available_transitions:
            transitions_data.append({
                'entrance': {
                    'id': transition['entrance'].id,
                    'name': transition['entrance'].name,
                    'face': transition['entrance'].face,
                    'door_type': transition['entrance'].door_type,
                    'material': transition['entrance'].material
                },
                'target_room': {
                    'id': transition['target_room'].id,
                    'name': transition['target_room'].name,
                    'description': transition['target_room'].description
                } if transition['target_room'] else None,
                'energy_cost': transition['energy_cost'],
                'experience_reward': transition['experience_reward'],
                'accessible': transition['accessible'],
                'reason': transition.get('reason', '')
            })

        return Response({
            'success': True,
            'current_room': {
                'id': player_profile.current_room.id if player_profile.current_room else None,
                'name': player_profile.current_room.name if player_profile.current_room else None
            },
            'available_transitions': transitions_data,
            'player_energy': player_profile.energy
        })

    except Exception as e:
        logger.error(f"Error en get_available_transitions: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)

@api_view(['POST'])
def teleport_to_room(request, room_id):
    """
    API endpoint para teletransportarse a una habitación específica.
    """
    try:
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile

        # Get target room
        try:
            target_room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Habitación no encontrada.'
            }, status=404)

        # Check if it's just a check request
        check_only = request.data.get('check_only', False)
        if check_only:
            can_teleport, reason = player_profile.can_teleport_to(target_room)
            return Response({
                'success': can_teleport,
                'message': reason,
                'energy_cost': 20,
                'current_energy': player_profile.energy
            })

        # Attempt teleportation
        success, message = player_profile.teleport_to(target_room)

        if success:
            return Response({
                'success': True,
                'message': message,
                'target_room': {
                    'id': target_room.id,
                    'name': target_room.name,
                    'description': target_room.description
                },
                'energy_cost': 20,
                'remaining_energy': player_profile.energy
            })
        else:
            return Response({
                'success': False,
                'message': message
            }, status=400)

    except Exception as e:
        logger.error(f"Error en teleport_to_room: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)

@api_view(['GET'])
def get_navigation_history(request):
    """
    API endpoint para obtener el historial de navegación del jugador.
    """
    try:
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile

        # Convert room IDs to room data
        history_data = []
        for room_id in (player_profile.navigation_history or []):
            try:
                room = Room.objects.get(id=room_id)
                history_data.append({
                    'id': room.id,
                    'name': room.name,
                    'description': room.description[:50] + '...' if len(room.description) > 50 else room.description
                })
            except Room.DoesNotExist:
                continue

        return Response({
            'success': True,
            'navigation_history': history_data,
            'current_room': {
                'id': player_profile.current_room.id if player_profile.current_room else None,
                'name': player_profile.current_room.name if player_profile.current_room else None
            }
        })

    except Exception as e:
        logger.error(f"Error en get_navigation_history: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)

@api_view(['GET'])
def get_user_current_room(request):
    """
    API endpoint para obtener la habitación actual física del usuario.
    """
    try:
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile

        if not player_profile.current_room:
            return Response({
                'success': False,
                'message': 'No estás en ninguna habitación actualmente.'
            }, status=400)

        return Response({
            'success': True,
            'current_room': {
                'id': player_profile.current_room.id,
                'name': player_profile.current_room.name,
                'description': player_profile.current_room.description,
                'room_type': player_profile.current_room.room_type,
                'permissions': player_profile.current_room.permissions
            },
            'player_stats': {
                'energy': player_profile.energy,
                'productivity': player_profile.productivity,
                'social': player_profile.social,
                'position_x': player_profile.position_x,
                'position_y': player_profile.position_y
            }
        })

    except Exception as e:
        logger.error(f"Error en get_user_current_room: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)

@api_view(['GET'])
def room_detail_view(request, pk):
    """
    API view to retrieve details of a specific room.
    """
    try:
        room = get_object_or_404(Room, pk=pk)
        data = {
            'id': room.id,
            'name': room.name,
            'description': room.description,
            'created_at': room.created_at,
            'updated_at': room.updated_at,
        }
        return JsonResponse(data, status=200)
    except Http404:
        logger.warning(f"Room with ID {pk} not found.")
        return JsonResponse({'detail': 'No Room matches the given query.'}, status=404)

def get_recent_activities(limit=5):
    """
    Get recent activities across the system.
    Returns a list of activity dictionaries with user, action, timestamp, icon, and color.
    """
    activities = []
    now = timezone.now()
    past_24h = now - timedelta(hours=24)

    # Get recent room creations
    recent_rooms = Room.objects.filter(
        created_at__gte=past_24h
    ).select_related('creator')[:limit]

    for room in recent_rooms:
        if room.creator:  # Check if creator exists
            activities.append({
                'user': room.creator.username,
                'action': f'created room "{room.name}"',
                'timestamp': room.created_at,
                'icon': 'bi-house-add',
                'color': 'success'
            })

    # Only add portal activities if Portal has created_at field
    if hasattr(Portal, 'created_at'):
        recent_portals = Portal.objects.filter(
            created_at__gte=past_24h
        ).select_related('room')[:limit]

        for portal in recent_portals:
            # Defensive: check if portal.room and portal.room.creator exist
            user = getattr(getattr(portal.room, 'creator', None), 'username', None)
            if user:
                activities.append({
                    'user': user,
                    'action': f'created portal in {portal.room.name}',
                    'timestamp': portal.created_at,
                    'icon': 'bi-door-open',
                    'color': 'info'
                })

    # Sort all activities by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:limit]
    
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import PlayerProfile, Room, EntranceExit, RoomConnection
from django.http import JsonResponse

@login_required
def navigate_room(request, direction):
    """
    Vista para manejar la navegación entre habitaciones
    """
    player = request.user.player_profile
    
    if not player.current_room:
        return JsonResponse({
            'success': False,
            'message': 'No estás en ninguna habitación actualmente'
        }, status=400)
    
    # Intentar mover al jugador
    success = player.move_to_room(direction)
    
    if success:
        new_room = player.current_room
        entrance = new_room.entrance_exits.filter(face=direction.opposite()).first()
        
        # Obtener información de la nueva habitación
        room_info = {
            'id': new_room.id,
            'name': new_room.name,
            'description': new_room.description,
            'image_url': new_room.get_image_url() or '/static/images/default-room.jpg',
            'connections': get_available_exits(new_room),
            'objects': list(new_room.room_objects.values('id', 'name', 'object_type', 'position_x', 'position_y')),
            'entrance_position': {
                'x': entrance.position_x if entrance else new_room.length // 2,
                'y': entrance.position_y if entrance else new_room.width // 2
            } if entrance else None
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Te has movido a {new_room.name}',
            'room': room_info
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'No hay conexión disponible en esa dirección'
        }, status=400)

def get_available_exits(room):
    """
    Obtiene las salidas disponibles de una habitación
    """
    exits = []
    for entrance in room.entrance_exits.filter(enabled=True):
        if entrance.connection:
            exits.append({
                'direction': entrance.face,
                'to_room': entrance.connection.to_room.name,
                'to_room_id': entrance.connection.to_room.id,
                'energy_cost': entrance.connection.energy_cost
            })
    return exits

@login_required
def room_view(request, room_id=None):
    """Vista principal para mostrar una habitación"""
    player = request.user.player_profile
    
    # Si no se especifica room_id, usar la actual
    room = player.current_room if room_id is None else get_object_or_404(Room, id=room_id)
    
    # Actualizar habitación del jugador si es diferente
    if player.current_room != room:
        player.current_room = room
        player.save()
    
    return JsonResponse({
        'room': {
            'id': room.id,
            'name': room.name,
            'description': room.description,
            'image_url': room.get_image_url() or '/static/default-room.jpg'
        },
        'exits': player.get_available_exits(),
        'player': {
            'energy': player.energy,
            'position': [player.position_x, player.position_y]
        }
    })

@login_required
def navigate(request):
    """Maneja la navegación entre habitaciones"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    player = request.user.player_profile
    exit_type = request.POST.get('exit_type')
    exit_id = request.POST.get('exit_id')
    
    if not exit_type or not exit_id:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)
    
    if player.use_exit(exit_type, exit_id):
        return JsonResponse({
            'success': True,
            'new_room': {
                'id': player.current_room.id,
                'name': player.current_room.name
            },
            'energy': player.energy,
            'position': [player.position_x, player.position_y]
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'No se puede usar esta salida'
        }, status=400)

@login_required
def room_delete(request, pk):
    """Vista para eliminar una habitación"""
    room = get_object_or_404(Room, pk=pk)

    # Verificar permisos
    if not room.can_user_manage(request.user):
        messages.error(request, 'No tienes permisos para eliminar esta habitación.')
        return redirect('rooms:room_detail', pk=pk)

    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f'La habitación "{room_name}" ha sido eliminada exitosamente.')
        return redirect('rooms:room_list')

    # Si es GET, mostrar confirmación
    return render(request, 'rooms/room_confirm_delete.html', {'room': room})

@login_required
def create_room_complete(request):
    """Vista para crear una habitación completa con todas las opciones"""
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            room = form.save(commit=False)
            room.owner = request.user
            room.creator = request.user
            room.save()
            messages.success(request, f'Habitación "{room.name}" creada exitosamente.')
            return redirect('rooms:room_detail', pk=room.pk)
    else:
        form = RoomForm(user=request.user)

    context = {
        'form': form,
        'page_title': 'Crear Habitación Completa',
        'is_edit': False,
        'room_count': Room.objects.count(),
        'active_rooms': Room.objects.filter(is_active=True).count()
    }

    return render(request, 'rooms/room_form_complete.html', context)


# API CRUD Views for Rooms
class RoomCRUDViewSet(ModelViewSet):
    """
    API endpoint completo para operaciones CRUD en habitaciones.
    Proporciona: list, create, retrieve, update, partial_update, destroy
    """
    serializer_class = RoomCRUDSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar habitaciones según permisos del usuario.
        - Owner puede ver todas sus habitaciones
        - Admin puede ver habitaciones administradas
        - Miembros pueden ver habitaciones donde son miembros
        """
        user = self.request.user
        return Room.objects.filter(
            Q(owner=user) |
            Q(administrators=user) |
            Q(members__user=user)
        ).distinct().order_by('-updated_at')

    def perform_create(self, serializer):
        """Asignar el owner y creator al crear una habitación"""
        serializer.save(owner=self.request.user, creator=self.request.user)

    def update(self, request, *args, **kwargs):
        """Actualización completa con validación de permisos"""
        instance = self.get_object()

        # Verificar permisos
        if not instance.can_user_manage(request.user):
            return Response(
                {"error": "No tienes permisos para editar esta habitación"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial con validación de permisos"""
        instance = self.get_object()

        # Verificar permisos
        if not instance.can_user_manage(request.user):
            return Response(
                {"error": "No tienes permisos para editar esta habitación"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Eliminación con validación de permisos"""
        instance = self.get_object()

        # Verificar permisos
        if not instance.can_user_manage(request.user):
            return Response(
                {"error": "No tienes permisos para eliminar esta habitación"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)


# API CRUD Views for EntranceExit (Doors)
class EntranceExitCRUDViewSet(ModelViewSet):
    """
    API endpoint completo para operaciones CRUD de EntranceExit (puertas).
    Proporciona: list, create, retrieve, update, partial_update, destroy
    """
    serializer_class = EntranceExitCRUDSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar puertas por habitaciones del usuario"""
        user = self.request.user
        return EntranceExit.objects.filter(
            room__owner=user
        ).select_related('room', 'connection').order_by('-created_at')

    def perform_create(self, serializer):
        """Crear puerta con validaciones adicionales"""
        serializer.save()


# API CRUD Views for Portal
class PortalCRUDViewSet(ModelViewSet):
    """
    API endpoint completo para operaciones CRUD de Portal.
    Proporciona: list, create, retrieve, update, partial_update, destroy
    """
    serializer_class = PortalCRUDSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar portales por habitaciones del usuario"""
        user = self.request.user
        return Portal.objects.filter(
            Q(entrance__room__owner=user) | Q(exit__room__owner=user)
        ).select_related('entrance__room', 'exit__room').distinct().order_by('-created_at')

    def perform_create(self, serializer):
        """Crear portal con validaciones adicionales"""
        serializer.save()


# API CRUD Views for RoomConnection
class RoomConnectionCRUDViewSet(ModelViewSet):
    """
    API endpoint completo para operaciones CRUD de RoomConnection.
    Proporciona: list, create, retrieve, update, partial_update, destroy
    """
    serializer_class = RoomConnectionCRUDSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar conexiones por habitaciones del usuario"""
        user = self.request.user
        return RoomConnection.objects.filter(
            Q(from_room__owner=user) | Q(to_room__owner=user)
        ).select_related('from_room', 'to_room', 'entrance').distinct().order_by('-created_at')

    def perform_create(self, serializer):
        """Crear conexión con validaciones adicionales"""
        serializer.save()


# Frontend CRUD View
@login_required
def room_crud_view(request):
    """
    Vista para el frontend moderno de gestión CRUD de habitaciones.
    """
    return render(request, 'rooms/room_crud.html', {
        'page_title': 'Gestión de Habitaciones',
    })


# ===== API ENDPOINTS PARA ENTORNO 3D =====

@api_view(['GET'])
def get_room_3d_data(request, room_id):
    """
    API endpoint para obtener datos 3D completos de una habitación.
    Incluye geometría, objetos, conexiones y estado del player.
    """
    try:
        room = get_object_or_404(Room, pk=room_id)

        # Verificar permisos de acceso
        if room.permissions == 'private':
            # Solo miembros pueden acceder a habitaciones privadas
            if not RoomMember.objects.filter(room=room, user=request.user).exists():
                return Response({
                    'success': False,
                    'message': 'No tienes acceso a esta habitación.'
                }, status=403)

        # Obtener perfil del jugador
        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        # Datos básicos de la habitación
        room_data = {
            'id': room.id,
            'name': room.name,
            'description': room.description,
            'dimensions': {
                'length': room.length,
                'width': room.width,
                'height': room.height
            },
            'position': {
                'x': room.x,
                'y': room.y,
                'z': room.z
            },
            'colors': {
                'primary': room.color_primary,
                'secondary': room.color_secondary
            },
            'material': room.material_type,
            'lighting_intensity': room.lighting_intensity,
            'temperature': float(room.temperature)
        }

        # Estado del jugador
        player_data = {
            'position': {
                'x': player_profile.position_x or room.length // 2,
                'y': player_profile.position_y or room.width // 2,
                'z': 1.7  # Altura típica de una persona
            },
            'energy': player_profile.energy,
            'productivity': player_profile.productivity,
            'social': player_profile.social
        }

        # Obtener objetos 3D (puertas y portales)
        objects_3d = []

        # Puertas (EntranceExit)
        for entrance in room.entrance_exits.filter(enabled=True):
            obj_data = {
                'type': 'door',
                'id': entrance.id,
                'name': entrance.name,
                'position': {
                    'x': entrance.position_x or 0,
                    'y': entrance.position_y or 0,
                    'z': 0
                },
                'dimensions': {
                    'width': entrance.width / 100,  # Convertir cm a metros
                    'height': entrance.height / 100,
                    'depth': 0.2
                },
                'properties': {
                    'face': entrance.face,
                    'is_locked': entrance.is_locked,
                    'door_type': entrance.door_type,
                    'material': entrance.material,
                    'color': entrance.color,
                    'interaction_distance': entrance.interaction_distance / 100  # Convertir cm a metros
                }
            }

            # Agregar información de conexión si existe
            if entrance.connection:
                obj_data['connection'] = {
                    'target_room_id': entrance.connection.to_room.id if entrance.connection.from_room == room else entrance.connection.from_room.id,
                    'energy_cost': entrance.connection.energy_cost,
                    'bidirectional': entrance.connection.bidirectional
                }

            objects_3d.append(obj_data)

        # Portales
        for portal in room.portals.all():
            # Determinar si este portal sale de esta habitación
            if portal.entrance.room == room:
                portal_exit = portal.exit
                target_room = portal_exit.room
            else:
                portal_exit = portal.entrance
                target_room = portal.entrance.room

            obj_data = {
                'type': 'portal',
                'id': portal.id,
                'name': portal.name,
                'position': {
                    'x': portal_exit.position_x or 0,
                    'y': portal_exit.position_y or 0,
                    'z': room.height // 2  # Centro vertical de la habitación
                },
                'dimensions': {
                    'width': 2,
                    'height': 3,
                    'depth': 0.1
                },
                'properties': {
                    'energy_cost': portal.energy_cost,
                    'cooldown': portal.cooldown,
                    'is_active': portal.is_active(),
                    'target_room_id': target_room.id
                }
            }
            objects_3d.append(obj_data)

        # Obtener conexiones disponibles
        connections = []
        for entrance in room.entrance_exits.filter(enabled=True, connection__isnull=False):
            connection = entrance.connection
            target_room = connection.to_room if connection.from_room == room else connection.from_room

            connections.append({
                'direction': entrance.face,
                'target_room_id': target_room.id,
                'target_room_name': target_room.name,
                'energy_cost': connection.energy_cost,
                'entrance_id': entrance.id
            })

        # Datos de respuesta
        response_data = {
            'success': True,
            'room': room_data,
            'player': player_data,
            'objects': objects_3d,
            'connections': connections,
            'portals': [obj for obj in objects_3d if obj['type'] == 'portal']
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"Error en get_room_3d_data: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)


@api_view(['POST'])
def room_transition(request):
    """
    API endpoint para manejar transiciones entre habitaciones.
    Actualiza la posición del player y cambia de habitación.
    """
    try:
        # Validar datos de entrada
        exit_type = request.data.get('exit_type')  # 'door' o 'portal'
        exit_id = request.data.get('exit_id')
        target_room_id = request.data.get('target_room_id')

        if not exit_type or not exit_id:
            return Response({
                'success': False,
                'message': 'Faltan parámetros: exit_type y exit_id son requeridos.'
            }, status=400)

        # Obtener perfil del jugador
        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        # Procesar transición según el tipo
        if exit_type == 'door':
            entrance = get_object_or_404(EntranceExit, pk=exit_id)

            # Usar el RoomTransitionManager existente
            transition_manager = get_room_transition_manager()
            result = transition_manager.attempt_transition(player_profile, entrance)

            if result['success']:
                # Obtener datos de la nueva habitación
                new_room = result['target_room']
                new_room_data = {
                    'id': new_room.id,
                    'name': new_room.name,
                    'description': new_room.description
                }

                return Response({
                    'success': True,
                    'message': result['message'],
                    'target_room': new_room_data,
                    'energy_cost': result['energy_cost'],
                    'player_stats': {
                        'energy': player_profile.energy,
                        'position_x': player_profile.position_x,
                        'position_y': player_profile.position_y
                    }
                })
            else:
                return Response({
                    'success': False,
                    'message': result['message']
                }, status=400)

        elif exit_type == 'portal':
            portal = get_object_or_404(Portal, pk=exit_id)

            # Verificar si el portal está activo
            if not portal.is_active():
                return Response({
                    'success': False,
                    'message': 'El portal no está disponible actualmente.'
                }, status=400)

            # Verificar energía suficiente
            if player_profile.energy < portal.energy_cost:
                return Response({
                    'success': False,
                    'message': f'Energía insuficiente. Necesitas {portal.energy_cost}, tienes {player_profile.energy}.'
                }, status=400)

            # Determinar habitación destino
            if portal.entrance.room == player_profile.current_room:
                target_room = portal.exit.room
                exit_entrance = portal.exit
            else:
                target_room = portal.entrance.room
                exit_entrance = portal.entrance

            # Realizar transición
            player_profile.add_to_navigation_history(player_profile.current_room.id)
            player_profile.current_room = target_room
            player_profile.position_x = exit_entrance.position_x or target_room.length // 2
            player_profile.position_y = exit_entrance.position_y or target_room.width // 2
            player_profile.energy -= portal.energy_cost
            player_profile.save()

            # Actualizar último uso del portal
            portal.last_used = timezone.now()
            portal.save()

            return Response({
                'success': True,
                'message': f'Teletransportado a {target_room.name} a través del portal.',
                'target_room': {
                    'id': target_room.id,
                    'name': target_room.name,
                    'description': target_room.description
                },
                'energy_cost': portal.energy_cost,
                'player_stats': {
                    'energy': player_profile.energy,
                    'position_x': player_profile.position_x,
                    'position_y': player_profile.position_y
                }
            })

        else:
            return Response({
                'success': False,
                'message': f'Tipo de salida no válido: {exit_type}'
            }, status=400)

    except Exception as e:
        logger.error(f"Error en room_transition: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)


@api_view(['POST'])
def update_player_position(request):
    """
    API endpoint para actualizar la posición del player en 3D.
    """
    try:
        # Validar datos de entrada
        position_x = request.data.get('position_x')
        position_y = request.data.get('position_y')
        position_z = request.data.get('position_z', 1.7)  # Altura por defecto

        if position_x is None or position_y is None:
            return Response({
                'success': False,
                'message': 'Faltan coordenadas de posición.'
            }, status=400)

        # Obtener perfil del jugador
        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        # Validar límites de la habitación actual
        if player_profile.current_room:
            room = player_profile.current_room
            # Asegurar que la posición esté dentro de los límites de la habitación
            position_x = max(0, min(position_x, room.length))
            position_y = max(0, min(position_y, room.width))
            position_z = max(0, min(position_z, room.height))

        # Actualizar posición
        player_profile.position_x = position_x
        player_profile.position_y = position_y
        # Nota: position_z no se guarda en el modelo actual, pero se puede agregar si es necesario
        player_profile.save()

        return Response({
            'success': True,
            'message': 'Posición actualizada correctamente.',
            'position': {
                'x': player_profile.position_x,
                'y': player_profile.position_y,
                'z': position_z
            }
        })

    except Exception as e:
        logger.error(f"Error en update_player_position: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)


@api_view(['GET'])
def get_player_status(request):
    """
    API endpoint para obtener el estado completo del player.
    """
    try:
        # Obtener perfil del jugador
        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        # Obtener habitación actual
        current_room_data = None
        if player_profile.current_room:
            room = player_profile.current_room
            current_room_data = {
                'id': room.id,
                'name': room.name,
                'description': room.description,
                'dimensions': {
                    'length': room.length,
                    'width': room.width,
                    'height': room.height
                }
            }

        return Response({
            'success': True,
            'player': {
                'energy': player_profile.energy,
                'productivity': player_profile.productivity,
                'social': player_profile.social,
                'position': {
                    'x': player_profile.position_x or 0,
                    'y': player_profile.position_y or 0,
                    'z': 1.7
                },
                'state': player_profile.state,
                'skills': player_profile.skills
            },
            'current_room': current_room_data,
            'navigation_history': player_profile.navigation_history or []
        })

    except Exception as e:
        logger.error(f"Error en get_player_status: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)


@login_required
def create_navigation_test_zone(request):
    """
    Vista para crear la zona de pruebas de navegación con estructura jerárquica de 4 niveles
    y conexiones interconectadas (puertas, portales, objetos).
    """
    from django.db import transaction

    # Usar transacción para asegurar atomicidad
    with transaction.atomic():
        # Nivel 1: Habitación raíz
        root_room, created = Room.objects.get_or_create(
            name='Navigation Test Zone',
            defaults={
                'description': 'Zona de pruebas para testing de navegación por habitaciones interconectadas',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'x': 0, 'y': 0, 'z': 0,
                'length': 20, 'width': 20, 'height': 5,
                'color_primary': '#4CAF50',
                'color_secondary': '#2196F3',
                'material_type': 'CONCRETE',
                'lighting_intensity': 80,
                'temperature': 22.0
            }
        )

        # Nivel 2: Sectores principales
        alpha_sector, _ = Room.objects.get_or_create(
            name='Alpha Sector',
            defaults={
                'description': 'Sector Alpha - Área de desarrollo y testing',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': root_room,
                'x': 25, 'y': 0, 'z': 0,
                'length': 15, 'width': 15, 'height': 4,
                'color_primary': '#FF9800',
                'color_secondary': '#F44336',
                'material_type': 'METAL',
                'lighting_intensity': 70
            }
        )

        beta_sector, _ = Room.objects.get_or_create(
            name='Beta Sector',
            defaults={
                'description': 'Sector Beta - Área de producción',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'MEETING',
                'parent_room': root_room,
                'x': 0, 'y': 25, 'z': 0,
                'length': 12, 'width': 18, 'height': 4,
                'color_primary': '#9C27B0',
                'color_secondary': '#673AB7',
                'material_type': 'GLASS',
                'lighting_intensity': 60
            }
        )

        gamma_sector, _ = Room.objects.get_or_create(
            name='Gamma Sector',
            defaults={
                'description': 'Sector Gamma - Área administrativa',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'LOUNGE',
                'parent_room': root_room,
                'x': -20, 'y': 0, 'z': 0,
                'length': 18, 'width': 12, 'height': 4,
                'color_primary': '#00BCD4',
                'color_secondary': '#009688',
                'material_type': 'WOOD',
                'lighting_intensity': 75
            }
        )

        # Nivel 3: Sub-sectores
        # Alpha sub-sectores
        alpha_1, _ = Room.objects.get_or_create(
            name='Alpha-1',
            defaults={
                'description': 'Sub-sector Alpha-1 - Desarrollo frontend',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': alpha_sector,
                'x': 30, 'y': 5, 'z': 0,
                'length': 10, 'width': 8, 'height': 3,
                'color_primary': '#FF5722',
                'color_secondary': '#E64A19'
            }
        )

        alpha_2, _ = Room.objects.get_or_create(
            name='Alpha-2',
            defaults={
                'description': 'Sub-sector Alpha-2 - Desarrollo backend',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': alpha_sector,
                'x': 30, 'y': -5, 'z': 0,
                'length': 10, 'width': 8, 'height': 3,
                'color_primary': '#2196F3',
                'color_secondary': '#1976D2'
            }
        )

        alpha_3, _ = Room.objects.get_or_create(
            name='Alpha-3',
            defaults={
                'description': 'Sub-sector Alpha-3 - Testing y QA',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'MEETING',
                'parent_room': alpha_sector,
                'x': 45, 'y': 0, 'z': 0,
                'length': 8, 'width': 10, 'height': 3,
                'color_primary': '#4CAF50',
                'color_secondary': '#388E3C'
            }
        )

        # Beta sub-sectores
        beta_1, _ = Room.objects.get_or_create(
            name='Beta-1',
            defaults={
                'description': 'Sub-sector Beta-1 - Producción primaria',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': beta_sector,
                'x': 5, 'y': 30, 'z': 0,
                'length': 8, 'width': 12, 'height': 3,
                'color_primary': '#9C27B0',
                'color_secondary': '#7B1FA2'
            }
        )

        beta_2, _ = Room.objects.get_or_create(
            name='Beta-2',
            defaults={
                'description': 'Sub-sector Beta-2 - Producción secundaria',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': beta_sector,
                'x': -5, 'y': 30, 'z': 0,
                'length': 8, 'width': 12, 'height': 3,
                'color_primary': '#FF9800',
                'color_secondary': '#F57C00'
            }
        )

        # Gamma sub-sectores
        gamma_1, _ = Room.objects.get_or_create(
            name='Gamma-1',
            defaults={
                'description': 'Sub-sector Gamma-1 - Administración general',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'LOUNGE',
                'parent_room': gamma_sector,
                'x': -25, 'y': 5, 'z': 0,
                'length': 10, 'width': 6, 'height': 3,
                'color_primary': '#00BCD4',
                'color_secondary': '#00ACC1'
            }
        )

        gamma_2, _ = Room.objects.get_or_create(
            name='Gamma-2',
            defaults={
                'description': 'Sub-sector Gamma-2 - Recursos humanos',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'MEETING',
                'parent_room': gamma_sector,
                'x': -25, 'y': -5, 'z': 0,
                'length': 10, 'width': 6, 'height': 3,
                'color_primary': '#8BC34A',
                'color_secondary': '#689F38'
            }
        )

        gamma_3, _ = Room.objects.get_or_create(
            name='Gamma-3',
            defaults={
                'description': 'Sub-sector Gamma-3 - Finanzas',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': gamma_sector,
                'x': -40, 'y': 0, 'z': 0,
                'length': 12, 'width': 8, 'height': 3,
                'color_primary': '#FFC107',
                'color_secondary': '#FF8F00'
            }
        )

        gamma_4, _ = Room.objects.get_or_create(
            name='Gamma-4',
            defaults={
                'description': 'Sub-sector Gamma-4 - Legal',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'MEETING',
                'parent_room': gamma_sector,
                'x': -25, 'y': -15, 'z': 0,
                'length': 8, 'width': 8, 'height': 3,
                'color_primary': '#795548',
                'color_secondary': '#5D4037'
            }
        )

        # Nivel 4: Sub-sub-sectores
        alpha_1a, _ = Room.objects.get_or_create(
            name='Alpha-1A',
            defaults={
                'description': 'Sub-sub-sector Alpha-1A - UI/UX Design',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': alpha_1,
                'x': 35, 'y': 8, 'z': 0,
                'length': 6, 'width': 5, 'height': 3,
                'color_primary': '#E91E63',
                'color_secondary': '#C2185B'
            }
        )

        alpha_1b, _ = Room.objects.get_or_create(
            name='Alpha-1B',
            defaults={
                'description': 'Sub-sub-sector Alpha-1B - Frontend Development',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': alpha_1,
                'x': 35, 'y': 2, 'z': 0,
                'length': 6, 'width': 5, 'height': 3,
                'color_primary': '#3F51B5',
                'color_secondary': '#303F9F'
            }
        )

        gamma_3x, _ = Room.objects.get_or_create(
            name='Gamma-3X',
            defaults={
                'description': 'Sub-sub-sector Gamma-3X - Contabilidad',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'OFFICE',
                'parent_room': gamma_3,
                'x': -45, 'y': 3, 'z': 0,
                'length': 6, 'width': 6, 'height': 3,
                'color_primary': '#FF5722',
                'color_secondary': '#D84315'
            }
        )

        gamma_3y, _ = Room.objects.get_or_create(
            name='Gamma-3Y',
            defaults={
                'description': 'Sub-sub-sector Gamma-3Y - Auditoría',
                'owner': request.user,
                'creator': request.user,
                'permissions': 'public',
                'room_type': 'MEETING',
                'parent_room': gamma_3,
                'x': -45, 'y': -3, 'z': 0,
                'length': 6, 'width': 6, 'height': 3,
                'color_primary': '#607D8B',
                'color_secondary': '#455A64'
            }
        )

        # Crear conexiones físicas (puertas) entre habitaciones del mismo nivel
        # Función helper para crear conexiones bidireccionales
        def create_door_connection(from_room, to_room, direction_from, direction_to, door_name_suffix=""):
            # Crear entrada en habitación from
            entrance_from, _ = EntranceExit.objects.get_or_create(
                room=from_room,
                face=direction_from,
                defaults={
                    'name': f'Puerta a {to_room.name}{door_name_suffix}',
                    'description': f'Conecta a {to_room.name}',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'WOOD',
                    'color': '#8B4513'
                }
            )

            # Crear entrada en habitación to
            entrance_to, _ = EntranceExit.objects.get_or_create(
                room=to_room,
                face=direction_to,
                defaults={
                    'name': f'Puerta desde {from_room.name}{door_name_suffix}',
                    'description': f'Conecta desde {from_room.name}',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'WOOD',
                    'color': '#8B4513'
                }
            )

            # Crear conexión
            connection, _ = RoomConnection.objects.get_or_create(
                from_room=from_room,
                to_room=to_room,
                entrance=entrance_from,
                defaults={
                    'bidirectional': True,
                    'energy_cost': 5
                }
            )

            # Asignar conexión a la entrada de destino
            entrance_to.connection = connection
            entrance_to.save()

            return entrance_from, entrance_to

        # Conexiones horizontales (mismo nivel)
        # Nivel 2: entre sectores
        create_door_connection(root_room, alpha_sector, 'NORTH', 'SOUTH')
        create_door_connection(root_room, beta_sector, 'EAST', 'WEST')
        create_door_connection(root_room, gamma_sector, 'WEST', 'EAST')

        # Nivel 3: conexiones en Alpha
        create_door_connection(alpha_1, alpha_2, 'EAST', 'WEST')
        create_door_connection(alpha_2, alpha_3, 'EAST', 'WEST')

        # Nivel 3: conexiones en Beta
        create_door_connection(beta_1, beta_2, 'NORTH', 'SOUTH')

        # Nivel 3: conexiones en Gamma
        create_door_connection(gamma_1, gamma_2, 'NORTH', 'SOUTH')
        create_door_connection(gamma_2, gamma_3, 'WEST', 'EAST')
        create_door_connection(gamma_3, gamma_4, 'SOUTH', 'NORTH')

        # Nivel 4: conexiones
        create_door_connection(alpha_1a, alpha_1b, 'EAST', 'WEST')
        create_door_connection(gamma_3x, gamma_3y, 'NORTH', 'SOUTH')

        # Crear portales entre niveles diferentes
        def create_portal(from_room, to_room, entrance_from, entrance_to, portal_name):
            portal, _ = Portal.objects.get_or_create(
                entrance=entrance_from,
                exit=entrance_to,
                defaults={
                    'name': portal_name,
                    'energy_cost': 15,
                    'cooldown': 60  # 1 minuto
                }
            )
            return portal

        # Portales entre niveles
        # De Alpha Sector a Beta-1
        alpha_entrance = EntranceExit.objects.filter(room=alpha_sector, face='UP').first()
        if not alpha_entrance:
            alpha_entrance, _ = EntranceExit.objects.get_or_create(
                room=alpha_sector,
                face='UP',
                defaults={
                    'name': 'Portal Ascendente',
                    'description': 'Portal a Beta Sector',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#2196F3'
                }
            )

        beta1_entrance = EntranceExit.objects.filter(room=beta_1, face='DOWN').first()
        if not beta1_entrance:
            beta1_entrance, _ = EntranceExit.objects.get_or_create(
                room=beta_1,
                face='DOWN',
                defaults={
                    'name': 'Portal Descendente',
                    'description': 'Portal desde Alpha Sector',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#2196F3'
                }
            )

        create_portal(alpha_sector, beta_1, alpha_entrance, beta1_entrance, 'Portal Alpha-Beta')

        # De Beta Sector a Gamma-2
        beta_entrance = EntranceExit.objects.filter(room=beta_sector, face='UP').first()
        if not beta_entrance:
            beta_entrance, _ = EntranceExit.objects.get_or_create(
                room=beta_sector,
                face='UP',
                defaults={
                    'name': 'Portal Ascendente',
                    'description': 'Portal a Gamma Sector',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#9C27B0'
                }
            )

        gamma2_entrance = EntranceExit.objects.filter(room=gamma_2, face='DOWN').first()
        if not gamma2_entrance:
            gamma2_entrance, _ = EntranceExit.objects.get_or_create(
                room=gamma_2,
                face='DOWN',
                defaults={
                    'name': 'Portal Descendente',
                    'description': 'Portal desde Beta Sector',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#9C27B0'
                }
            )

        create_portal(beta_sector, gamma_2, beta_entrance, gamma2_entrance, 'Portal Beta-Gamma')

        # De Gamma Sector a Alpha-1
        gamma_entrance = EntranceExit.objects.filter(room=gamma_sector, face='UP').first()
        if not gamma_entrance:
            gamma_entrance, _ = EntranceExit.objects.get_or_create(
                room=gamma_sector,
                face='UP',
                defaults={
                    'name': 'Portal Ascendente',
                    'description': 'Portal a Alpha Sector',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#FF9800'
                }
            )

        alpha1_entrance = EntranceExit.objects.filter(room=alpha_1, face='DOWN').first()
        if not alpha1_entrance:
            alpha1_entrance, _ = EntranceExit.objects.get_or_create(
                room=alpha_1,
                face='DOWN',
                defaults={
                    'name': 'Portal Descendente',
                    'description': 'Portal desde Gamma Sector',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#FF9800'
                }
            )

        create_portal(gamma_sector, alpha_1, gamma_entrance, alpha1_entrance, 'Portal Gamma-Alpha')

        # De Alpha-1 a Gamma-3X
        alpha1_portal_entrance = EntranceExit.objects.filter(room=alpha_1, face='UP').first()
        if not alpha1_portal_entrance:
            alpha1_portal_entrance, _ = EntranceExit.objects.get_or_create(
                room=alpha_1,
                face='UP',
                defaults={
                    'name': 'Portal Dimensional',
                    'description': 'Portal a Gamma-3X',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'GLASS',
                    'color': '#00BCD4'
                }
            )

        gamma3x_entrance = EntranceExit.objects.filter(room=gamma_3x, face='DOWN').first()
        if not gamma3x_entrance:
            gamma3x_entrance, _ = EntranceExit.objects.get_or_create(
                room=gamma_3x,
                face='DOWN',
                defaults={
                    'name': 'Portal Dimensional',
                    'description': 'Portal desde Alpha-1',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'GLASS',
                    'color': '#00BCD4'
                }
            )

        create_portal(alpha_1, gamma_3x, alpha1_portal_entrance, gamma3x_entrance, 'Portal Dimensional Alpha-Gamma')

        # De Beta-2 a Alpha-1A
        beta2_portal_entrance = EntranceExit.objects.filter(room=beta_2, face='UP').first()
        if not beta2_portal_entrance:
            beta2_portal_entrance, _ = EntranceExit.objects.get_or_create(
                room=beta_2,
                face='UP',
                defaults={
                    'name': 'Portal Express',
                    'description': 'Portal a Alpha-1A',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#4CAF50'
                }
            )

        alpha1a_entrance = EntranceExit.objects.filter(room=alpha_1a, face='DOWN').first()
        if not alpha1a_entrance:
            alpha1a_entrance, _ = EntranceExit.objects.get_or_create(
                room=alpha_1a,
                face='DOWN',
                defaults={
                    'name': 'Portal Express',
                    'description': 'Portal desde Beta-2',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#4CAF50'
                }
            )

        create_portal(beta_2, alpha_1a, beta2_portal_entrance, alpha1a_entrance, 'Portal Express Beta-Alpha')

        # Crear objetos de conexión en habitaciones específicas
        def create_connection_object(room, name, obj_type, position_x, position_y):
            obj, _ = RoomObject.objects.get_or_create(
                room=room,
                name=name,
                defaults={
                    'position_x': position_x,
                    'position_y': position_y,
                    'object_type': obj_type,
                    'effect': {'connection_type': 'teleport', 'target_room': 'Gamma-3Y'},
                    'interaction_cooldown': 30
                }
            )
            return obj

        # Objeto de conexión en Alpha-1A que conecta a Gamma-3Y
        create_connection_object(alpha_1a, 'Cristal Dimensional', 'DOOR', 3, 2)

        # Objeto de conexión en Gamma-3Y que conecta de vuelta
        create_connection_object(gamma_3y, 'Cristal Dimensional', 'PORTAL', 3, 2)

        # Teletransportar al usuario a la habitación raíz si no está ya ahí
        player_profile, _ = PlayerProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'current_room': root_room,
                'energy': 100,
                'productivity': 50,
                'social': 50,
                'position_x': 10,
                'position_y': 10
            }
        )

        if player_profile.current_room != root_room:
            player_profile.current_room = root_room
            player_profile.position_x = 10
            player_profile.position_y = 10
            player_profile.save()

        messages.success(request, 'Zona de pruebas de navegación creada exitosamente. Te hemos teletransportado a la habitación raíz.')
        return redirect('rooms:room_detail', pk=root_room.pk)


# ==========================================
# ACTION PANEL - CREACIÓN DE OBJETOS
# ==========================================

@login_required
def object_action_panel(request, room_id):
    """Renderiza el panel de acciones para crear objetos en una habitación."""
    room = get_object_or_404(Room, pk=room_id)
    if not room.can_user_manage(request.user):
        messages.error(request, 'No tienes permisos para modificar esta habitación.')
        return redirect('rooms:room_detail', pk=room.pk)

    form = ObjectCreateForm()
    form.room = room

    hotbar_types = [
        {'type': 'WORK', 'label': 'Workstation', 'icon': 'bi-tools', 'color': 'primary'},
        {'type': 'SOCIAL', 'label': 'Social Area', 'icon': 'bi-people', 'color': 'success'},
        {'type': 'REST', 'label': 'Rest Zone', 'icon': 'bi-moon', 'color': 'info'},
        {'type': 'DOOR', 'label': 'Door', 'icon': 'bi-door-open', 'color': 'warning'},
        {'type': 'EQUIPMENT', 'label': 'Equipment', 'icon': 'bi-cpu', 'color': 'secondary'},
        {'type': 'BOX', 'label': 'Box', 'icon': 'bi-box', 'color': 'dark'},
    ]

    context = {
        'room': room,
        'form': form,
        'hotbar_types': hotbar_types,
        'page_title': f'Crear objeto en {room.name}',
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'rooms/includes/object_action_panel_content.html', context)

    return render(request, 'rooms/includes/object_action_panel.html', context)


@login_required
def create_room_object(request, room_id):
    """Crea un RoomObject o Box en la habitación indicada."""
    room = get_object_or_404(Room, pk=room_id)
    if not room.can_user_manage(request.user):
        return JsonResponse({'success': False, 'message': 'Sin permisos.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    form = ObjectCreateForm(request.POST)
    form.room = room

    if not form.is_valid():
        return JsonResponse({
            'success': False,
            'errors': form.errors.get_json_data(),
            'message': 'Formulario inválido.',
            'detail': 'El formulario contiene errores. Revisa los campos e intenta nuevamente.'
        }, status=400)

    object_type = form.cleaned_data['object_type']

    try:
        if object_type == 'BOX':
            box = Box(
                room=room,
                name=form.cleaned_data['name'],
                description=form.cleaned_data.get('description', ''),
                position_x=form.cleaned_data.get('position_x', 0),
                position_y=form.cleaned_data.get('position_y', 0),
                width=form.cleaned_data.get('box_width', 60),
                height=form.cleaned_data.get('box_height', 40),
                depth=form.cleaned_data.get('box_depth', 40),
                color=form.cleaned_data.get('box_color', '#8B4513'),
                material_type=form.cleaned_data.get('box_material_type', 'CARDBOARD'),
                is_locked=form.cleaned_data.get('box_is_locked', False),
                required_key=form.cleaned_data.get('box_required_key', ''),
                mass=form.cleaned_data.get('box_mass', 1.0),
                capacity=form.cleaned_data.get('box_capacity', 10),
                contents=form.cleaned_data.get('box_contents', []),
            )
            box.save()
            return JsonResponse({
                'success': True,
                'message': f'Caja "{box.name}" creada exitosamente.',
                'object': {
                    'id': box.id,
                    'name': box.name,
                    'type': 'BOX',
                    'room_id': room.id,
                    'position_x': box.position_x,
                    'position_y': box.position_y,
                }
            })
        else:
            room_object = RoomObject(
                room=room,
                name=form.cleaned_data['name'],
                object_type=object_type,
                position_x=form.cleaned_data.get('position_x', 0),
                position_y=form.cleaned_data.get('position_y', 0),
                effect=form.cleaned_data.get('effect', {}),
            )
            room_object.save()
            return JsonResponse({
                'success': True,
                'message': f'Objeto "{room_object.name}" creado exitosamente.',
                'object': {
                    'id': room_object.id,
                    'name': room_object.name,
                    'type': room_object.object_type,
                    'room_id': room.id,
                    'position_x': room_object.position_x,
                    'position_y': room_object.position_y,
                }
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error al crear el objeto.',
            'detail': str(e),
            'exception': str(type(e).__name__)
        }, status=400)


@login_required
@api_view(['GET'])
def object_hotbar_types(request):
    """Devuelve los tipos de objeto disponibles para el hotbar."""
    types = [
        {'type': 'WORK', 'label': 'Workstation', 'icon': 'bi-tools', 'color': 'primary'},
        {'type': 'SOCIAL', 'label': 'Social Area', 'icon': 'bi-people', 'color': 'success'},
        {'type': 'REST', 'label': 'Rest Zone', 'icon': 'bi-moon', 'color': 'info'},
        {'type': 'DOOR', 'label': 'Door', 'icon': 'bi-door-open', 'color': 'warning'},
        {'type': 'EQUIPMENT', 'label': 'Equipment', 'icon': 'bi-cpu', 'color': 'secondary'},
        {'type': 'BOX', 'label': 'Box', 'icon': 'bi-box', 'color': 'dark'},
    ]
    return Response({'success': True, 'types': types})
