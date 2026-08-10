from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from datetime import timedelta
from django.utils import timezone

class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player_profile')
    current_room = models.ForeignKey('Room', on_delete=models.SET_NULL, null=True, blank=True)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    energy = models.IntegerField(default=100)
    productivity = models.IntegerField(default=50)
    social = models.IntegerField(default=50)
    last_interaction = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=20, choices=[
        ('AVAILABLE', 'Disponible'),
        ('WORKING', 'Trabajando'),
        ('RESTING', 'Descansando'),
        ('SOCIALIZING', 'Socializando'),
        ('IDLE', 'Inactivo'),
        ('DISCONNECTED', 'Desconectado')
    ], default='IDLE')
    skills = models.JSONField(default=list)  # Ej: ["programming", "design"]
    last_state_change = models.DateTimeField(auto_now=True)

    # Navigation history for back button handling
    navigation_history = models.JSONField(default=list, help_text='Historial de habitaciones visitadas para navegación con botón atrás')
    last_navigation_time = models.DateTimeField(auto_now=True)
    
    def move_to_room(self, direction):
        current_room = self.current_room
        entrance = current_room.entrances.filter(face=direction.upper(), enabled=True).first()
        
        if not entrance or not entrance.connection:
            return False  # No hay conexión en esa dirección
        
        connection = entrance.connection
        if connection.bidirectional or connection.from_room == current_room:
            self.current_room = connection.to_room
            self.position_x, self.position_y = self.calculate_new_position(direction)
            self.save()
            return True
        return False

    def calculate_new_position(self, direction):
        # Lógica para posicionar al jugador en la entrada correspondiente de la nueva habitación
        if direction == 'NORTH':
            return self.position_x, 0
        elif direction == 'SOUTH':
            return self.position_x, self.current_room.width

    def get_available_exits(self):
        """Devuelve todas las salidas disponibles de la habitación actual."""
        exits = []
        current_room = self.current_room

        # 1. Entradas físicas habilitadas
        for entrance in current_room.entrance_exits.filter(enabled=True):
            if entrance.connection:
                exits.append({
                    'type': 'entrance',
                    'id': entrance.id,
                    'direction': entrance.face,
                    'name': entrance.name,
                    'to_room': entrance.connection.to_room.id,
                    'energy_cost': entrance.connection.energy_cost
                })

        # 2. Portales activos
        for portal in current_room.portals.all():
            if portal.is_active():
                exits.append({
                    'type': 'portal',
                    'id': portal.id,
                    'name': portal.name,
                    'to_room': portal.exit.room.id,
                    'energy_cost': portal.energy_cost
                })

        # 3. Objetos transportables
        for obj in current_room.room_objects.filter(object_type__in=['DOOR', 'PORTAL']):
            exits.append({
                'type': 'object',
                'id': obj.id,
                'name': obj.name,
                'interaction': obj.object_type.lower()
            })

        # 4. Navegación jerárquica (padre/hijo)
        # Ir al padre (si existe)
        if current_room.parent_room:
            exits.append({
                'type': 'hierarchy',
                'id': current_room.parent_room.id,
                'name': f"⬆️ Ir a {current_room.parent_room.name} (padre)",
                'to_room': current_room.parent_room.id,
                'energy_cost': 1,  # Costo mínimo para navegación jerárquica
                'direction': 'UP'
            })

        # Ir a habitaciones hijas (si existen)
        child_rooms = current_room.child_of_rooms.filter(is_active=True)
        for child in child_rooms:
            exits.append({
                'type': 'hierarchy',
                'id': child.id,
                'name': f"⬇️ Ir a {child.name} (hijo)",
                'to_room': child.id,
                'energy_cost': 1,  # Costo mínimo para navegación jerárquica
                'direction': 'DOWN'
            })

        return exits

    def can_use_exit(self, exit_type, exit_id):
        """Verifica si el jugador puede usar una salida específica."""
        if exit_type == 'entrance':
            entrance = EntranceExit.objects.get(id=exit_id)
            return entrance.enabled and entrance.connection
        elif exit_type == 'portal':
            portal = Portal.objects.get(id=exit_id)
            return portal.is_active() and self.energy >= portal.energy_cost
        elif exit_type == 'hierarchy':
            # Para navegación jerárquica, verificar que la habitación existe y está activa
            from .models import Room
            try:
                target_room = Room.objects.get(id=exit_id)
                return target_room.is_active and self.energy >= 1
            except Room.DoesNotExist:
                return False
        return True

    def use_exit(self, exit_type, exit_id):
        """Utiliza una salida y actualiza la posición del jugador"""
        if not self.can_use_exit(exit_type, exit_id):
            return False

        # Record current room in navigation history before moving
        self.add_to_navigation_history(self.current_room.id)

        if exit_type == 'entrance':
            entrance = EntranceExit.objects.get(id=exit_id)
            self.current_room = entrance.connection.to_room
            # Posicionar al jugador frente a la entrada correspondiente
            opposite_entrance = entrance.connection.entrance
            self.position_x = opposite_entrance.position_x
            self.position_y = opposite_entrance.position_y
            self.energy -= entrance.connection.energy_cost

        elif exit_type == 'portal':
            portal = Portal.objects.get(id=exit_id)
            self.current_room = portal.exit.room
            self.position_x = portal.exit.position_x
            self.position_y = portal.exit.position_y
            self.energy -= portal.energy_cost
            portal.last_used = timezone.now()
            portal.save()

        elif exit_type == 'hierarchy':
            # Navegación jerárquica directa
            from .models import Room
            target_room = Room.objects.get(id=exit_id)
            self.current_room = target_room
            # Centrar al jugador en la nueva habitación
            self.position_x = target_room.length // 2
            self.position_y = target_room.width // 2
            self.energy -= 1  # Costo mínimo para navegación jerárquica

        self.save()
        return True

    def add_to_navigation_history(self, room_id):
        """Agrega una habitación al historial de navegación"""
        history = self.navigation_history or []
        # Evitar duplicados consecutivos
        if not history or history[-1] != room_id:
            history.append(room_id)
            # Mantener solo las últimas 10 habitaciones
            if len(history) > 10:
                history = history[-10:]
            self.navigation_history = history
            self.save()

    def can_teleport_to(self, target_room):
        """Verifica si el jugador puede teletransportarse a una habitación"""
        if not target_room or not target_room.is_active:
            return False, "Habitación no disponible"

        teleport_cost = 20  # Costo base de teletransportación
        if self.energy < teleport_cost:
            return False, f"Insuficiente energía. Necesitas {teleport_cost}, tienes {self.energy}"

        return True, "Teletransportación disponible"

    def teleport_to(self, target_room):
        """Teletransporta al jugador a una habitación específica"""
        can_teleport, reason = self.can_teleport_to(target_room)
        if not can_teleport:
            return False, reason

        # Record current room in history before teleporting
        self.add_to_navigation_history(self.current_room.id)

        # Teleport
        self.current_room = target_room
        self.energy -= 20  # Costo de teletransportación
        self.position_x = target_room.length // 2  # Centro de la habitación
        self.position_y = target_room.width // 2
        self.save()

        return True, f"Teletransportado a {target_room.name}"

