#!/usr/bin/env python
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from rooms.models import PlayerProfile, Cell, CellMembership, CellConnection

User = get_user_model()

# Buscar usuario staff; si no existe, crear uno
user, created = User.objects.get_or_create(
    username='test_navigator',
    defaults={
        'email': 'test@example.com',
        'is_staff': True,
        'is_superuser': True,
    }
)
if created:
    user.set_password('testpass123')
    user.save()
    print(f"Usuario creado: {user.username}")
else:
    print(f"Usuario existente: {user.username}")

# Asegurar PlayerProfile
player, _ = PlayerProfile.objects.get_or_create(user=user, defaults={'energy': 200})

# Limpiar celdas previas del usuario para este script
Cell.objects.filter(owner=user, cell_type__in=['UNIVERSE','WORLD','AREA','ROOM','CONTAINER','ITEM','DOOR','PORTAL']).delete()
# Importante: no borrar todas las celdas si hay otras, solo las del usuario

universo = Cell.objects.create(
    owner=user,
    cell_type='UNIVERSE',
    name='Ecosistema de Gestión',
    description='Universo de prueba para explorar jerarquías espaciales, contenedores y navegación.',
    width=1000,
    height=800,
)

CellMembership.objects.get_or_create(cell=universo, user=user, defaults={'role': CellMembership.ROLE_OWNER})

mundo_operativo = Cell.objects.create(
    owner=user,
    cell_type='WORLD',
    name='Mundo Operativo',
    parent=universo,
    description='Áreas centradas en operación, control y desarrollo.',
)

mundo_social = Cell.objects.create(
    owner=user,
    cell_type='WORLD',
    name='Mundo Social',
    parent=universo,
    description='Áreas de descanso, comida y recreación.',
)

area_control = Cell.objects.create(
    owner=user,
    cell_type='AREA',
    name='Sala de Control',
    parent=mundo_operativo,
    description='Centro de mando, monitoreo y respuesta rápida.',
)

area_desarrollo = Cell.objects.create(
    owner=user,
    cell_type='AREA',
    name='Zona de Desarrollo',
    parent=mundo_operativo,
    description='Laboratorios y talleres de prototipado.',
)

area_comedor = Cell.objects.create(
    owner=user,
    cell_type='AREA',
    name='Comedor',
    parent=mundo_social,
    description='Zona de alimentación y cafetería.',
)

area_recreacion = Cell.objects.create(
    owner=user,
    cell_type='AREA',
    name='Recreación',
    parent=mundo_social,
    description='Juegos, descanso y espacios verdes.',
)

# Rooms
centro_mando = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Centro de Mando',
    parent=area_control,
    description='Sala principal de toma de decisiones.',
    width=400,
    height=300,
    length=30,
)

sala_monitoreo = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Sala de Monitoreo',
    parent=area_control,
    description='Pantallas y métricas en tiempo real.',
    width=350,
    height=250,
    length=30,
)

sala_crisis = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Sala de Crisis',
    parent=area_control,
    description='Sala de respuesta ante incidentes.',
    width=300,
    height=220,
    length=30,
)

laboratorio = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Laboratorio',
    parent=area_desarrollo,
    description='Experimentos y validaciones.',
    width=360,
    height=260,
    length=30,
)

taller = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Taller de Prototipos',
    parent=area_desarrollo,
    description='Construcción y prueba de prototipos.',
    width=380,
    height=280,
    length=30,
)

cafeteria = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Cafetería',
    parent=area_comedor,
    description='Mesas, café y espacio de charla informal.',
    width=340,
    height=240,
    length=30,
)

sala_juegos = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Sala de Juegos',
    parent=area_recreacion,
    description='Juegos de mesa, consolas y entretenimiento.',
    width=320,
    height=230,
    length=30,
)

jardin = Cell.objects.create(
    owner=user,
    cell_type='ROOM',
    name='Jardín',
    parent=area_recreacion,
    description='Espacio al aire libre para descansar.',
    width=500,
    height=350,
    length=30,
)

# Containers nested
consola = Cell.objects.create(
    owner=user,
    cell_type='CONTAINER',
    name='Consola Principal',
    parent=centro_mando,
    description='Consola de control central.',
    width=120,
    height=80,
    depth=60,
    capacity=5,
)

rack = Cell.objects.create(
    owner=user,
    cell_type='CONTAINER',
    name='Rack de Servidores',
    parent=sala_monitoreo,
    description='Rack con equipos de cómputo.',
    width=100,
    height=180,
    depth=90,
    capacity=8,
)

pantalla = Cell.objects.create(
    owner=user,
    cell_type='CONTAINER',
    name='Pantalla LED',
    parent=sala_monitoreo,
    description='Panel LED de métricas.',
    width=160,
    height=90,
    depth=10,
    capacity=2,
)

# Items dentro de contenedores
Cell.objects.create(
    owner=user,
    cell_type='ITEM',
    name='Tablero de Comandos',
    parent=consola,
    description='Interfaz táctil de comandos.',
    width=40,
    height=30,
    depth=5,
)

Cell.objects.create(
    owner=user,
    cell_type='ITEM',
    name='Panel de Alertas',
    parent=consola,
    description='Indicadores luminosos y alertas.',
    width=30,
    height=20,
    depth=5,
)

