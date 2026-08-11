# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from .models import Cell, CellConnection, CellMembership, Comment, Evaluation, PlayerProfile
from .forms import CellForm, EvaluationForm, ObjectCreateForm
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from .exceptions import RoomManagerError
from django.http import Http404
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import uuid
from .transition_manager import get_room_transition_manager

import json
import logging
import math
import requests
from requests.adapters import HTTPAdapter, Retry
from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Count
from rest_framework import status, viewsets
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .models import Cell, CellConnection, Message, Outbox, CDC, PlayerProfile
from .serializers import (
    MessageSerializer, CellSearchSerializer, CellSerializer, CellCRUDSerializer, CellConnectionSerializer
)

logger = logging.getLogger(__name__)


def _room_qs():
    return Cell.objects.filter(cell_type='ROOM')


def _user_can_manage(cell, user):
    return cell.owner == user or user.is_staff


@login_required
def lobby(request):
    user_universes = Cell.objects.filter(cell_type='UNIVERSE', owner=request.user).order_by('-created_at')[:5]
    user_worlds = Cell.objects.filter(cell_type='WORLD', owner=request.user).order_by('-created_at')[:5]
    user_areas = Cell.objects.filter(cell_type='AREA', owner=request.user).order_by('-created_at')[:5]
    sections = [
        {
            'title': 'Tus Universos',
            'url_name': 'rooms:universe_list',
            'detail_url_name': 'rooms:universe_detail',
            'icon': 'bi-globe',
            'items': user_universes,
        },
        {
            'title': 'Tus Mundos',
            'url_name': 'rooms:world_list',
            'detail_url_name': 'rooms:world_detail',
            'icon': 'bi-globe2',
            'items': user_worlds,
        },
        {
            'title': 'Tus Áreas',
            'url_name': 'rooms:area_list',
            'detail_url_name': 'rooms:area_detail',
            'icon': 'bi-layers',
            'items': user_areas,
        },
        {
            'title': 'Recent Rooms',
            'url_name': 'rooms:room_list',
            'detail_url_name': 'rooms:room_detail',
            'icon': 'bi-house',
            'items': _room_qs().order_by('-created_at')[:5]
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
    ]

    stats = [
        {
            'title': 'Total Rooms',
            'value': _room_qs().count(),
            'icon': 'bi-house-door',
            'trend': 12,
            'trend_color': 'success',
            'period': 'This month'
        },
        {
            'title': 'Tus Universos',
            'value': user_universes.count(),
            'icon': 'bi-globe',
            'trend': 0,
            'trend_color': 'info',
            'period': 'Activos'
        },
        {
            'title': 'Tus Mundos',
            'value': user_worlds.count(),
            'icon': 'bi-globe2',
            'trend': 0,
            'trend_color': 'info',
            'period': 'Activos'
        },
        {
            'title': 'Tus Áreas',
            'value': user_areas.count(),
            'icon': 'bi-layers',
            'trend': 0,
            'trend_color': 'info',
            'period': 'Activas'
        },
    ]

    quick_filters = ['Available', 'Recently Added', 'Popular']
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

    player_profile.state = 'AVAILABLE'
    player_profile.energy = 100

    initial_room = _room_qs().filter(properties__permissions='public').first()
    if not initial_room:
        initial_room, room_created = Cell.objects.get_or_create(
            name='Lobby Principal',
            cell_type='ROOM',
            defaults={
                'description': 'Habitación principal para nuevos usuarios',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'LOUNGE'}
            }
        )

    player_profile.current_room = initial_room
    player_profile.save()

    messages.success(request, f'Te has registrado como disponible y entrado al {initial_room.name}')
    return redirect('rooms:room_detail', pk=initial_room.pk)


@login_required
def create_room(request):
    if request.method == 'POST':
        form = CellForm(request.POST, request.FILES)
        if form.is_valid():
            cell = form.save(commit=False)
            cell.cell_type = 'ROOM'
            cell.owner = request.user
            cell.save()
            messages.success(request, 'Sala creada con éxito')
            cache.set('room_{}'.format(cell.pk), cell)
            return HttpResponseRedirect(reverse_lazy('rooms:lobby'))
    else:
        form = CellForm()
    context = {
        'form': form,
        'page_title': 'Crear Nueva Habitación',
        'is_edit': False
    }

    return render(request, 'rooms/room_form.html', context)


@login_required
def create_cell(request):
    if request.method == 'POST':
        form = CellForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            cell = form.save(commit=False)
            cell.owner = request.user
            if not cell.cell_type:
                cell.cell_type = 'ROOM'
            cell.save()
            messages.success(request, 'Celda creada con éxito')
            return redirect('rooms:room_detail', pk=cell.pk)
    else:
        form = CellForm(user=request.user, initial={'cell_type': 'ROOM'})
    context = {
        'form': form,
        'page_title': 'Crear Celda',
        'is_edit': False
    }
    return render(request, 'rooms/create_cell.html', context)


@login_required
def universe_list(request):
    user = request.user
    base_qs = Cell.objects.filter(cell_type='UNIVERSE').select_related('owner')
    user_memberships = CellMembership.objects.filter(user=user, cell__cell_type='UNIVERSE').select_related('cell')
    user_universe_ids = list(user_memberships.values_list('cell_id', flat=True))

    my_universes = base_qs.filter(owner=user)
    member_universes = base_qs.filter(id__in=user_universe_ids).exclude(owner=user)
    other_universes = base_qs.exclude(id__in=user_universe_ids)

    context = {
        'my_universes': my_universes,
        'member_universes': member_universes,
        'other_universes': other_universes,
        'user_memberships': user_memberships,
    }
    return render(request, 'rooms/universe_list.html', context)


@login_required
def create_universe(request):
    if request.method == 'POST':
        form = CellForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            cell = form.save(commit=False)
            cell.cell_type = 'UNIVERSE'
            cell.owner = request.user
            cell.save()
            CellMembership.objects.create(cell=cell, user=request.user, role=CellMembership.ROLE_OWNER)
            messages.success(request, 'Universo creado con éxito')
            return redirect('rooms:universe_detail', pk=cell.pk)
    else:
        form = CellForm(user=request.user, initial={'cell_type': 'UNIVERSE'})
    return render(request, 'rooms/create_cell.html', {'form': form, 'page_title': 'Crear Universo'})


@login_required
def world_list(request):
    user = request.user
    my_worlds = Cell.objects.filter(cell_type='WORLD', owner=user).order_by('-created_at')
    other_worlds = Cell.objects.filter(cell_type='WORLD').exclude(owner=user).order_by('-created_at')

    context = {
        'my_worlds': my_worlds,
        'other_worlds': other_worlds,
    }
    return render(request, 'rooms/world_list.html', context)


@login_required
def world_detail(request, pk):
    world = get_object_or_404(Cell, pk=pk, cell_type='WORLD')
    children = world.children.all().order_by('cell_type', 'name')

    player = getattr(request.user, 'player_profile', None)
    nav_breadcrumb = player.get_navigation_breadcrumb() if player else []
    nav_back_target = player.get_last_navigation_target() if player else None

    history_cells = []
    if player and player.navigation_history:
        history_ids = list(reversed(player.navigation_history[-10:]))
        history_cells = list(Cell.objects.filter(pk__in=history_ids).order_by('?'))

    context = {
        'world': world,
        'children': children,
        'page_title': world.name,
        'current_cell': world,
        'player': player,
        'nav_breadcrumb': nav_breadcrumb,
        'nav_back_target': nav_back_target,
        'history': history_cells,
        'exits': children,
    }
    return render(request, 'rooms/world_detail.html', context)


@login_required
def create_world(request):
    if request.method == 'POST':
        form = CellForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            cell = form.save(commit=False)
            cell.cell_type = 'WORLD'
            cell.owner = request.user
            cell.save()
            messages.success(request, 'Mundo creado con éxito')
            return redirect('rooms:world_detail', pk=cell.pk)
    else:
        form = CellForm(user=request.user, initial={'cell_type': 'WORLD'})
    return render(request, 'rooms/create_cell.html', {'form': form, 'page_title': 'Crear Mundo'})


@login_required
def area_list(request):
    user = request.user
    my_areas = Cell.objects.filter(cell_type='AREA', owner=user).order_by('-created_at')
    other_areas = Cell.objects.filter(cell_type='AREA').exclude(owner=user).order_by('-created_at')

    context = {
        'my_areas': my_areas,
        'other_areas': other_areas,
    }
    return render(request, 'rooms/area_list.html', context)


@login_required
def area_detail(request, pk):
    area = get_object_or_404(Cell, pk=pk, cell_type='AREA')
    children = area.children.all().order_by('cell_type', 'name')

    player = getattr(request.user, 'player_profile', None)
    nav_breadcrumb = player.get_navigation_breadcrumb() if player else []
    nav_back_target = player.get_last_navigation_target() if player else None

    history_cells = []
    if player and player.navigation_history:
        history_ids = list(reversed(player.navigation_history[-10:]))
        history_cells = list(Cell.objects.filter(pk__in=history_ids).order_by('?'))

    context = {
        'area': area,
        'children': children,
        'page_title': area.name,
        'current_cell': area,
        'player': player,
        'nav_breadcrumb': nav_breadcrumb,
        'nav_back_target': nav_back_target,
        'history': history_cells,
        'exits': children,
    }
    return render(request, 'rooms/area_detail.html', context)


@login_required
def create_area(request):
    if request.method == 'POST':
        form = CellForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            cell = form.save(commit=False)
            cell.cell_type = 'AREA'
            cell.owner = request.user
            cell.save()
            messages.success(request, 'Área creada con éxito')
            return redirect('rooms:area_detail', pk=cell.pk)
    else:
        form = CellForm(user=request.user, initial={'cell_type': 'AREA'})
    return render(request, 'rooms/create_cell.html', {'form': form, 'page_title': 'Crear Área'})


def cell_detail(request, pk):
    cell = get_object_or_404(Cell, pk=pk)
    if cell.cell_type == 'CONTAINER':
        return redirect('rooms:container_detail', pk=cell.pk)
    if cell.cell_type == 'ITEM':
        return redirect('rooms:item_detail', pk=cell.pk)
    if cell.cell_type == 'UNIVERSE':
        return redirect('rooms:universe_detail', pk=cell.pk)
    if cell.cell_type == 'WORLD':
        return redirect('rooms:world_detail', pk=cell.pk)
    if cell.cell_type == 'AREA':
        return redirect('rooms:area_detail', pk=cell.pk)
    return render(request, 'rooms/cell_detail.html', {'cell': cell, 'page_title': cell.name})