class RoomManager(models.Manager):
    pass

class Room(models.Model):
    version = models.PositiveBigIntegerField(default=0)
    bumped_at = models.DateTimeField(auto_now_add=True)
    last_message = models.ForeignKey(
        'Message', related_name='last_message_rooms',
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_rooms')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms', null=True, blank=True)
    administrators = models.ManyToManyField(User, related_name='administered_rooms', blank=True)
    capacity = models.IntegerField(default=0)
    address = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='./room_images/', blank=True)
    permissions = models.CharField(max_length=255, choices=[
        ('public', 'Public'),
        ('private', 'Private'),
        ('restricted', 'Restricted')
    ], default='public')
    comments = models.ManyToManyField(User, through='Comment', related_name='comments')
    evaluations = models.ManyToManyField(User, through='Evaluation', related_name='evaluations')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    x = models.IntegerField(default=0)
    y = models.IntegerField(default=0)
    z = models.IntegerField(default=0)
    length = models.IntegerField(default=30)
    width = models.IntegerField(default=30)
    height = models.IntegerField(default=10)
    pitch = models.IntegerField(default=0)
    yaw = models.IntegerField(default=0)
    roll = models.IntegerField(default=0)
    room_type = models.CharField(max_length=20, choices=[
        ('OFFICE', 'Office'),
        ('MEETING', 'Meeting Room'),
        ('LOUNGE', 'Lounge'),
        ('KITCHEN', 'Kitchen'),
        ('BATHROOM', 'Bathroom'),
        ('SPECIAL', 'Special Area')
    ], default='OFFICE')
    connections = models.ManyToManyField(
        'self',
        through='RoomConnection',
        symmetrical=False,
        related_name='connected_rooms',  # Ensure unique related_name
    )
    parent_room = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_of_rooms',  # Ensure unique related_name
    )
    portals = models.ManyToManyField('Portal', related_name='rooms', blank=True)  # Define the relationship
    objects = RoomManager()  # Define a custom manager to avoid conflicts

    # Propiedades de apariencia y material
    color_primary = models.CharField(max_length=7, default='#2196f3', help_text='Color primario en formato hex (#RRGGBB)')
    color_secondary = models.CharField(max_length=7, default='#1976d2', help_text='Color secundario en formato hex (#RRGGBB)')
    material_type = models.CharField(max_length=50, choices=[
        ('WOOD', 'Madera'),
        ('METAL', 'Metal'),
        ('GLASS', 'Vidrio'),
        ('CONCRETE', 'Concreto'),
        ('PLASTIC', 'Plástico'),
        ('FABRIC', 'Tela'),
        ('STONE', 'Piedra'),
        ('SPECIAL', 'Especial')
    ], default='CONCRETE')
    texture_url = models.URLField(blank=True, help_text='URL de la textura/imagen')
    opacity = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text='Opacidad (0.0-1.0)')

    # Propiedades físicas
    mass = models.DecimalField(max_digits=10, decimal_places=2, default=1000.0, help_text='Masa en kg')
    density = models.DecimalField(max_digits=5, decimal_places=2, default=2.4, help_text='Densidad en g/cm³')
    friction = models.DecimalField(max_digits=3, decimal_places=2, default=0.5, help_text='Coeficiente de fricción')
    restitution = models.DecimalField(max_digits=3, decimal_places=2, default=0.3, help_text='Coeficiente de restitución (rebote)')

    # Estado y funcionalidad
    is_active = models.BooleanField(default=True, help_text='Si la habitación está activa')
    health = models.IntegerField(default=100, help_text='Salud/durabilidad (0-100)')
    temperature = models.DecimalField(max_digits=5, decimal_places=1, default=22.0, help_text='Temperatura en °C')
    lighting_intensity = models.IntegerField(default=50, help_text='Intensidad de iluminación (0-100)')
    sound_ambient = models.CharField(max_length=100, blank=True, help_text='Sonido ambiente')
    special_properties = models.JSONField(default=dict, help_text='Propiedades especiales en formato JSON')

    def increment_version(self):
        self.version += 1
        self.save()
        return self.version

    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return None  # Return None if no file is associated

    def __str__(self):
        return self.name

    def add_member(self, user, role='member', added_by=None):
        """Add a user to the room with specified role"""
        membership, created = RoomMember.objects.get_or_create(
            room=self, user=user,
            defaults={'role': role}
        )
        if created:
            # Create notification for new member
            Notification.objects.create(
                user=user,
                title=f"Welcome to {self.name}",
                message=f"You have been added to the room {self.name}",
                notification_type='room_invite',
                related_room=self,
                action_url=f'/chat/room/{self.id}/'
            )
            # Create room notification
            RoomNotification.objects.create(
                room=self,
                user=user,
                title='New Member',
                message=f'{user.get_full_name()} joined the room',
                notification_type='member_join',
                created_by=added_by
            )
        return membership

    def remove_member(self, user, removed_by=None):
        """Remove a user from the room"""
        try:
            membership = RoomMember.objects.get(room=self, user=user)
            membership.delete()

            # Create room notification
            RoomNotification.objects.create(
                room=self,
                user=user,
                title='Member Left',
                message=f'{user.get_full_name()} left the room',
                notification_type='member_leave',
                created_by=removed_by
            )
            return True
        except RoomMember.DoesNotExist:
            return False

    def get_active_members(self):
        """Get all active members of the room"""
        return self.members.filter(is_active=True).select_related('user')

    def get_online_members(self):
        """Get members who were active in the last 5 minutes"""
        from django.utils import timezone
        five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
        return self.members.filter(
            is_active=True,
            last_seen__gte=five_minutes_ago
        ).select_related('user')

    def can_user_manage(self, user):
        """Check if user can manage this room"""
        if user == self.owner:
            return True
        return self.members.filter(
            user=user,
            role__in=['admin', 'moderator'],
            is_active=True
        ).exists()