Cell.objects.create(
    owner=user,
    cell_type='ITEM',
    name='Servidor Principal',
    parent=rack,
    description='Servidor principal de aplicaciones.',
    width=45,
    height=88,
    depth=70,
)

Cell.objects.create(
    owner=user,
    cell_type='ITEM',
    name='Backup',
    parent=rack,
    description='Servidor de respaldo.',
    width=45,
    height=88,
    depth=70,
)

Cell.objects.create(
    owner=user,
    cell_type='ITEM',
    name='Módulo LED',
    parent=pantalla,
    description='Panel LED reemplazable.',
    width=150,
    height=80,
    depth=5,
)

# Doors entre rooms
door_cm_sm, _ = Cell.objects.get_or_create(
    owner=user,
    cell_type='DOOR',
    name='Puerta CM->SM',
    defaults={
        'description': 'Puerta entre Centro de Mando y Sala de Monitoreo.',
        'is_open': True,
        'properties': {'face': 'NORTH', 'enabled': True, 'door_type': 'SINGLE', 'material': 'METAL'},
    }
)
door_cm_sm.parent = centro_mando
door_cm_sm.save()

door_sm_cm, _ = Cell.objects.get_or_create(
    owner=user,
    cell_type='DOOR',
    name='Puerta SM->CM',
    defaults={
        'description': 'Puerta entre Sala de Monitoreo y Centro de Mando.',
        'is_open': True,
        'properties': {'face': 'SOUTH', 'enabled': True, 'door_type': 'SINGLE', 'material': 'METAL'},
    }
)
door_sm_cm.parent = sala_monitoreo
door_sm_cm.save()

CellConnection.objects.get_or_create(from_cell=centro_mando, to_cell=sala_monitoreo, entrance=door_cm_sm, defaults={'energy_cost': 1})
CellConnection.objects.get_or_create(from_cell=sala_monitoreo, to_cell=centro_mando, entrance=door_sm_cm, defaults={'energy_cost': 1})

# Portal entre Laboratorio y Taller
portal_lab_taller, _ = Cell.objects.get_or_create(
    owner=user,
    cell_type='PORTAL',
    name='Portal Lab-Taller',
    defaults={
        'description': 'Portal directo entre Laboratorio y Taller.',
        'is_active': True,
        'properties': {'energy_cost': 5, 'cooldown': 30},
    }
)
portal_lab_taller.parent = laboratorio
portal_lab_taller.save()

portal_taller_lab, _ = Cell.objects.get_or_create(
    owner=user,
    cell_type='PORTAL',
    name='Portal Taller-Lab',
    defaults={
        'description': 'Portal directo entre Taller y Laboratorio.',
        'is_active': True,
        'properties': {'energy_cost': 5, 'cooldown': 30},
    }
)
portal_taller_lab.parent = taller
portal_taller_lab.save()

CellConnection.objects.get_or_create(from_cell=laboratorio, to_cell=taller, entrance=portal_lab_taller, defaults={'energy_cost': 5})
CellConnection.objects.get_or_create(from_cell=taller, to_cell=laboratorio, entrance=portal_taller_lab, defaults={'energy_cost': 5})

# Door entre Cafetería y Sala de Juegos
door_cafe_juegos, _ = Cell.objects.get_or_create(
    owner=user,
    cell_type='DOOR',
    name='Puerta Cafetería-Juegos',
    defaults={
        'description': 'Puerta entre Cafetería y Sala de Juegos.',
        'is_open': True,
        'properties': {'face': 'EAST', 'enabled': True, 'door_type': 'SINGLE', 'material': 'WOOD'},
    }
)
door_cafe_juegos.parent = cafeteria
door_cafe_juegos.save()

door_juegos_cafe, _ = Cell.objects.get_or_create(
    owner=user,
    cell_type='DOOR',
    name='Puerta Juegos-Cafetería',
    defaults={
        'description': 'Puerta entre Sala de Juegos y Cafetería.',
        'is_open': True,
        'properties': {'face': 'WEST', 'enabled': True, 'door_type': 'SINGLE', 'material': 'WOOD'},
    }
)
door_juegos_cafe.parent = sala_juegos
door_juegos_cafe.save()

CellConnection.objects.get_or_create(from_cell=cafeteria, to_cell=sala_juegos, entrance=door_cafe_juegos, defaults={'energy_cost': 1})
CellConnection.objects.get_or_create(from_cell=sala_juegos, to_cell=cafeteria, entrance=door_juegos_cafe, defaults={'energy_cost': 1})

# Establecer ubicación inicial del jugador
player.current_room = centro_mando
player.position_x = centro_mando.width // 2
player.position_y = centro_mando.length // 2
player.save()

print('Universo creado: Ecosistema de Gestión')
print(f'Universe pk={universo.pk}, World pks={mundo_operativo.pk},{mundo_social.pk}')
print(f'Rooms: {centro_mando.name}, {sala_monitoreo.name}, {sala_crisis.name}, {laboratorio.name}, {taller.name}, {cafeteria.name}, {sala_juegos.name}, {jardin.name}')
print(f'Containers: {consola.name}, {rack.name}, {pantalla.name}')
print(f'Player set in: {player.current_room.name}')