def item_detail(request, pk):
    item = get_object_or_404(Cell, pk=pk, cell_type='ITEM')
    context = {
        'item': item,
        'page_title': item.name,
    }
    return render(request, 'rooms/item_detail.html', context)


def container_detail(request, pk):
    container = get_object_or_404(Cell, pk=pk, cell_type='CONTAINER')
    items = container.children.all().order_by('cell_type', 'name')
    context = {
        'container': container,
        'items': items,
        'page_title': container.name,
    }
    return render(request, 'rooms/container_detail.html', context)


@login_required
def add_container_item(request, pk):
    container = get_object_or_404(Cell, pk=pk, cell_type='CONTAINER')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        cell_type = request.POST.get('cell_type', 'ITEM')
        position_x = request.POST.get('position_x', 0)
        position_y = request.POST.get('position_y', 0)
        position_z = request.POST.get('position_z', 0)
        description = request.POST.get('description', '')

        if not name:
            messages.error(request, 'El nombre es obligatorio')
            return redirect('rooms:container_detail', pk=container.pk)

        Cell.objects.create(
            name=name,
            cell_type=cell_type,
            parent=container,
            position_x=position_x,
            position_y=position_y,
            position_z=position_z,
            description=description,
            owner=request.user,
        )
        messages.success(request, 'Item agregado al contenedor')
        return redirect('rooms:container_detail', pk=container.pk)

    return render(request, 'rooms/add_container_item.html', {
        'container': container,
        'page_title': f'Agregar item a {container.name}',
    })


def universe_detail(request, pk):
    universe = get_object_or_404(Cell, pk=pk, cell_type='UNIVERSE')
    membership = CellMembership.objects.filter(cell=universe, user=request.user).first()
    if not membership:
        messages.error(request, 'No tienes acceso a este universo.')
        return redirect('rooms:universe_list')
    children = universe.children.all().order_by('cell_type', 'name')

    player = getattr(request.user, 'player_profile', None)
    nav_breadcrumb = player.get_navigation_breadcrumb() if player else []
    nav_back_target = player.get_last_navigation_target() if player else None

    history_cells = []
    if player and player.navigation_history:
        history_ids = list(reversed(player.navigation_history[-10:]))
        history_cells = list(Cell.objects.filter(pk__in=history_ids).order_by('?'))

    context = {
        'universe': universe,
        'membership': membership,
        'children': children,
        'current_cell': universe,
        'player': player,
        'nav_breadcrumb': nav_breadcrumb,
        'nav_back_target': nav_back_target,
        'history': history_cells,
        'exits': children,
    }
    return render(request, 'rooms/universe_detail.html', context)


@login_required
def join_universe(request, pk):
    universe = get_object_or_404(Cell, pk=pk, cell_type='UNIVERSE')
    membership, created = CellMembership.objects.get_or_create(cell=universe, user=request.user, defaults={'role': CellMembership.ROLE_MEMBER})
    if created:
        messages.success(request, f'Te uniste al universo {universe.name}')
    else:
        messages.info(request, f'Ya eres miembro de {universe.name}')
    return redirect('rooms:universe_detail', pk=universe.pk)