class RoomConnection(models.Model):
    from_room = models.ForeignKey(Room, related_name='from_connections', on_delete=models.CASCADE)
    to_room = models.ForeignKey(Room, related_name='to_connections', on_delete=models.CASCADE)
    entrance = models.ForeignKey('EntranceExit', related_name='room_connections', on_delete=models.CASCADE)
    bidirectional = models.BooleanField(default=True)
    energy_cost = models.IntegerField(default=0)

    class Meta:
        unique_together = ('from_room', 'to_room', 'entrance')

    def __str__(self):
        return f"{self.from_room.name} -> {self.to_room.name} via {self.entrance.name}"

class RoomObject(models.Model):
    name = models.CharField(max_length=100)
    room = models.ForeignKey(Room, related_name='room_objects', on_delete=models.CASCADE)  # Updated related_name
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    object_type = models.CharField(max_length=50, choices=[
        ('WORK', 'Workstation'),
        ('SOCIAL', 'Social Area'),
        ('REST', 'Rest Zone'),
        ('DOOR', 'Door'),
        ('EQUIPMENT', 'Equipment')
    ])
    effect = models.JSONField(default=dict)
    interaction_cooldown = models.IntegerField(default=60)

    def interact(self, player):
        if self.object_type == 'WORK':
            player.state = 'WORKING'
            player.productivity += 10
        elif self.object_type == 'SOCIAL':
            player.state = 'SOCIALIZING'
            player.social += 5
        player.save()
        return {"status": player.state, "energy": player.energy}                
    
    def __str__(self):
        return f"{self.name} ({self.get_object_type_display()}) in {self.room.name}"


class Box(models.Model):
    name = models.CharField(max_length=100)
    room = models.ForeignKey(Room, related_name='boxes', on_delete=models.CASCADE)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=60, help_text='Ancho en cm')
    height = models.IntegerField(default=40, help_text='Alto en cm')
    depth = models.IntegerField(default=40, help_text='Profundidad en cm')
    color = models.CharField(max_length=7, default='#8B4513', help_text='Color en formato hex (#RRGGBB)')
    material_type = models.CharField(max_length=50, choices=[
        ('WOOD', 'Madera'),
        ('METAL', 'Metal'),
        ('PLASTIC', 'Plástico'),
        ('CARDBOARD', 'Cartón'),
        ('GLASS', 'Vidrio'),
        ('SPECIAL', 'Especial')
    ], default='CARDBOARD')
    is_open = models.BooleanField(default=False, help_text='Estado actual (abierto/cerrado)')
    is_locked = models.BooleanField(default=False, help_text='Si está cerrado con llave')
    required_key = models.CharField(max_length=100, blank=True, help_text='ID del objeto/llave necesario')
    mass = models.DecimalField(max_digits=10, decimal_places=2, default=1.0, help_text='Masa en kg')
    capacity = models.IntegerField(default=10, help_text='Capacidad de items')
    contents = models.JSONField(default=list, help_text='Lista de items dentro de la caja')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='./box_images/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        state = "🔓" if not self.is_locked else "🔒"
        open_state = "🟢" if self.is_open else "🔴"
        return f"{state}{open_state} {self.name} ({self.room.name})"

    def can_open(self, player_profile):
        if not self.is_locked:
            return True, "La caja se puede abrir"
        if self.required_key and self.required_key in getattr(player_profile, 'inventory', []):
            return True, "Llave correcta"
        return False, "Caja cerrada con llave"

    def open(self):
        if not self.is_open:
            self.is_open = True
            self.save()

    def close(self):
        if self.is_open:
            self.is_open = False
            self.save()

    def add_item(self, item):
        contents = self.contents or []
        if len(contents) < self.capacity:
            contents.append(item)
            self.contents = contents
            self.save()
            return True
        return False

    def remove_item(self, item_id):
        contents = self.contents or []
        for index, item in enumerate(contents):
            if item.get('id') == item_id:
                contents.pop(index)
                self.contents = contents
                self.save()
                return item
        return None