def room_detail(request, pk):
    cell = get_object_or_404(Cell, pk=pk)
    if cell.cell_type != 'ROOM':
        return redirect('rooms:cell_detail', pk=cell.pk)

    room = cell
    try:

        try:
            room_image_url = room.image.url if room.image and room.image.name else None
        except ValueError as e:
            logger.warning(f"Room with ID {pk} has no associated image: {str(e)}")
            room_image_url = None

        if not room_image_url:
            room_image_url = '/static/images/default-room.jpg'

        detail_url = reverse_lazy('rooms:room_detail', kwargs={'pk': pk})
        logger.debug(f"Generated URL for room_detail: {detail_url}")

        entrance_exits = room.children.filter(cell_type='DOOR')
        portals = room.children.filter(cell_type='PORTAL')

        if request.method == 'POST':
            if 'create_entrance_exit' in request.POST:
                name = request.POST.get('name', 'Door')
                cell_type = request.POST.get('cell_type', 'DOOR')
                door_cell, _ = Cell.objects.get_or_create(
                    room=room,
                    name=name,
                    cell_type=cell_type,
                    defaults={
                        'position_x': request.POST.get('position_x', 0),
                        'position_y': request.POST.get('position_y', 0),
                        'width': request.POST.get('width', 100),
                        'height': request.POST.get('height', 200),
                        'is_locked': request.POST.get('is_locked', False),
                        'properties': {
                            'face': request.POST.get('face', 'NORTH'),
                            'enabled': True,
                            'door_type': request.POST.get('door_type', 'SINGLE'),
                            'material': request.POST.get('material', 'WOOD'),
                            'color': request.POST.get('color', '#8B4513'),
                            'interaction_type': request.POST.get('interaction_type', 'PUSH'),
                            'animation_type': request.POST.get('animation_type', 'SWING'),
                            'requires_both_hands': request.POST.get('requires_both_hands', False),
                            'interaction_distance': request.POST.get('interaction_distance', 150),
                            'is_open': request.POST.get('is_open', False),
                            'usage_count': 0,
                            'health': request.POST.get('health', 100),
                            'access_level': request.POST.get('access_level', 0),
                            'security_system': request.POST.get('security_system', 'NONE'),
                            'alarm_triggered': request.POST.get('alarm_triggered', False),
                            'seals_air': request.POST.get('seals_air', True),
                            'seals_sound': request.POST.get('seals_sound', 20),
                            'temperature_resistance': request.POST.get('temperature_resistance', 50),
                            'pressure_resistance': request.POST.get('pressure_resistance', 1),
                            'energy_cost_modifier': request.POST.get('energy_cost_modifier', 0),
                            'experience_reward': request.POST.get('experience_reward', 1),
                            'special_effects': request.POST.get('special_effects', {}),
                            'cooldown': request.POST.get('cooldown', 0),
                            'max_usage_per_hour': request.POST.get('max_usage_per_hour', 0),
                            'glow_intensity': request.POST.get('glow_intensity', 0),
                            'decoration_type': request.POST.get('decoration_type', 'NONE'),
                            'auto_close': request.POST.get('auto_close', False),
                            'close_delay': request.POST.get('close_delay', 5),
                            'open_speed': request.POST.get('open_speed', 1.0),
                            'close_speed': request.POST.get('close_speed', 1.0),
                            'opacity': request.POST.get('opacity', 1.0),
                        }
                    }
                )
                messages.success(request, 'Entrada/Salida creada con éxito')
                return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': pk}))

            elif 'create_portal' in request.POST:
                name = request.POST.get('name', 'Portal')
                portal_cell, _ = Cell.objects.get_or_create(
                    room=room,
                    name=name,
                    cell_type='PORTAL',
                    defaults={
                        'position_x': request.POST.get('position_x', 0),
                        'position_y': request.POST.get('position_y', 0),
                        'properties': {
                            'energy_cost': request.POST.get('energy_cost', 10),
                            'cooldown': request.POST.get('cooldown', 60),
                            'is_active': True,
                        }
                    }
                )
                messages.success(request, 'Portal creado con éxito')
                return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': pk}))

            elif 'enter_room' in request.POST:
                room_id = request.POST['room_id']
                return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': room_id}))

        cells = room.children.select_related('parent').all()
        player = request.user.player_profile if hasattr(request.user, 'player_profile') else None
        nav_breadcrumb = request.user.player_profile.get_navigation_breadcrumb() if hasattr(request.user, 'player_profile') else []
        nav_back_target = request.user.player_profile.get_last_navigation_target() if hasattr(request.user, 'player_profile') else None
        from_connections = CellConnection.objects.filter(from_cell=room).select_related('to_cell', 'entrance')
        to_connections = CellConnection.objects.filter(to_cell=room).select_related('from_cell', 'entrance')

        all_exits = []
        for entrance in entrance_exits:
            all_exits.append({
                'name': entrance.name,
                'cell_type': entrance.get_cell_type_display(),
                'energy_cost': 1,
                'id': entrance.id,
                'url': reverse_lazy('rooms:cell_detail', kwargs={'pk': entrance.pk}),
            })
        for portal in portals:
            all_exits.append({
                'name': portal.name,
                'cell_type': portal.get_cell_type_display(),
                'energy_cost': 1,
                'id': portal.id,
                'url': reverse_lazy('rooms:cell_detail', kwargs={'pk': portal.pk}),
            })
        for conn in from_connections:
            all_exits.append({
                'name': conn.to_cell.name,
                'cell_type': conn.to_cell.get_cell_type_display(),
                'energy_cost': conn.energy_cost,
                'id': conn.to_cell.id,
                'url': reverse_lazy('rooms:cell_detail', kwargs={'pk': conn.to_cell.pk}),
            })
        for conn in to_connections:
            all_exits.append({
                'name': conn.from_cell.name,
                'cell_type': conn.from_cell.get_cell_type_display(),
                'energy_cost': conn.energy_cost,
                'id': conn.from_cell.id,
                'url': reverse_lazy('rooms:cell_detail', kwargs={'pk': conn.from_cell.pk}),
            })

        history_cells = []
        if player and player.navigation_history:
            history_ids = list(reversed(player.navigation_history[-10:]))
            history_cells = list(Cell.objects.filter(pk__in=history_ids).order_by('?'))

        return render(request, 'rooms/room_detail.html', {
            'page_title': 'Room Details',
            'room': room,
            'room_image_url': room_image_url,
            'entrance_exits': entrance_exits,
            'portals': portals,
            'cells': cells,
            'player': player,
            'nav_breadcrumb': nav_breadcrumb,
            'nav_back_target': nav_back_target,
            'from_connections': from_connections,
            'to_connections': to_connections,
            'current_cell': room,
            'exits': all_exits,
            'history': history_cells,
        })
    except Http404:
        logger.warning(f"Room with ID {pk} not found in the database.")
        return JsonResponse({'detail': 'No Room matches the given query.'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in room_detail: {str(e)}", exc_info=True)
        return JsonResponse({'detail': 'An unexpected error occurred.'}, status=500)


def room_3d_view(request, pk):
    room = get_object_or_404(Cell, pk=pk, cell_type='ROOM')
    svg_content = generate_room_3d_svg(room)

    context = {
        'room': room,
        'svg_content': svg_content,
        'page_title': f'Vista 3D - {room.name}'
    }

    return render(request, 'rooms/room_3d.html', context)


@login_required
def room_3d_interactive_view(request, pk):
    room = get_object_or_404(Cell, pk=pk, cell_type='ROOM')

    permissions = getattr(room, 'permissions', room.properties.get('permissions', 'public'))
    if permissions == 'private':
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
    base_room, created = Cell.objects.get_or_create(
        name='Habitación Base 3D',
        cell_type='ROOM',
        defaults={
            'description': 'Habitación principal en posición 0,0,0 con conexiones 3D',
            'owner': request.user,
            'properties': {
                'permissions': 'public',
                'room_type': 'OFFICE',
            },
            'position_x': 0,
            'position_y': 0,
            'position_z': 0,
            'length': 10,
            'width': 10,
            'height': 3,
            'color_primary': '#4CAF50',
            'color_secondary': '#2196F3'
        }
    )

    connected_rooms = []

    north_room, _ = Cell.objects.get_or_create(
        name='Cocina',
        cell_type='ROOM',
        defaults={
            'description': 'Habitación conectada al norte',
            'owner': request.user,
            'properties': {'permissions': 'public', 'room_type': 'KITCHEN'},
            'position_x': 0,
            'position_y': 10,
            'position_z': 0,
            'length': 8,
            'width': 6,
            'height': 3,
            'color_primary': '#FF9800',
            'color_secondary': '#795548'
        }
    )
    connected_rooms.append(('north', north_room))

    east_room, _ = Cell.objects.get_or_create(
        name='Baño',
        cell_type='ROOM',
        defaults={
            'description': 'Habitación conectada al este',
            'owner': request.user,
            'properties': {'permissions': 'public', 'room_type': 'BATHROOM'},
            'position_x': 10,
            'position_y': 0,
            'position_z': 0,
            'length': 4,
            'width': 6,
            'height': 3,
            'color_primary': '#00BCD4',
            'color_secondary': '#607D8B'
        }
    )
    connected_rooms.append(('east', east_room))

    west_room, _ = Cell.objects.get_or_create(
        name='Dormitorio',
        cell_type='ROOM',
        defaults={
            'description': 'Habitación conectada al oeste',
            'owner': request.user,
            'properties': {'permissions': 'public', 'room_type': 'SPECIAL'},
            'position_x': -8,
            'position_y': 0,
            'position_z': 0,
            'length': 8,
            'width': 6,
            'height': 3,
            'color_primary': '#9C27B0',
            'color_secondary': '#673AB7'
        }
    )
    connected_rooms.append(('west', west_room))

    for direction, room in connected_rooms:
        entrance, _ = Cell.objects.get_or_create(
            room=base_room,
            name=f'Puerta {direction.title()}',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': direction.upper(),
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'WOOD',
                    'color': '#8B4513',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        connection, _ = CellConnection.objects.get_or_create(
            from_cell=base_room,
            to_cell=room,
            entrance=entrance,
            defaults={
                'bidirectional': True,
                'energy_cost': 5
            }
        )

        opposite_face = {
            'north': 'south',
            'south': 'north',
            'east': 'west',
            'west': 'east'
        }[direction]

        opposite_entrance, _ = Cell.objects.get_or_create(
            room=room,
            name=f'Puerta {opposite_face.title()}',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': opposite_face.upper(),
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'WOOD',
                    'color': '#8B4513',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

    exit_entrance, _ = Cell.objects.get_or_create(
        room=base_room,
        name='Salida a Calle',
        cell_type='DOOR',
        defaults={
            'position_x': 0,
            'position_y': 0,
            'width': 100,
            'height': 200,
            'is_locked': False,
            'properties': {
                'face': 'SOUTH',
                'enabled': True,
                'door_type': 'DOUBLE',
                'material': 'GLASS',
                'color': '#87CEEB',
                'interaction_type': 'PUSH',
                'animation_type': 'SWING',
                'requires_both_hands': False,
                'interaction_distance': 150,
                'is_open': False,
                'usage_count': 0,
                'health': 100,
                'access_level': 0,
                'security_system': 'NONE',
                'alarm_triggered': False,
                'seals_air': True,
                'seals_sound': 20,
                'temperature_resistance': 50,
                'pressure_resistance': 1,
                'energy_cost_modifier': 0,
                'experience_reward': 1,
                'special_effects': {},
                'cooldown': 0,
                'max_usage_per_hour': 0,
                'glow_intensity': 0,
                'decoration_type': 'NONE',
                'auto_close': False,
                'close_delay': 5,
                'open_speed': 1.0,
                'close_speed': 1.0,
                'opacity': 1.0,
                'is_locked': False,
            }
        }
    )

    player_profile, _ = PlayerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'current_room': base_room,
            'energy': 100,
            'productivity': 50,
            'social': 50,
            'position_x': 5,
            'position_y': 5,
            'state': 'AVAILABLE'
        }
    )

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


def room_comments(request, pk):
    room = get_object_or_404(Cell, pk=pk, cell_type='ROOM')
    if request.method == 'POST':
        comment = request.POST['comment']
        Comment.objects.create(room=room, comment=comment, user=request.user)
        messages.success(request, 'Comentario agregado con éxito')
        return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': pk}))
    return render(request, 'rooms/room_comments.html', {'room': room})


def room_evaluations(request, pk):
    room = get_object_or_404(Cell, pk=pk, cell_type='ROOM')
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
    return render(request, 'rooms/room_evaluations.html', {'room': room, 'evaluation_form': evaluation_form})


@login_required
def create_entrance_exit(request):
    if request.method == 'POST':
        name = request.POST.get('name', 'Door')
        cell_type = request.POST.get('cell_type', 'DOOR')
        properties = {
            'face': request.POST.get('face', 'NORTH'),
            'enabled': True,
            'door_type': request.POST.get('door_type', 'SINGLE'),
            'material': request.POST.get('material', 'WOOD'),
            'color': request.POST.get('color', '#8B4513'),
            'interaction_type': request.POST.get('interaction_type', 'PUSH'),
            'animation_type': request.POST.get('animation_type', 'SWING'),
            'requires_both_hands': request.POST.get('requires_both_hands', False),
            'interaction_distance': request.POST.get('interaction_distance', 150),
            'is_open': request.POST.get('is_open', False),
            'usage_count': 0,
            'health': request.POST.get('health', 100),
            'access_level': request.POST.get('access_level', 0),
            'security_system': request.POST.get('security_system', 'NONE'),
            'alarm_triggered': request.POST.get('alarm_triggered', False),
            'seals_air': request.POST.get('seals_air', True),
            'seals_sound': request.POST.get('seals_sound', 20),
            'temperature_resistance': request.POST.get('temperature_resistance', 50),
            'pressure_resistance': request.POST.get('pressure_resistance', 1),
            'energy_cost_modifier': request.POST.get('energy_cost_modifier', 0),
            'experience_reward': request.POST.get('experience_reward', 1),
            'special_effects': request.POST.get('special_effects', {}),
            'cooldown': request.POST.get('cooldown', 0),
            'max_usage_per_hour': request.POST.get('max_usage_per_hour', 0),
            'glow_intensity': request.POST.get('glow_intensity', 0),
            'decoration_type': request.POST.get('decoration_type', 'NONE'),
            'auto_close': request.POST.get('auto_close', False),
            'close_delay': request.POST.get('close_delay', 5),
            'open_speed': request.POST.get('open_speed', 1.0),
            'close_speed': request.POST.get('close_speed', 1.0),
            'opacity': request.POST.get('opacity', 1.0),
            'is_locked': request.POST.get('is_locked', False),
        }
        room_id = request.POST.get('room_id')
        room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
        entrance = Cell.objects.create(
            room=room,
            name=name,
            cell_type=cell_type,
            position_x=request.POST.get('position_x', 0),
            position_y=request.POST.get('position_y', 0),
            width=request.POST.get('width', 100),
            height=request.POST.get('height', 200),
            is_locked=request.POST.get('is_locked', False),
            properties=properties
        )
        messages.success(request, 'Entrada/Salida creada con éxito')
        return HttpResponseRedirect(reverse_lazy('entrance_exit_list'))
    return render(request, 'create_entrance_exit.html', {'form': None})


@login_required
def edit_entrance_exit(request, pk):
    entrance = get_object_or_404(Cell, pk=pk, cell_type='DOOR')
    room = entrance.room

    if not _user_can_manage(room, request.user):
        messages.error(request, 'No tienes permisos para editar esta entrada/salida.')
        return redirect('rooms:room_detail', pk=room.pk)

    if request.method == 'POST':
        entrance.name = request.POST.get('name', entrance.name)
        entrance.position_x = request.POST.get('position_x', entrance.position_x)
        entrance.position_y = request.POST.get('position_y', entrance.position_y)
        entrance.width = request.POST.get('width', entrance.width) or 100
        entrance.height = request.POST.get('height', entrance.height) or 200
        entrance.is_locked = request.POST.get('is_locked', entrance.is_locked)

        props = entrance.properties or {}
        props.update({
            'face': request.POST.get('face', props.get('face', 'NORTH')),
            'enabled': request.POST.get('enabled', props.get('enabled', True)),
            'door_type': request.POST.get('door_type', props.get('door_type', 'SINGLE')),
            'material': request.POST.get('material', props.get('material', 'WOOD')),
            'color': request.POST.get('color', props.get('color', '#8B4513')),
            'interaction_type': request.POST.get('interaction_type', props.get('interaction_type', 'PUSH')),
            'animation_type': request.POST.get('animation_type', props.get('animation_type', 'SWING')),
            'requires_both_hands': request.POST.get('requires_both_hands', props.get('requires_both_hands', False)),
            'interaction_distance': request.POST.get('interaction_distance', props.get('interaction_distance', 150)),
            'is_open': request.POST.get('is_open', props.get('is_open', False)),
            'usage_count': request.POST.get('usage_count', props.get('usage_count', 0)),
            'health': request.POST.get('health', props.get('health', 100)),
            'access_level': request.POST.get('access_level', props.get('access_level', 0)),
            'security_system': request.POST.get('security_system', props.get('security_system', 'NONE')),
            'alarm_triggered': request.POST.get('alarm_triggered', props.get('alarm_triggered', False)),
            'seals_air': request.POST.get('seals_air', props.get('seals_air', True)),
            'seals_sound': request.POST.get('seals_sound', props.get('seals_sound', 20)),
            'temperature_resistance': request.POST.get('temperature_resistance', props.get('temperature_resistance', 50)),
            'pressure_resistance': request.POST.get('pressure_resistance', props.get('pressure_resistance', 1)),
            'energy_cost_modifier': request.POST.get('energy_cost_modifier', props.get('energy_cost_modifier', 0)),
            'experience_reward': request.POST.get('experience_reward', props.get('experience_reward', 1)),
            'special_effects': request.POST.get('special_effects', props.get('special_effects', {})),
            'cooldown': request.POST.get('cooldown', props.get('cooldown', 0)),
            'max_usage_per_hour': request.POST.get('max_usage_per_hour', props.get('max_usage_per_hour', 0)),
            'glow_intensity': request.POST.get('glow_intensity', props.get('glow_intensity', 0)),
            'decoration_type': request.POST.get('decoration_type', props.get('decoration_type', 'NONE')),
            'auto_close': request.POST.get('auto_close', props.get('auto_close', False)),
            'close_delay': request.POST.get('close_delay', props.get('close_delay', 5)),
            'open_speed': request.POST.get('open_speed', props.get('open_speed', 1.0)),
            'close_speed': request.POST.get('close_speed', props.get('close_speed', 1.0)),
            'opacity': request.POST.get('opacity', props.get('opacity', 1.0)),
        })
        entrance.properties = props
        entrance.save()
        messages.success(request, f'Entrada/Salida "{entrance.name}" actualizada exitosamente.')
        return redirect('rooms:room_detail', pk=room.pk)

    context = {
        'entrance_exit': entrance,
        'room': room,
        'page_title': f'Editar Entrada/Salida - {entrance.name}',
        'is_edit': True
    }

    return render(request, 'rooms/entrance_exit_form.html', context)


@login_required
def delete_entrance_exit(request, pk):
    entrance = get_object_or_404(Cell, pk=pk, cell_type='DOOR')
    room = entrance.room

    if not _user_can_manage(room, request.user):
        messages.error(request, 'No tienes permisos para eliminar esta entrada/salida.')
        return redirect('rooms:room_detail', pk=room.pk)

    if CellConnection.objects.filter(entrance=entrance).exists():
        messages.error(request, 'No se puede eliminar una entrada/salida que tiene conexiones activas.')
        return redirect('rooms:room_detail', pk=room.pk)

    if request.method == 'POST':
        room_pk = room.pk
        entrance_name = entrance.name
        entrance.delete()
        messages.success(request, f'Entrada/Salida "{entrance_name}" eliminada exitosamente.')
        return redirect('rooms:room_detail', pk=room_pk)

    context = {
        'entrance_exit': entrance,
        'room': room,
        'page_title': f'Eliminar Entrada/Salida - {entrance.name}'
    }

    return render(request, 'rooms/entrance_exit_confirm_delete.html', context)


def entrance_exit_list(request):
    entrance_exits = Cell.objects.filter(cell_type='DOOR')
    return render(request, 'rooms/entrance_exit_list.html', {'entrance_exits': entrance_exits})


def entrance_exit_detail(request, pk):
    entrance_exit = get_object_or_404(Cell, pk=pk, cell_type='DOOR')
    return render(request, 'rooms/entrance_exit_detail.html', {'entrance_exit': entrance_exit})


@login_required
def create_portal(request):
    if request.method == 'POST':
        name = request.POST.get('name', 'Portal')
        properties = {
            'energy_cost': request.POST.get('energy_cost', 10),
            'cooldown': request.POST.get('cooldown', 60),
            'is_active': True,
        }
        room_id = request.POST.get('room_id')
        room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
        portal = Cell.objects.create(
            room=room,
            name=name,
            cell_type='PORTAL',
            position_x=request.POST.get('position_x', 0),
            position_y=request.POST.get('position_y', 0),
            properties=properties
        )
        messages.success(request, 'Portal creado con éxito')
        return HttpResponseRedirect(reverse_lazy('portal_list'))

    return render(request, 'rooms/portal_create.html', {
        'form': None,
        'page_title': 'Crear Nuevo Portal'
    })


def portal_list(request):
    portals = Cell.objects.filter(cell_type='PORTAL')
    return render(request, 'rooms/portal_list.html', {'portals': portals})


def portal_detail(request, pk):
    portal = get_object_or_404(Cell, pk=pk, cell_type='PORTAL')
    return render(request, 'rooms/portal_detail.html', {'portal': portal})


@login_required
def create_room_connection(request, room_id):
    room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')

    if not _user_can_manage(room, request.user):
        messages.error(request, 'No tienes permisos para gestionar conexiones en esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if request.method == 'POST':
        from_cell_id = request.POST.get('from_cell') or room_id
        to_cell_id = request.POST.get('to_cell')
        entrance_id = request.POST.get('entrance')
        bidirectional = request.POST.get('bidirectional', True)
        energy_cost = request.POST.get('energy_cost', 0)

        from_cell = get_object_or_404(Cell, pk=from_cell_id, cell_type='ROOM')
        to_cell = get_object_or_404(Cell, pk=to_cell_id, cell_type='ROOM')
        entrance = get_object_or_404(Cell, pk=entrance_id, cell_type='DOOR')

        connection = CellConnection.objects.create(
            from_cell=from_cell,
            to_cell=to_cell,
            entrance=entrance,
            bidirectional=bidirectional,
            energy_cost=energy_cost
        )
        messages.success(request, f'Conexión creada exitosamente entre {connection.from_cell.name} y {connection.to_cell.name}')
        return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': room_id}))

    context = {
        'room': room,
        'page_title': f'Crear Conexión - {room.name}',
        'is_create': True
    }

    return render(request, 'rooms/room_connection_form.html', context)


@login_required
def edit_room_connection(request, room_id, connection_id):
    room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
    connection = get_object_or_404(CellConnection, pk=connection_id)

    if connection.from_cell != room and connection.to_cell != room:
        messages.error(request, 'Esta conexión no pertenece a esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if not _user_can_manage(room, request.user):
        messages.error(request, 'No tienes permisos para gestionar conexiones en esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if request.method == 'POST':
        connection.from_cell_id = request.POST.get('from_cell', connection.from_cell_id)
        connection.to_cell_id = request.POST.get('to_cell', connection.to_cell_id)
        connection.entrance_id = request.POST.get('entrance', connection.entrance_id)
        connection.bidirectional = request.POST.get('bidirectional', connection.bidirectional)
        connection.energy_cost = request.POST.get('energy_cost', connection.energy_cost)
        connection.save()
        messages.success(request, f'Conexión actualizada exitosamente entre {connection.from_cell.name} y {connection.to_cell.name}')
        return HttpResponseRedirect(reverse_lazy('rooms:room_detail', kwargs={'pk': room_id}))

    context = {
        'room': room,
        'connection': connection,
        'page_title': f'Editar Conexión - {room.name}',
        'is_create': False
    }

    return render(request, 'rooms/room_connection_form.html', context)


@login_required
def delete_room_connection(request, room_id, connection_id):
    room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
    connection = get_object_or_404(CellConnection, pk=connection_id)

    if connection.from_cell != room and connection.to_cell != room:
        messages.error(request, 'Esta conexión no pertenece a esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if not _user_can_manage(room, request.user):
        messages.error(request, 'No tienes permisos para gestionar conexiones en esta habitación.')
        return redirect('rooms:room_detail', pk=room_id)

    if request.method == 'POST':
        from_room_name = connection.from_cell.name
        to_room_name = connection.to_cell.name
        connection.delete()
        messages.success(request, f'Conexión eliminada entre {from_room_name} y {to_room_name}')
        return redirect('rooms:room_detail', pk=room_id)

    context = {
        'room': room,
        'connection': connection,
        'page_title': f'Eliminar Conexión - {room.name}'
    }

    return render(request, 'rooms/room_connection_confirm_delete.html', context)


def room_list(request):
    logger.debug("Fetching all rooms from the database.")
    if not request.user.is_authenticated:
        logger.warning("User not authenticated. Redirecting to login.")
        return redirect('login')

    page_title = 'Lista de Salas'
    rooms = _room_qs()
    if not rooms.exists():
        logger.warning("No rooms found in the database.")
        messages.info(request, 'No hay salas disponibles en este momento.')
    else:
        logger.debug(f"Rooms count: {rooms.count()}")

    return render(request, 'rooms/room_list.html', {
        'page_title': page_title,
        'rooms': rooms,
    })


@api_view(['GET'])
def room_search(request):
    query = request.GET.get('q', '')
    rooms = _room_qs().filter(Q(name__icontains=query) | Q(description__icontains=query))
    return render(request, 'rooms/room_search.html', {'rooms': rooms, 'query': query})


def process_message_command(content, user):
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
    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))
    screen_x = (x - y) * cos30 * scale
    screen_y = ((x + y) * sin30 - z) * scale
    return screen_x, screen_y


def generate_room_3d_svg(room, canvas_width=800, canvas_height=600):
    scale = 8
    center_x = canvas_width // 2
    center_y = canvas_height // 2

    vertices = []
    for dx in [0, room.length]:
        for dy in [0, room.width]:
            for dz in [0, room.height]:
                x, y = project_isometric(dx, dy, dz, scale)
                vertices.append((x, y))

    min_x = min(v[0] for v in vertices)
    max_x = max(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)

    offset_x = center_x - (min_x + max_x) // 2
    offset_y = center_y - (min_y + max_y) // 2

    vertices = [(x + offset_x, y + offset_y) for x, y in vertices]

    faces = [
        [0, 1, 3, 2],
        [1, 5, 7, 3],
        [4, 5, 7, 6],
        [0, 2, 6, 4],
        [2, 3, 7, 6],
        [0, 1, 5, 4]
    ]

    base_color = room.color_primary
    accent_color = room.color_secondary

    colors = [
        base_color,
        accent_color,
        base_color,
        accent_color,
        base_color,
        accent_color,
    ]

    svg_parts = []
    svg_parts.append(f'<svg width="{canvas_width}" height="{canvas_height}" xmlns="http://www.w3.org/2000/svg">')
    svg_parts.append(f'<rect width="100%" height="100%" fill="#f5f5f5"/>')

    for i, face_indices in enumerate(faces):
        points = []
        for idx in face_indices:
            vx, vy = vertices[idx]
            points.append(f"{vx},{vy}")
        points_str = " ".join(points)
        svg_parts.append(f'<polygon points="{points_str}" fill="{colors[i]}" stroke="#1976d2" stroke-width="1"/>')

    edges = [
        (0, 1), (1, 3), (3, 2), (2, 0),
        (4, 5), (5, 7), (7, 6), (6, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]

    for edge in edges:
        x1, y1 = vertices[edge[0]]
        x2, y2 = vertices[edge[1]]
        svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0d47a1" stroke-width="2"/>')

    svg_parts.append(f'<text x="20" y="30" font-family="Arial" font-size="16" fill="#000">Habitación: {room.name}</text>')
    svg_parts.append(f'<text x="20" y="50" font-family="Arial" font-size="12" fill="#666">Dimensiones: {room.length}×{room.width}×{room.height}</text>')
    svg_parts.append(f'<text x="20" y="70" font-family="Arial" font-size="12" fill="#666">Posición: ({room.position_x}, {room.position_y}, {room.position_z})</text>')

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


class RoomListViewSet(ListModelMixin, GenericViewSet):
    serializer_class = CellSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.user.pk
        logger.debug(f"Fetching rooms for user_id: {user_id}")
        queryset = _room_qs().annotate(
            member_count=Count('id')
        ).order_by('-updated_at')
        logger.debug(f"Queryset: {queryset.query}")
        return queryset


class RoomDetailViewSet(RetrieveModelMixin, GenericViewSet):
    serializer_class = CellSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _room_qs().annotate(
            member_count=Count('id')
        )


class RoomSearchViewSet(viewsets.ModelViewSet):
    serializer_class = CellSearchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return _room_qs().annotate(
            is_member=Exists(Outbox.objects.filter(pk=Outbox.objects.filter(pk=0).values('pk')[:1]))
        ).order_by('name')


class CentrifugoMixin:
    def get_room_member_channels(self, room_id):
        return []

    def broadcast_room(self, room_id, broadcast_payload):
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
            transaction.on_commit(broadcast)
        elif settings.CENTRIFUGO_BROADCAST_MODE == 'outbox':
            partition = hash(room_id) % settings.CENTRIFUGU_OUTBOX_PARTITIONS
            Outbox.objects.create(method='broadcast', payload=broadcast_payload, partition=partition)
        elif settings.CENTRIFUGO_BROADCAST_MODE == 'cdc':
            partition = hash(room_id)
            CDC.objects.create(method='broadcast', payload=broadcast_payload, partition=partition)
        elif settings.CENTRIFUGO_BROADCAST_MODE == 'api_cdc':
            if len(broadcast_payload['channels']) <= 1000000:
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
        get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
        return Message.objects.filter(
            room_id=room_id).prefetch_related('user', 'room').order_by('-created_at')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        room_id = self.kwargs['room_id']
        room = Cell.objects.select_for_update().filter(cell_type='ROOM').get(id=room_id)
        channels = self.get_room_member_channels(room_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(room=room, user=request.user)

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
        room = Cell.objects.select_for_update().filter(cell_type='ROOM').get(id=room_id)
        channels = self.get_room_member_channels(room_id)
        body = {'room_id': room_id, 'user_id': request.user.pk}

        broadcast_payload = {
            'channels': channels,
            'data': {
                'type': 'user_joined',
                'body': body
            },
            'idempotency_key': f'user_joined_{request.user.pk}'
        }
        self.broadcast_room(room_id, broadcast_payload)
        return Response(body, status=status.HTTP_200_OK)


class LeaveRoomView(APIView, CentrifugoMixin):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, room_id):
        room = Cell.objects.select_for_update().filter(cell_type='ROOM').get(id=room_id)
        channels = self.get_room_member_channels(room_id)
        body = {'room_id': room_id, 'user_id': request.user.pk}

        broadcast_payload = {
            'channels': channels,
            'data': {
                'type': 'user_left',
                'body': body
            },
            'idempotency_key': f'user_left_{request.user.pk}'
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
    obj = get_object_or_404(Cell, pk=object_id)
    result = obj.interact(request.user.player_profile)
    return Response(result)


@api_view(['POST'])
def use_entrance_exit(request, entrance_id):
    try:
        entrance = get_object_or_404(Cell, pk=entrance_id, cell_type='DOOR')

        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile

        target_room = None
        for conn in entrance.cell_connections.select_related('to_cell').all():
            if conn.from_cell_id == player_profile.current_room_id:
                target_room = conn.to_cell
                break
            elif conn.bidirectional and conn.to_cell_id == player_profile.current_room_id:
                target_room = conn.from_cell
                break

        if not target_room:
            return Response({
                'success': False,
                'message': 'No hay conexión disponible desde tu ubicación actual.'
            }, status=400)

        if not target_room.is_active:
            return Response({
                'success': False,
                'message': 'La habitación destino no está disponible.'
            }, status=400)

        energy_cost = 5
        if player_profile.energy < energy_cost:
            return Response({
                'success': False,
                'message': f'No tienes suficiente energía. Necesitas {energy_cost}, tienes {player_profile.energy}.'
            }, status=400)

        player_profile.current_room = target_room
        player_profile.energy -= energy_cost
        player_profile.save()

        return Response({
            'success': True,
            'message': f'Transición exitosa a {target_room.name}',
            'target_room': {
                'id': target_room.id,
                'name': target_room.name,
                'description': target_room.description
            },
            'energy_cost': energy_cost,
            'experience_gained': 0,
            'player_stats': {
                'energy': player_profile.energy,
                'productivity': player_profile.productivity,
                'position_x': player_profile.position_x,
                'position_y': player_profile.position_y
            }
        })

    except Exception as e:
        logger.error(f"Error en use_entrance_exit: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)


@api_view(['GET'])
def get_entrance_info(request, entrance_id):
    try:
        entrance = get_object_or_404(Cell, pk=entrance_id, cell_type='DOOR')

        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        props = entrance.properties or {}
        connections = entrance.cell_connections.all()
        connection_data = None
        if connections.exists():
            conn = connections.first()
            connection_data = {
                'exists': True,
                'bidirectional': conn.bidirectional,
                'energy_cost': conn.energy_cost
            }

        return Response({
            'success': True,
            'entrance': {
                'id': entrance.id,
                'name': entrance.name,
                'description': entrance.description,
                'face': props.get('face', ''),
                'enabled': props.get('enabled', True),
                'is_locked': entrance.is_locked,
                'door_type': props.get('door_type', 'SINGLE'),
                'material': props.get('material', 'WOOD'),
                'width': entrance.width,
                'height': entrance.height,
                'access_level': props.get('access_level', 0),
                'interaction_type': props.get('interaction_type', 'PUSH'),
                'health': props.get('health', 100)
            },
            'connection': connection_data
        })

    except Exception as e:
        logger.error(f"Error en get_entrance_info: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': 'Error interno del sistema.'
        }, status=500)


@api_view(['GET'])
def get_available_transitions(request):
    try:
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile
        current_room = player_profile.current_room
        if not current_room or current_room.cell_type != 'ROOM':
            return Response({
                'success': True,
                'current_room': None,
                'available_transitions': [],
                'player_energy': player_profile.energy
            })

        transitions_data = []

        for conn in current_room.outgoing_connections.select_related('entrance', 'to_cell').all():
            entrance = conn.entrance
            props = entrance.properties or {}
            if not props.get('enabled', True):
                continue

            transitions_data.append({
                'entrance': {
                    'id': entrance.id,
                    'name': entrance.name,
                    'face': props.get('face', ''),
                    'door_type': props.get('door_type', 'SINGLE'),
                    'material': props.get('material', 'WOOD')
                },
                'target_room': {
                    'id': conn.to_cell.id,
                    'name': conn.to_cell.name,
                    'description': conn.to_cell.description
                },
                'energy_cost': conn.energy_cost,
                'experience_reward': props.get('experience_reward', 0),
                'accessible': True,
                'reason': ''
            })

        return Response({
            'success': True,
            'current_room': {
                'id': current_room.id,
                'name': current_room.name
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
    try:
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile

        try:
            target_room = _room_qs().get(id=room_id)
        except Cell.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Habitación no encontrada.'
            }, status=404)

        check_only = request.data.get('check_only', False)
        if check_only:
            can_teleport, reason = player_profile.can_teleport_to(target_room)
            return Response({
                'success': can_teleport,
                'message': reason,
                'energy_cost': 20,
                'current_energy': player_profile.energy
            })

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
    try:
        if not hasattr(request.user, 'player_profile'):
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        player_profile = request.user.player_profile

        history_data = []
        for room_id in (player_profile.navigation_history or []):
            try:
                room = _room_qs().get(id=room_id)
                history_data.append({
                    'id': room.id,
                    'name': room.name,
                    'description': room.description[:50] + '...' if len(room.description) > 50 else room.description
                })
            except Cell.DoesNotExist:
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

        current_room = player_profile.current_room
        return Response({
            'success': True,
            'current_room': {
                'id': current_room.id,
                'name': current_room.name,
                'description': current_room.description,
                'room_type': current_room.properties.get('room_type', '') if current_room.properties else '',
                'permissions': current_room.properties.get('permissions', 'public') if current_room.properties else 'public'
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
    try:
        room = get_object_or_404(Cell, pk=pk, cell_type='ROOM')
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
    activities = []
    now = timezone.now()
    past_24h = now - timedelta(hours=24)

    recent_rooms = _room_qs().filter(
        created_at__gte=past_24h
    ).select_related('owner')[:limit]

    for room in recent_rooms:
        creator = getattr(room, 'creator', None) or room.owner
        if creator:
            activities.append({
                'user': creator.username,
                'action': f'created room "{room.name}"',
                'timestamp': room.created_at,
                'icon': 'bi-house-add',
                'color': 'success'
            })

    recent_doors = Cell.objects.filter(
        cell_type='DOOR',
        created_at__gte=past_24h
    ).select_related('parent')[:limit]

    for door in recent_doors:
        parent_room = door.parent
        if parent_room and parent_room.cell_type == 'ROOM':
            creator = getattr(parent_room, 'creator', None) or parent_room.owner
            if creator:
                activities.append({
                    'user': creator.username,
                    'action': f'created door in {parent_room.name}',
                    'timestamp': door.created_at,
                    'icon': 'bi-door-open',
                    'color': 'info'
                })

    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:limit]


@login_required
def navigate_room(request, direction):
    player = request.user.player_profile

    if not player.current_room:
        return JsonResponse({
            'success': False,
            'message': 'No estás en ninguna habitación actualmente'
        }, status=400)

    success = player.move_to_room(direction)

    if success:
        new_room = player.current_room
        entrance = None
        for conn in new_room.outgoing_connections.select_related('entrance').all():
            props = conn.entrance.properties or {}
            if props.get('face') == direction.upper():
                entrance = conn.entrance
                break

        room_info = {
            'id': new_room.id,
            'name': new_room.name,
            'description': new_room.description,
            'image_url': new_room.get_image_url() if hasattr(new_room, 'get_image_url') and new_room.get_image_url() else '/static/images/default-room.jpg',
            'connections': get_available_exits(new_room),
            'objects': list(new_room.children.values('id', 'name', 'cell_type', 'position_x', 'position_y')),
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
    exits = []
    for conn in room.outgoing_connections.select_related('entrance', 'to_cell').all():
        entrance = conn.entrance
        props = entrance.properties or {}
        if props.get('enabled', True):
            exits.append({
                'direction': props.get('face', ''),
                'to_room': conn.to_cell.name,
                'to_room_id': conn.to_cell.id,
                'energy_cost': conn.energy_cost
            })
    return exits


@login_required
def navigate_to_cell(request, cell_id):
    player = request.user.player_profile

    if not player.current_room:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'No estás en ninguna habitación actualmente'
            }, status=400)
        messages.error(request, 'No estás en ninguna habitación actualmente')
        return redirect('rooms:lobby')

    success, message = player.move_to_cell(cell_id)

    if success:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'target_room': {
                    'id': player.current_room.id,
                    'name': player.current_room.name,
                },
                'message': message,
            })
        return redirect('rooms:room_detail', pk=player.current_room.id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': message,
        }, status=400)

    messages.error(request, message)
    return redirect('rooms:room_detail', pk=player.current_room.id)


@login_required
def room_view(request, room_id=None):
    player = request.user.player_profile
    room = player.current_room if room_id is None else get_object_or_404(Cell, id=room_id, cell_type='ROOM')

    if player.current_room != room:
        player.current_room = room
        player.save()

    return JsonResponse({
        'room': {
            'id': room.id,
            'name': room.name,
            'description': room.description,
            'image_url': room.get_image_url() if hasattr(room, 'get_image_url') and room.get_image_url() else '/static/default-room.jpg'
        },
        'exits': player.get_available_exits(),
        'player': {
            'energy': player.energy,
            'position': [player.position_x, player.position_y]
        }
    })


@login_required
def navigate(request):
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
    room = get_object_or_404(Cell, pk=pk, cell_type='ROOM')

    if not _user_can_manage(room, request.user):
        messages.error(request, 'No tienes permisos para eliminar esta habitación.')
        return redirect('rooms:room_detail', pk=pk)

    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f'La habitación "{room_name}" ha sido eliminada exitosamente.')
        return redirect('rooms:room_list')

    return render(request, 'rooms/room_confirm_delete.html', {'room': room})


@login_required
def create_room_complete(request):
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            cell = form.save(commit=False)
            cell.cell_type = 'ROOM'
            cell.owner = request.user
            cell.save()
            messages.success(request, f'Habitación "{cell.name}" creada exitosamente.')
            return redirect('rooms:room_detail', pk=cell.pk)
    else:
        form = RoomForm(user=request.user)

    context = {
        'form': form,
        'page_title': 'Crear Habitación Completa',
        'is_edit': False,
        'room_count': _room_qs().count(),
        'active_rooms': _room_qs().filter(is_active=True).count()
    }

    return render(request, 'rooms/room_form_complete.html', context)


class RoomCRUDViewSet(ModelViewSet):
    serializer_class = CellCRUDSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return _room_qs().filter(
            Q(owner=user)
        ).distinct().order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if not _user_can_manage(instance, request.user):
            return Response(
                {"error": "No tienes permisos para editar esta habitación"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        if not _user_can_manage(instance, request.user):
            return Response(
                {"error": "No tienes permisos para editar esta habitación"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if not _user_can_manage(instance, request.user):
            return Response(
                {"error": "No tienes permisos para eliminar esta habitación"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)


class RoomConnectionCRUDViewSet(ModelViewSet):
    serializer_class = CellConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return CellConnection.objects.filter(
            Q(from_cell__owner=user) | Q(to_cell__owner=user)
        ).select_related('from_cell', 'to_cell', 'entrance').distinct().order_by('-id')

    def perform_create(self, serializer):
        serializer.save()


@login_required
def room_crud_view(request):
    return render(request, 'rooms/room_crud.html', {
        'page_title': 'Gestión de Habitaciones',
    })


@api_view(['GET'])
def get_room_3d_data(request, room_id):
    try:
        room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')

        permissions = getattr(room, 'permissions', room.properties.get('permissions', 'public'))
        if permissions == 'private':
            return Response({
                'success': False,
                'message': 'No tienes acceso a esta habitación.'
            }, status=403)

        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

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
                'x': room.position_x,
                'y': room.position_y,
                'z': room.position_z
            },
            'colors': {
                'primary': room.color_primary,
                'secondary': room.color_secondary
            },
            'material': room.material_type,
            'lighting_intensity': room.properties.get('lighting_intensity', 80) if room.properties else 80,
            'temperature': float(room.properties.get('temperature', 22.0)) if room.properties else 22.0
        }

        player_data = {
            'position': {
                'x': player_profile.position_x or room.length // 2,
                'y': player_profile.position_y or room.width // 2,
                'z': 1.7
            },
            'energy': player_profile.energy,
            'productivity': player_profile.productivity,
            'social': player_profile.social
        }

        objects_3d = []

        for entrance in room.children.filter(cell_type='DOOR', is_active=True):
            props = entrance.properties or {}
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
                    'width': (entrance.width or 100) / 100,
                    'height': (entrance.height or 200) / 100,
                    'depth': 0.2
                },
                'properties': {
                    'face': props.get('face', ''),
                    'is_locked': entrance.is_locked,
                    'door_type': props.get('door_type', 'SINGLE'),
                    'material': props.get('material', 'WOOD'),
                    'color': props.get('color', '#8B4513'),
                    'interaction_distance': props.get('interaction_distance', 150) / 100
                }
            }

            connections = entrance.cell_connections.all()
            if connections.exists():
                conn = connections.first()
                target_room = conn.to_cell if conn.from_cell_id == room.id else conn.from_cell
                obj_data['connection'] = {
                    'target_room_id': target_room.id,
                    'energy_cost': conn.energy_cost,
                    'bidirectional': conn.bidirectional
                }

            objects_3d.append(obj_data)

        for portal in room.children.filter(cell_type='PORTAL', is_active=True):
            props = portal.properties or {}
            obj_data = {
                'type': 'portal',
                'id': portal.id,
                'name': portal.name,
                'position': {
                    'x': portal.position_x or 0,
                    'y': portal.position_y or 0,
                    'z': room.height // 2
                },
                'dimensions': {
                    'width': 2,
                    'height': 3,
                    'depth': 0.1
                },
                'properties': {
                    'energy_cost': props.get('energy_cost', 10),
                    'cooldown': props.get('cooldown', 60),
                    'is_active': props.get('is_active', True),
                    'target_room_id': None
                }
            }
            objects_3d.append(obj_data)

        connections = []
        for conn in room.outgoing_connections.select_related('entrance', 'to_cell').all():
            entrance = conn.entrance
            props = entrance.properties or {}
            target_room = conn.to_cell
            connections.append({
                'direction': props.get('face', ''),
                'target_room_id': target_room.id,
                'target_room_name': target_room.name,
                'energy_cost': conn.energy_cost,
                'entrance_id': entrance.id
            })

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
    try:
        exit_type = request.data.get('exit_type')
        exit_id = request.data.get('exit_id')
        target_room_id = request.data.get('target_room_id')

        if not exit_type or not exit_id:
            return Response({
                'success': False,
                'message': 'Faltan parámetros: exit_type y exit_id son requeridos.'
            }, status=400)

        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        if exit_type == 'door':
            entrance = get_object_or_404(Cell, pk=exit_id, cell_type='DOOR')

            target_room = None
            for conn in entrance.cell_connections.select_related('to_cell', 'from_cell').all():
                if conn.from_cell_id == player_profile.current_room_id:
                    target_room = conn.to_cell
                    break
                elif conn.bidirectional and conn.to_cell_id == player_profile.current_room_id:
                    target_room = conn.from_cell
                    break

            if not target_room:
                return Response({
                    'success': False,
                    'message': 'No hay conexión disponible desde tu ubicación actual.'
                }, status=400)

            new_room_data = {
                'id': target_room.id,
                'name': target_room.name,
                'description': target_room.description
            }

            return Response({
                'success': True,
                'message': f'Transición exitosa a {target_room.name}',
                'target_room': new_room_data,
                'energy_cost': 5,
                'player_stats': {
                    'energy': player_profile.energy,
                    'position_x': player_profile.position_x,
                    'position_y': player_profile.position_y
                }
            })

        elif exit_type == 'portal':
            portal = get_object_or_404(Cell, pk=exit_id, cell_type='PORTAL')
            props = portal.properties or {}

            if not props.get('is_active', True):
                return Response({
                    'success': False,
                    'message': 'El portal no está disponible actualmente.'
                }, status=400)

            energy_cost = props.get('energy_cost', 10)
            if player_profile.energy < energy_cost:
                return Response({
                    'success': False,
                    'message': f'Energía insuficiente. Necesitas {energy_cost}, tienes {player_profile.energy}.'
                }, status=400)

            target_room = portal.room
            if target_room and target_room.id == player_profile.current_room_id:
                return Response({
                    'success': False,
                    'message': 'Ya estás en la habitación destino del portal.'
                }, status=400)

            if target_room:
                player_profile.add_to_navigation_history(player_profile.current_room.id)
                player_profile.current_room = target_room
                player_profile.position_x = target_room.position_x
                player_profile.position_y = target_room.position_y
                player_profile.energy -= energy_cost
                player_profile.save()

                return Response({
                    'success': True,
                    'message': f'Teletransportado a {target_room.name} a través del portal.',
                    'target_room': {
                        'id': target_room.id,
                        'name': target_room.name,
                        'description': target_room.description
                    },
                    'energy_cost': energy_cost,
                    'player_stats': {
                        'energy': player_profile.energy,
                        'position_x': player_profile.position_x,
                        'position_y': player_profile.position_y
                    }
                })

            return Response({
                'success': False,
                'message': 'El portal no tiene una habitación destino válida.'
            }, status=400)

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
    try:
        position_x = request.data.get('position_x')
        position_y = request.data.get('position_y')
        position_z = request.data.get('position_z', 1.7)

        if position_x is None or position_y is None:
            return Response({
                'success': False,
                'message': 'Faltan coordenadas de posición.'
            }, status=400)

        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

        if player_profile.current_room:
            room = player_profile.current_room
            position_x = max(0, min(position_x, room.length))
            position_y = max(0, min(position_y, room.width))
            position_z = max(0, min(position_z, room.height))

        player_profile.position_x = position_x
        player_profile.position_y = position_y
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
    try:
        try:
            player_profile = request.user.player_profile
        except PlayerProfile.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No tienes un perfil de jugador activo.'
            }, status=400)

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
    from django.db import transaction

    with transaction.atomic():
        root_room, created = Cell.objects.get_or_create(
            name='Navigation Test Zone',
            cell_type='ROOM',
            defaults={
                'description': 'Zona de pruebas para testing de navegación por habitaciones interconectadas',
                'owner': request.user,
                'properties': {
                    'permissions': 'public',
                    'room_type': 'OFFICE',
                },
                'position_x': 0,
                'position_y': 0,
                'position_z': 0,
                'length': 20,
                'width': 20,
                'height': 5,
                'color_primary': '#4CAF50',
                'color_secondary': '#2196F3',
                'material_type': 'CONCRETE',
                'properties': {
                    'permissions': 'public',
                    'room_type': 'OFFICE',
                    'lighting_intensity': 80,
                    'temperature': 22.0
                }
            }
        )

        alpha_sector, _ = Cell.objects.get_or_create(
            name='Alpha Sector',
            cell_type='ROOM',
            defaults={
                'description': 'Sector Alpha - Área de desarrollo y testing',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': root_room,
                'position_x': 25,
                'position_y': 0,
                'position_z': 0,
                'length': 15,
                'width': 15,
                'height': 4,
                'color_primary': '#FF9800',
                'color_secondary': '#F44336',
                'material_type': 'METAL',
                'properties': {
                    'permissions': 'public',
                    'room_type': 'OFFICE',
                    'lighting_intensity': 70
                }
            }
        )

        beta_sector, _ = Cell.objects.get_or_create(
            name='Beta Sector',
            cell_type='ROOM',
            defaults={
                'description': 'Sector Beta - Área de producción',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'MEETING'},
                'parent': root_room,
                'position_x': 0,
                'position_y': 25,
                'position_z': 0,
                'length': 12,
                'width': 18,
                'height': 4,
                'color_primary': '#9C27B0',
                'color_secondary': '#673AB7',
                'material_type': 'GLASS',
                'properties': {
                    'permissions': 'public',
                    'room_type': 'MEETING',
                    'lighting_intensity': 60
                }
            }
        )

        gamma_sector, _ = Cell.objects.get_or_create(
            name='Gamma Sector',
            cell_type='ROOM',
            defaults={
                'description': 'Sector Gamma - Área administrativa',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'LOUNGE'},
                'parent': root_room,
                'position_x': -20,
                'position_y': 0,
                'position_z': 0,
                'length': 18,
                'width': 12,
                'height': 4,
                'color_primary': '#00BCD4',
                'color_secondary': '#009688',
                'material_type': 'WOOD',
                'properties': {
                    'permissions': 'public',
                    'room_type': 'LOUNGE',
                    'lighting_intensity': 75
                }
            }
        )

        alpha_1, _ = Cell.objects.get_or_create(
            name='Alpha-1',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Alpha-1 - Desarrollo frontend',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': alpha_sector,
                'position_x': 30,
                'position_y': 5,
                'position_z': 0,
                'length': 10,
                'width': 8,
                'height': 3,
                'color_primary': '#FF5722',
                'color_secondary': '#E64A19'
            }
        )

        alpha_2, _ = Cell.objects.get_or_create(
            name='Alpha-2',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Alpha-2 - Desarrollo backend',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': alpha_sector,
                'position_x': 30,
                'position_y': -5,
                'position_z': 0,
                'length': 10,
                'width': 8,
                'height': 3,
                'color_primary': '#2196F3',
                'color_secondary': '#1976D2'
            }
        )

        alpha_3, _ = Cell.objects.get_or_create(
            name='Alpha-3',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Alpha-3 - Testing y QA',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'MEETING'},
                'parent': alpha_sector,
                'position_x': 45,
                'position_y': 0,
                'position_z': 0,
                'length': 8,
                'width': 10,
                'height': 3,
                'color_primary': '#4CAF50',
                'color_secondary': '#388E3C'
            }
        )

        beta_1, _ = Cell.objects.get_or_create(
            name='Beta-1',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Beta-1 - Producción primaria',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': beta_sector,
                'position_x': 5,
                'position_y': 30,
                'position_z': 0,
                'length': 8,
                'width': 12,
                'height': 3,
                'color_primary': '#9C27B0',
                'color_secondary': '#7B1FA2'
            }
        )

        beta_2, _ = Cell.objects.get_or_create(
            name='Beta-2',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Beta-2 - Producción secundaria',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': beta_sector,
                'position_x': -5,
                'position_y': 30,
                'position_z': 0,
                'length': 8,
                'width': 12,
                'height': 3,
                'color_primary': '#FF9800',
                'color_secondary': '#F57C00'
            }
        )

        gamma_1, _ = Cell.objects.get_or_create(
            name='Gamma-1',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Gamma-1 - Administración general',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'LOUNGE'},
                'parent': gamma_sector,
                'position_x': -25,
                'position_y': 5,
                'position_z': 0,
                'length': 10,
                'width': 6,
                'height': 3,
                'color_primary': '#00BCD4',
                'color_secondary': '#00ACC1'
            }
        )

        gamma_2, _ = Cell.objects.get_or_create(
            name='Gamma-2',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Gamma-2 - Recursos humanos',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'MEETING'},
                'parent': gamma_sector,
                'position_x': -25,
                'position_y': -5,
                'position_z': 0,
                'length': 10,
                'width': 6,
                'height': 3,
                'color_primary': '#8BC34A',
                'color_secondary': '#689F38'
            }
        )

        gamma_3, _ = Cell.objects.get_or_create(
            name='Gamma-3',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Gamma-3 - Finanzas',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': gamma_sector,
                'position_x': -40,
                'position_y': 0,
                'position_z': 0,
                'length': 12,
                'width': 8,
                'height': 3,
                'color_primary': '#FFC107',
                'color_secondary': '#FF8F00'
            }
        )

        gamma_4, _ = Cell.objects.get_or_create(
            name='Gamma-4',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sector Gamma-4 - Legal',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'MEETING'},
                'parent': gamma_sector,
                'position_x': -25,
                'position_y': -15,
                'position_z': 0,
                'length': 8,
                'width': 8,
                'height': 3,
                'color_primary': '#795548',
                'color_secondary': '#5D4037'
            }
        )

        alpha_1a, _ = Cell.objects.get_or_create(
            name='Alpha-1A',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sub-sector Alpha-1A - UI/UX Design',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': alpha_1,
                'position_x': 35,
                'position_y': 8,
                'position_z': 0,
                'length': 6,
                'width': 5,
                'height': 3,
                'color_primary': '#E91E63',
                'color_secondary': '#C2185B'
            }
        )

        alpha_1b, _ = Cell.objects.get_or_create(
            name='Alpha-1B',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sub-sector Alpha-1B - Frontend Development',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': alpha_1,
                'position_x': 35,
                'position_y': 2,
                'position_z': 0,
                'length': 6,
                'width': 5,
                'height': 3,
                'color_primary': '#3F51B5',
                'color_secondary': '#303F9F'
            }
        )

        gamma_3x, _ = Cell.objects.get_or_create(
            name='Gamma-3X',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sub-sector Gamma-3X - Contabilidad',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'OFFICE'},
                'parent': gamma_3,
                'position_x': -45,
                'position_y': 3,
                'position_z': 0,
                'length': 6,
                'width': 6,
                'height': 3,
                'color_primary': '#FF5722',
                'color_secondary': '#D84315'
            }
        )

        gamma_3y, _ = Cell.objects.get_or_create(
            name='Gamma-3Y',
            cell_type='ROOM',
            defaults={
                'description': 'Sub-sub-sector Gamma-3Y - Auditoría',
                'owner': request.user,
                'properties': {'permissions': 'public', 'room_type': 'MEETING'},
                'parent': gamma_3,
                'position_x': -45,
                'position_y': -3,
                'position_z': 0,
                'length': 6,
                'width': 6,
                'height': 3,
                'color_primary': '#607D8B',
                'color_secondary': '#455A64'
            }
        )

        def create_door_connection(from_room, to_room, direction_from, direction_to, door_name_suffix=""):
            entrance_from, _ = Cell.objects.get_or_create(
                room=from_room,
                name=f'Puerta a {to_room.name}{door_name_suffix}',
                cell_type='DOOR',
                defaults={
                    'position_x': 0,
                    'position_y': 0,
                    'width': 100,
                    'height': 200,
                    'is_locked': False,
                    'properties': {
                        'face': direction_from,
                        'enabled': True,
                        'door_type': 'SINGLE',
                        'material': 'WOOD',
                        'color': '#8B4513',
                        'interaction_type': 'PUSH',
                        'animation_type': 'SWING',
                        'requires_both_hands': False,
                        'interaction_distance': 150,
                        'is_open': False,
                        'usage_count': 0,
                        'health': 100,
                        'access_level': 0,
                        'security_system': 'NONE',
                        'alarm_triggered': False,
                        'seals_air': True,
                        'seals_sound': 20,
                        'temperature_resistance': 50,
                        'pressure_resistance': 1,
                        'energy_cost_modifier': 0,
                        'experience_reward': 1,
                        'special_effects': {},
                        'cooldown': 0,
                        'max_usage_per_hour': 0,
                        'glow_intensity': 0,
                        'decoration_type': 'NONE',
                        'auto_close': False,
                        'close_delay': 5,
                        'open_speed': 1.0,
                        'close_speed': 1.0,
                        'opacity': 1.0,
                    }
                }
            )

            entrance_to, _ = Cell.objects.get_or_create(
                room=to_room,
                name=f'Puerta desde {from_room.name}{door_name_suffix}',
                cell_type='DOOR',
                defaults={
                    'position_x': 0,
                    'position_y': 0,
                    'width': 100,
                    'height': 200,
                    'is_locked': False,
                    'properties': {
                        'face': direction_to,
                        'enabled': True,
                        'door_type': 'SINGLE',
                        'material': 'WOOD',
                        'color': '#8B4513',
                        'interaction_type': 'PUSH',
                        'animation_type': 'SWING',
                        'requires_both_hands': False,
                        'interaction_distance': 150,
                        'is_open': False,
                        'usage_count': 0,
                        'health': 100,
                        'access_level': 0,
                        'security_system': 'NONE',
                        'alarm_triggered': False,
                        'seals_air': True,
                        'seals_sound': 20,
                        'temperature_resistance': 50,
                        'pressure_resistance': 1,
                        'energy_cost_modifier': 0,
                        'experience_reward': 1,
                        'special_effects': {},
                        'cooldown': 0,
                        'max_usage_per_hour': 0,
                        'glow_intensity': 0,
                        'decoration_type': 'NONE',
                        'auto_close': False,
                        'close_delay': 5,
                        'open_speed': 1.0,
                        'close_speed': 1.0,
                        'opacity': 1.0,
                    }
                }
            )

            connection, _ = CellConnection.objects.get_or_create(
                from_cell=from_room,
                to_cell=to_room,
                entrance=entrance_from,
                defaults={
                    'bidirectional': True,
                    'energy_cost': 5
                }
            )

            return entrance_from, entrance_to

        create_door_connection(root_room, alpha_sector, 'NORTH', 'SOUTH')
        create_door_connection(root_room, beta_sector, 'EAST', 'WEST')
        create_door_connection(root_room, gamma_sector, 'WEST', 'EAST')

        create_door_connection(alpha_1, alpha_2, 'EAST', 'WEST')
        create_door_connection(alpha_2, alpha_3, 'EAST', 'WEST')

        create_door_connection(beta_1, beta_2, 'NORTH', 'SOUTH')

        create_door_connection(gamma_1, gamma_2, 'NORTH', 'SOUTH')
        create_door_connection(gamma_2, gamma_3, 'WEST', 'EAST')
        create_door_connection(gamma_3, gamma_4, 'SOUTH', 'NORTH')

        create_door_connection(alpha_1a, alpha_1b, 'EAST', 'WEST')
        create_door_connection(gamma_3x, gamma_3y, 'NORTH', 'SOUTH')

        def create_portal(from_room, to_room, entrance_from, entrance_to, portal_name):
            portal, _ = Cell.objects.get_or_create(
                room=from_room,
                name=portal_name,
                cell_type='PORTAL',
                defaults={
                    'position_x': 0,
                    'position_y': 0,
                    'properties': {
                        'energy_cost': 15,
                        'cooldown': 60,
                        'is_active': True,
                    }
                }
            )
            return portal

        alpha_entrance, _ = Cell.objects.get_or_create(
            room=alpha_sector,
            name='Portal Ascendente',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'UP',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#2196F3',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        beta1_entrance, _ = Cell.objects.get_or_create(
            room=beta_1,
            name='Portal Descendente',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'DOWN',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#2196F3',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        create_portal(alpha_sector, beta_1, alpha_entrance, beta1_entrance, 'Portal Alpha-Beta')

        beta_entrance, _ = Cell.objects.get_or_create(
            room=beta_sector,
            name='Portal Ascendente',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'UP',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#9C27B0',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        gamma2_entrance, _ = Cell.objects.get_or_create(
            room=gamma_2,
            name='Portal Descendente',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'DOWN',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#9C27B0',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        create_portal(beta_sector, gamma_2, beta_entrance, gamma2_entrance, 'Portal Beta-Gamma')

        gamma_entrance, _ = Cell.objects.get_or_create(
            room=gamma_sector,
            name='Portal Ascendente',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'UP',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#FF9800',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        alpha1_entrance, _ = Cell.objects.get_or_create(
            room=alpha_1,
            name='Portal Descendente',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'DOWN',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#FF9800',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        create_portal(gamma_sector, alpha_1, gamma_entrance, alpha1_entrance, 'Portal Gamma-Alpha')

        alpha1_portal_entrance, _ = Cell.objects.get_or_create(
            room=alpha_1,
            name='Portal Dimensional',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'UP',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'GLASS',
                    'color': '#00BCD4',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        gamma3x_entrance, _ = Cell.objects.get_or_create(
            room=gamma_3x,
            name='Portal Dimensional',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'DOWN',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'GLASS',
                    'color': '#00BCD4',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        create_portal(alpha_1, gamma_3x, alpha1_portal_entrance, gamma3x_entrance, 'Portal Dimensional Alpha-Gamma')

        beta2_portal_entrance, _ = Cell.objects.get_or_create(
            room=beta_2,
            name='Portal Express',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'UP',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#4CAF50',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        alpha1a_entrance, _ = Cell.objects.get_or_create(
            room=alpha_1a,
            name='Portal Express',
            cell_type='DOOR',
            defaults={
                'position_x': 0,
                'position_y': 0,
                'width': 100,
                'height': 200,
                'is_locked': False,
                'properties': {
                    'face': 'DOWN',
                    'enabled': True,
                    'door_type': 'SINGLE',
                    'material': 'METAL',
                    'color': '#4CAF50',
                    'interaction_type': 'PUSH',
                    'animation_type': 'SWING',
                    'requires_both_hands': False,
                    'interaction_distance': 150,
                    'is_open': False,
                    'usage_count': 0,
                    'health': 100,
                    'access_level': 0,
                    'security_system': 'NONE',
                    'alarm_triggered': False,
                    'seals_air': True,
                    'seals_sound': 20,
                    'temperature_resistance': 50,
                    'pressure_resistance': 1,
                    'energy_cost_modifier': 0,
                    'experience_reward': 1,
                    'special_effects': {},
                    'cooldown': 0,
                    'max_usage_per_hour': 0,
                    'glow_intensity': 0,
                    'decoration_type': 'NONE',
                    'auto_close': False,
                    'close_delay': 5,
                    'open_speed': 1.0,
                    'close_speed': 1.0,
                    'opacity': 1.0,
                }
            }
        )

        create_portal(beta_2, alpha_1a, beta2_portal_entrance, alpha1a_entrance, 'Portal Express Beta-Alpha')

        def create_connection_object(room, name, obj_type, position_x, position_y):
            obj, _ = Cell.objects.get_or_create(
                room=room,
                name=name,
                defaults={
                    'position_x': position_x,
                    'position_y': position_y,
                    'cell_type': obj_type,
                    'effect': {'connection_type': 'teleport', 'target_room': 'Gamma-3Y'},
                }
            )
            return obj

        create_connection_object(alpha_1a, 'Cristal Dimensional', 'DOOR', 3, 2)
        create_connection_object(gamma_3y, 'Cristal Dimensional', 'PORTAL', 3, 2)

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


@login_required
def object_action_panel(request, room_id):
    room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
    if not _user_can_manage(room, request.user):
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
        {'type': 'CONTAINER', 'label': 'Contenedor', 'icon': 'bi-box', 'color': 'dark'},
        {'type': 'ITEM', 'label': 'Item/Decor', 'icon': 'bi-box-seam', 'color': 'secondary'},
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
    room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
    if not _user_can_manage(room, request.user):
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

    cell_type = form.cleaned_data['object_type']
    print('CELL_TYPE:', repr(cell_type))
    print('FORM_DATA:', form.cleaned_data)

    try:
        cell = Cell(
            room=room,
            name=form.cleaned_data['name'],
            cell_type=cell_type,
            position_x=form.cleaned_data.get('position_x', 0),
            position_y=form.cleaned_data.get('position_y', 0),
            width=form.cleaned_data.get('box_width'),
            height=form.cleaned_data.get('box_height'),
            depth=form.cleaned_data.get('box_depth'),
            color=form.cleaned_data.get('box_color'),
            material_type=form.cleaned_data.get('box_material_type'),
            is_locked=form.cleaned_data.get('box_is_locked', False),
            required_key=form.cleaned_data.get('box_required_key', ''),
            mass=form.cleaned_data.get('box_mass'),
            capacity=form.cleaned_data.get('box_capacity'),
            contents=form.cleaned_data.get('box_contents', []),
        )
        cell.save()
        return JsonResponse({
            'success': True,
            'message': f'Celda "{cell.name}" creada exitosamente.',
            'object': {
                'id': cell.id,
                'name': cell.name,
                'type': cell.cell_type,
                'room_id': room.id,
                'position_x': cell.position_x,
                'position_y': cell.position_y,
            }
        })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'message': 'Error al crear la celda.',
            'detail': str(e),
            'exception': str(type(e).__name__),
            'trace': tb
        }, status=400)


@login_required
@api_view(['GET'])
def object_hotbar_types(request):
    types = [
        {'type': 'WORK', 'label': 'Workstation', 'icon': 'bi-tools', 'color': 'primary'},
        {'type': 'SOCIAL', 'label': 'Social Area', 'icon': 'bi-people', 'color': 'success'},
        {'type': 'REST', 'label': 'Rest Zone', 'icon': 'bi-moon', 'color': 'info'},
        {'type': 'DOOR', 'label': 'Door', 'icon': 'bi-door-open', 'color': 'warning'},
        {'type': 'EQUIPMENT', 'label': 'Equipment', 'icon': 'bi-cpu', 'color': 'secondary'},
        {'type': 'CONTAINER', 'label': 'Contenedor', 'icon': 'bi-box', 'color': 'dark'},
        {'type': 'ITEM', 'label': 'Item/Decor', 'icon': 'bi-box-seam', 'color': 'secondary'},
    ]
    return Response({'success': True, 'types': types})


@login_required
def room_object_list(request, room_id):
    room = get_object_or_404(Cell, pk=room_id, cell_type='ROOM')
    cells = room.children.select_related('parent').all()

    context = {
        'room': room,
        'cells': cells,
    }
    return render(request, 'rooms/room_object_list.html', context)


@login_required
def box_detail(request, box_id):
    obj = get_object_or_404(Cell.objects.select_related('room'), pk=box_id, cell_type='CONTAINER')
    if not _user_can_manage(obj.room, request.user):
        return JsonResponse({'success': False, 'message': 'Sin permisos.'}, status=403)

    context = {
        'box': obj,
        'room': obj.room,
    }
    return render(request, 'rooms/box_detail.html', context)


@login_required
def box_action(request, box_id):
    obj = get_object_or_404(Cell, pk=box_id, cell_type='CONTAINER')
    if not _user_can_manage(obj.room, request.user):
        return JsonResponse({'success': False, 'message': 'Sin permisos.'}, status=403)

    action = request.POST.get('action') or request.GET.get('action')

    if action == 'open':
        can_open, reason = obj.can_open(None)
        if not can_open:
            return JsonResponse({'success': False, 'message': reason}, status=400)
        obj.open()
        return JsonResponse({'success': True, 'message': f'Celda "{obj.name}" abierta.', 'is_open': obj.is_open})

    if action == 'close':
        obj.close()
        return JsonResponse({'success': True, 'message': f'Celda "{obj.name}" cerrada.', 'is_open': obj.is_open})

    if action == 'add_item':
        item_name = request.POST.get('item_name')
        item_id = request.POST.get('item_id')
        if not item_name and not item_id:
            return JsonResponse({'success': False, 'message': 'Debes enviar item_name o item_id.'}, status=400)
        item = {'id': item_id or str(uuid.uuid4()), 'name': item_name or 'Item sin nombre'}
        added = obj.add_item(item)
        if not added:
            return JsonResponse({'success': False, 'message': 'La celda está llena.', 'capacity': obj.capacity, 'contents_count': len(obj.contents or [])}, status=400)
        return JsonResponse({'success': True, 'message': 'Item agregado.', 'item': item, 'contents': obj.contents})

    if action == 'remove_item':
        item_id = request.POST.get('item_id')
        if not item_id:
            return JsonResponse({'success': False, 'message': 'Debes enviar item_id.'}, status=400)
        item = obj.remove_item(item_id)
        if item is None:
            return JsonResponse({'success': False, 'message': 'Item no encontrado.'}, status=404)
        return JsonResponse({'success': True, 'message': 'Item removido.', 'item': item, 'contents': obj.contents})

    return JsonResponse({'success': False, 'message': f'Acción no soportada: {action}'}, status=400)