class EntranceExit(models.Model):
    name = models.CharField(max_length=255)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='entrance_exits')
    description = models.TextField(blank=True)
    face = models.CharField(max_length=10, choices=[
        ('NORTH', 'North'),
        ('SOUTH', 'South'),
        ('EAST', 'East'),
        ('WEST', 'West'),
        ('UP', 'Up'),
        ('DOWN', 'Down')
    ])
    position_x = models.IntegerField(null=True, blank=True)
    position_y = models.IntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    connection = models.ForeignKey(RoomConnection, on_delete=models.SET_NULL, null=True, blank=True)

    # Propiedades físicas/visuales
    width = models.IntegerField(default=100, help_text='Ancho de la puerta en cm')
    height = models.IntegerField(default=200, help_text='Alto de la puerta en cm')
    door_type = models.CharField(max_length=20, choices=[
        ('SINGLE', 'Puerta simple'),
        ('DOUBLE', 'Puerta doble'),
        ('SLIDING', 'Corrediza'),
        ('FOLDING', 'Plegable'),
        ('REVOLVING', 'Giratoria'),
        ('GATE', 'Portón'),
        ('HATCH', 'Escotilla')
    ], default='SINGLE')
    material = models.CharField(max_length=50, choices=[
        ('WOOD', 'Madera'),
        ('METAL', 'Metal'),
        ('GLASS', 'Vidrio'),
        ('PLASTIC', 'Plástico'),
        ('STONE', 'Piedra'),
        ('SPECIAL', 'Especial')
    ], default='WOOD')
    color = models.CharField(max_length=7, default='#8B4513', help_text='Color en formato hex (#RRGGBB)')
    texture_url = models.URLField(blank=True, help_text='URL de textura/imagen')
    opacity = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text='Opacidad (0.0-1.0)')

    # Propiedades funcionales
    is_locked = models.BooleanField(default=False, help_text='Si está cerrada con llave')
    required_key = models.CharField(max_length=100, blank=True, help_text='ID del objeto/llave necesario')
    auto_close = models.BooleanField(default=False, help_text='Si se cierra automáticamente')
    close_delay = models.IntegerField(default=5, help_text='Segundos antes de cerrarse automáticamente')
    open_speed = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, help_text='Velocidad de apertura (segundos)')
    close_speed = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, help_text='Velocidad de cierre (segundos)')
    sound_open = models.URLField(blank=True, help_text='Sonido al abrir')
    sound_close = models.URLField(blank=True, help_text='Sonido al cerrar')

    # Propiedades de interacción
    interaction_type = models.CharField(max_length=20, choices=[
        ('PUSH', 'Empujar'),
        ('PULL', 'Tirar'),
        ('HANDLE', 'Manija'),
        ('BUTTON', 'Botón'),
        ('AUTOMATIC', 'Automática'),
        ('LEVER', 'Palanca'),
        ('KNOB', 'Perilla')
    ], default='PUSH')
    animation_type = models.CharField(max_length=20, choices=[
        ('SWING', 'Giratoria'),
        ('SLIDE', 'Deslizante'),
        ('FOLD', 'Plegable'),
        ('ROLL', 'Enrollable'),
        ('NONE', 'Sin animación')
    ], default='SWING')
    requires_both_hands = models.BooleanField(default=False, help_text='Si requiere ambas manos')
    interaction_distance = models.IntegerField(default=150, help_text='Distancia máxima para interactuar (cm)')

    # Propiedades de estado
    is_open = models.BooleanField(default=False, help_text='Estado actual (abierta/cerrada)')
    last_opened = models.DateTimeField(null=True, blank=True)
    usage_count = models.IntegerField(default=0, help_text='Número de veces usada')
    health = models.IntegerField(default=100, help_text='Estado de la puerta (0-100)')

    # Propiedades de seguridad/permisos
    access_level = models.IntegerField(default=0, help_text='Nivel de acceso requerido (0-10, 0=abierto)')
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_doors', help_text='Usuarios con acceso especial')
    security_system = models.CharField(max_length=50, choices=[
        ('NONE', 'Sin seguridad'),
        ('BASIC', 'Básica'),
        ('ELECTRONIC', 'Electrónica'),
        ('BIOMETRIC', 'Biométrica'),
        ('MAGNETIC', 'Magnética')
    ], default='NONE')
    alarm_triggered = models.BooleanField(default=False, help_text='Si activó alarma de seguridad')

    # Propiedades ambientales
    seals_air = models.BooleanField(default=True, help_text='Si sella el aire (presurización)')
    seals_sound = models.IntegerField(default=20, help_text='Aislamiento acústico en dB')
    temperature_resistance = models.IntegerField(default=50, help_text='Resistencia a temperatura (-50 a +50°C)')
    pressure_resistance = models.IntegerField(default=1, help_text='Resistencia a presión (atm)')

    # Propiedades de juego/mecánicas
    energy_cost_modifier = models.IntegerField(default=0, help_text='Modificador del costo de energía base')
    experience_reward = models.IntegerField(default=1, help_text='Experiencia por usar la puerta')
    special_effects = models.JSONField(default=dict, help_text='Efectos especiales en JSON')
    cooldown = models.IntegerField(default=0, help_text='Cooldown entre usos (segundos)')
    max_usage_per_hour = models.IntegerField(default=0, help_text='Límite de uso por hora (0=ilimitado)')

    # Propiedades de apariencia avanzada
    glow_color = models.CharField(max_length=7, blank=True, help_text='Color de brillo (#RRGGBB)')
    glow_intensity = models.IntegerField(default=0, help_text='Intensidad del brillo (0-100)')
    particle_effects = models.CharField(max_length=100, blank=True, help_text='Efectos de partículas')
    decoration_type = models.CharField(max_length=50, choices=[
        ('NONE', 'Sin decoración'),
        ('FRAME', 'Marco decorativo'),
        ('WINDOW', 'Ventanal'),
        ('ORNAMENTAL', 'Adorno ornamental'),
        ('RUNIC', 'Rúnico/mágico')
    ], default='NONE')

    def save(self, *args, **kwargs):
        if self.position_x is None or self.position_y is None:
            self.assign_default_position()
        super().save(*args, **kwargs)

    def assign_default_position(self):
        if self.face == 'NORTH':
            self.position_x = self.room.length // 2
            self.position_y = self.room.width
        elif self.face == 'SOUTH':
            self.position_x = self.room.length // 2
            self.position_y = 0
        elif self.face == 'EAST':
            self.position_x = self.room.length
            self.position_y = self.room.width // 2
        elif self.face == 'WEST':
            self.position_x = 0
            self.position_y = self.room.width // 2
        else:
            self.position_x = self.room.length // 2
            self.position_y = self.room.width // 2

    def can_player_use(self, player_profile):
        """
        Verifica si un jugador puede usar esta puerta.
        Delega la lógica al RoomTransitionManager.
        """
        from .transition_manager import get_room_transition_manager
        manager = get_room_transition_manager()
        result = manager.attempt_transition(player_profile, self)
        return result['success'], result.get('message', '')

    def attempt_transition(self, player_profile):
        """
        Intenta realizar una transición a través de esta puerta.
        Delega la lógica al RoomTransitionManager.
        """
        from .transition_manager import get_room_transition_manager
        manager = get_room_transition_manager()
        return manager.attempt_transition(player_profile, self)

    def get_transition_info(self, player_profile):
        """
        Obtiene información sobre la transición posible a través de esta puerta.
        """
        from .transition_manager import get_room_transition_manager
        manager = get_room_transition_manager()

        if not self.connection:
            return {
                'can_use': False,
                'reason': 'No hay conexión activa',
                'target_room': None,
                'energy_cost': 0
            }

        # Determinar habitación destino
        if self.connection.from_room == player_profile.current_room:
            target_room = self.connection.to_room
        elif self.connection.to_room == player_profile.current_room and self.connection.bidirectional:
            target_room = self.connection.from_room
        else:
            target_room = None

        if not target_room:
            return {
                'can_use': False,
                'reason': 'Dirección inválida',
                'target_room': None,
                'energy_cost': 0
            }

        # Verificar acceso
        access_result = manager._validate_access(player_profile, self)
        energy_cost = manager._calculate_energy_cost(self.connection, self)

        return {
            'can_use': access_result['allowed'],
            'reason': access_result.get('message', ''),
            'target_room': target_room,
            'energy_cost': energy_cost,
            'experience_reward': self.experience_reward
        }

    def get_opposite_entrance(self):
        """
        Obtiene la entrada opuesta en la habitación conectada.
        """
        if not self.connection:
            return None

        target_room = None
        if self.connection.from_room == self.room:
            target_room = self.connection.to_room
        elif self.connection.to_room == self.room and self.connection.bidirectional:
            target_room = self.connection.from_room

        if not target_room:
            return None

        # Buscar la entrada correspondiente en la habitación destino
        for entrance in target_room.entrance_exits.all():
            if entrance.connection == self.connection and entrance != self:
                return entrance

        return None

    def get_usage_statistics(self):
        """
        Obtiene estadísticas de uso de la puerta.
        """
        return {
            'total_usage': self.usage_count,
            'last_used': self.last_opened,
            'is_open': self.is_open,
            'health_percentage': self.health
        }

    def __str__(self):
        status = "🔓" if not self.is_locked else "🔒"
        enabled = "✅" if self.enabled else "❌"
        return f"{status}{enabled} {self.name} ({self.room.name} - {self.face})"


class Portal(models.Model):
    name = models.CharField(max_length=255)
    entrance = models.ForeignKey(EntranceExit, related_name='portal_entrance', on_delete=models.CASCADE)
    exit = models.ForeignKey(EntranceExit, related_name='portal_exit', on_delete=models.CASCADE)
    energy_cost = models.IntegerField(default=10)
    cooldown = models.IntegerField(default=300)
    last_used = models.DateTimeField(null=True, blank=True)

    def is_active(self):
        """Un portal está activo si no está en cooldown"""
        return (self.last_used is None or 
                self.last_used + timedelta(seconds=self.cooldown) < timezone.now())    
    def __str__(self):
        return f"Portal: {self.name} ({self.entrance.room.name} → {self.exit.room.name})"
 

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Evaluation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class RoomMember(models.Model):
    room = models.ForeignKey(Room, related_name='members', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='room_memberships', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=20, choices=[
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin')
    ], default='member')
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    notification_preferences = models.JSONField(default=dict)  # Store user notification prefs

    class Meta:
        unique_together = ('room', 'user')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.room.name} ({self.role})"

    def can_manage_room(self):
        return self.role in ['admin', 'moderator'] or self.room.owner == self.user

    def can_delete_messages(self):
        return self.role == 'admin' or self.room.owner == self.user



class Message(models.Model):
    room = models.ForeignKey(Room, related_name='messages', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='messages', on_delete=models.CASCADE, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    message_type = models.CharField(max_length=20, choices=[
        ('text', 'Text'),
        ('system', 'System'),
        ('file', 'File'),
        ('image', 'Image')
    ], default='text')

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username if self.user else 'System'}: {self.content[:50]}"

    def get_replies(self):
        return self.replies.filter(is_deleted=False)

    def mark_as_read_for_user(self, user):
        MessageRead.objects.get_or_create(user=user, message=self)

class MessageRead(models.Model):
    user = models.ForeignKey(User, related_name='read_messages', on_delete=models.CASCADE)
    message = models.ForeignKey(Message, related_name='reads', on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('user', 'message')


class Notification(models.Model):
    user = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('chat', 'Chat Message'),
        ('system', 'System'),
        ('alert', 'Alert'),
        ('info', 'Information'),
        ('room_invite', 'Room Invitation'),
        ('room_join', 'Room Join'),
        ('room_leave', 'Room Leave'),
        ('admin_action', 'Admin Action')
    ], default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    related_room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    related_message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    action_url = models.CharField(max_length=500, blank=True)  # URL to redirect on click

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['user', 'notification_type']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class RoomNotification(models.Model):
    room = models.ForeignKey(Room, related_name='room_notifications', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='room_notifications', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('member_join', 'Member Joined'),
        ('member_leave', 'Member Left'),
        ('room_update', 'Room Updated'),
        ('admin_change', 'Admin Changed'),
        ('message_pinned', 'Message Pinned'),
        ('room_settings', 'Settings Changed')
    ], default='member_join')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='created_room_notifications', on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.room.name}: {self.title}"


class Outbox(models.Model):
    method = models.TextField(default="publish")
    payload = models.JSONField()
    partition = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class CDC(models.Model):
    method = models.TextField(default="publish")
    payload = models.JSONField()
    partition = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
