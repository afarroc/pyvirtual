from django.db import models
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player_profile')
    current_room = models.ForeignKey('Cell', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'cell_type': 'ROOM'})
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    position_z = models.IntegerField(default=0)
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
    skills = models.JSONField(default=list)
    last_state_change = models.DateTimeField(auto_now=True)
    navigation_history = models.JSONField(default=list, help_text='Historial de celdas visitadas para navegación con botón atrás')
    last_navigation_time = models.DateTimeField(auto_now=True)

    def move_to_room(self, direction):
        current_cell = self.current_room
        if not current_cell or current_cell.cell_type != 'ROOM':
            return False

        # Buscar salida en la dirección indicada entre las conexiones de la celda
        exit_cell = None
        for conn in current_cell.outgoing_connections.select_related('to_cell', 'entrance').all():
            if conn.entrance and conn.entrance.properties.get('face') == direction.upper() and conn.entrance.properties.get('enabled', True):
                exit_cell = conn.to_cell
                break

        if not exit_cell:
            return False

        self.add_to_navigation_history(self.current_room.id)
        self.current_room = exit_cell
        self.position_x, self.position_y = self.calculate_new_position(direction)
        self.save()
        return True

    def move_to_cell(self, cell_id):
        try:
            target_cell = Cell.objects.get(pk=cell_id)
        except Cell.DoesNotExist:
            return False, "Celda destino no encontrada"

        if not self.current_room or self.current_room.cell_type != 'ROOM':
            return False, "No estás en ninguna habitación (ROOM)"

        # Permitir movimiento si la celda destino está dentro de la jerarquía de la room actual
        if target_cell.cell_type == 'ROOM':
            self.add_to_navigation_history(self.current_room.id)
            self.current_room = target_cell
            self.position_x = target_cell.position_x
            self.position_y = target_cell.position_y
            self.save()
            return True, f"Movido a {target_cell.name}"

        # Para celdas hijas, deben pertenecer a la room actual o ser alcanzables
        if target_cell.parent != self.current_room and target_cell.parent_id != self.current_room.id:
            return False, "La celda destino no está en la habitación actual"

        self.position_x = target_cell.position_x
        self.position_y = target_cell.position_y
        self.save()
        return True, f"Movido a {target_cell.name}"

    def get_navigation_breadcrumb(self):
        breadcrumb = []
        current = self.current_room
        while current:
            breadcrumb.append({
                'id': current.id,
                'name': current.name,
                'cell_type': current.cell_type,
            })
            current = current.parent
        return list(reversed(breadcrumb))

    def get_last_navigation_target(self):
        if not self.navigation_history:
            return None
        last_id = self.navigation_history[-1]
        return Cell.objects.filter(pk=last_id).first()

    def calculate_new_position(self, direction):
        if direction == 'NORTH':
            return self.position_x, self.current_room.length
        elif direction == 'SOUTH':
            return self.position_x, 0
        elif direction == 'EAST':
            return self.current_room.width, self.position_y
        elif direction == 'WEST':
            return 0, self.position_y
        return self.position_x, self.position_y

    def get_available_exits(self):
        """Devuelve todas las salidas disponibles de la habitación actual."""
        exits = []
        current_room = self.current_room
        if not current_room or current_room.cell_type != 'ROOM':
            return exits

        # 1. Conexiones de celda ( Doors / Portales como celdas )
        for conn in current_room.outgoing_connections.select_related('to_cell', 'entrance').all():
            if conn.entrance and conn.entrance.properties.get('enabled', True):
                exits.append({
                    'type': 'connection',
                    'id': conn.entrance.id,
                    'direction': conn.entrance.properties.get('face', ''),
                    'name': conn.entrance.name,
                    'to_cell': conn.to_cell.id,
                    'energy_cost': conn.energy_cost,
                })

        # 2. Celdas hijas de tipo DOOR o PORTAL
        for child in current_room.children.filter(cell_type__in=['DOOR', 'PORTAL']):
            exits.append({
                'type': 'cell',
                'id': child.id,
                'name': child.name,
                'cell_type': child.cell_type,
            })

        # 3. Navegación jerárquica (padre/hijo ROOM)
        parent = current_room.parent
        if parent and parent.cell_type == 'ROOM':
            exits.append({
                'type': 'hierarchy',
                'id': parent.id,
                'name': f"⬆️ Ir a {parent.name} (padre)",
                'to_cell': parent.id,
                'energy_cost': 1,
                'direction': 'UP'
            })

        for child in current_room.children.filter(cell_type='ROOM', is_active=True):
            exits.append({
                'type': 'hierarchy',
                'id': child.id,
                'name': f"⬇️ Ir a {child.name} (hijo)",
                'to_cell': child.id,
                'energy_cost': 1,
                'direction': 'DOWN'
            })

        return exits

    def can_use_exit(self, exit_type, exit_id):
        if exit_type == 'connection':
            try:
                cell = Cell.objects.get(id=exit_id)
                return cell.is_active and self.energy >= 1
            except Cell.DoesNotExist:
                return False
        elif exit_type == 'cell':
            try:
                cell = Cell.objects.get(id=exit_id)
                return cell.is_active and self.energy >= 1
            except Cell.DoesNotExist:
                return False
        elif exit_type == 'hierarchy':
            try:
                target = Cell.objects.get(id=exit_id)
                return target.is_active and self.energy >= 1
            except Cell.DoesNotExist:
                return False
        return True

    def use_exit(self, exit_type, exit_id):
        if not self.can_use_exit(exit_type, exit_id):
            return False

        self.add_to_navigation_history(self.current_room.id)

        if exit_type == 'connection':
            # Las conexiones ahora son parte de CellConnections
            conn = CellConnection.objects.filter(entrance_id=exit_id).first()
            if conn:
                self.current_room = conn.to_cell
                self.energy -= conn.energy_cost

        elif exit_type == 'cell':
            target_cell = Cell.objects.get(id=exit_id)
            self.current_room = target_cell
            self.position_x = target_cell.position_x
            self.position_y = target_cell.position_y
            self.energy -= 1

        elif exit_type == 'hierarchy':
            target_cell = Cell.objects.get(id=exit_id)
            self.current_room = target_cell
            self.position_x = target_cell.position_x
            self.position_y = target_cell.position_y
            self.energy -= 1

        self.save()
        return True

    def add_to_navigation_history(self, cell_id):
        history = self.navigation_history or []
        if not history or history[-1] != cell_id:
            history.append(cell_id)
            if len(history) > 10:
                history = history[-10:]
            self.navigation_history = history
            self.save()

    def can_teleport_to(self, target_cell):
        if not target_cell or not target_cell.is_active:
            return False, "Celda no disponible"
        teleport_cost = 20
        if self.energy < teleport_cost:
            return False, f"Insuficiente energía. Necesitas {teleport_cost}, tienes {self.energy}"
        return True, "Teletransportación disponible"

    def teleport_to(self, target_cell):
        can_teleport, reason = self.can_teleport_to(target_cell)
        if not can_teleport:
            return False, reason

        self.add_to_navigation_history(self.current_room.id)
        self.current_room = target_cell
        self.energy -= 20
        self.position_x = target_cell.position_x
        self.position_y = target_cell.position_y
        self.save()
        return True, f"Teletransportado a {target_cell.name}"


class Cell(models.Model):
    CELL_TYPES = [
        ('UNIVERSE', 'Universo'),
        ('WORLD', 'Mundo'),
        ('ROOM', 'Habitación'),
        ('AREA', 'Área'),
        ('CONTAINER', 'Contenedor'),
        ('FURNITURE', 'Mobiliario'),
        ('OBJECT', 'Objeto'),
        ('ITEM', 'Item'),
        ('PORTAL', 'Portal'),
        ('DOOR', 'Puerta'),
        ('DECORATION', 'Decoración'),
    ]
    MATERIALS = [
        ('WOOD', 'Madera'),
        ('METAL', 'Metal'),
        ('PLASTIC', 'Plástico'),
        ('CARDBOARD', 'Cartón'),
        ('GLASS', 'Vidrio'),
        ('SPECIAL', 'Especial'),
    ]

    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    cell_type = models.CharField(max_length=20, choices=CELL_TYPES)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    position_z = models.IntegerField(default=0)
    width = models.IntegerField(null=True, blank=True, help_text='Ancho en cm')
    height = models.IntegerField(null=True, blank=True, help_text='Alto en cm')
    depth = models.IntegerField(null=True, blank=True, help_text='Profundidad en cm')
    length = models.IntegerField(default=30, help_text='Largo en cm')
    color = models.CharField(max_length=7, null=True, blank=True, help_text='Color hex #RRGGBB')
    color_primary = models.CharField(max_length=7, default='#2196f3', help_text='Color primario en formato hex (#RRGGBB)')
    color_secondary = models.CharField(max_length=7, default='#1976d2', help_text='Color secundario en formato hex (#RRGGBB)')
    material_type = models.CharField(max_length=50, choices=MATERIALS, null=True, blank=True)
    capacity = models.IntegerField(null=True, blank=True, help_text='Capacidad de items')
    contents = models.JSONField(default=list, blank=True, help_text='Items contenidos')
    is_open = models.BooleanField(null=True, blank=True, help_text='Estado actual')
    is_locked = models.BooleanField(null=True, blank=True, help_text='Si está cerrado con llave')
    required_key = models.CharField(max_length=100, blank=True, help_text='ID del objeto/llave necesario')
    mass = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Masa en kg')
    effect = models.JSONField(null=True, blank=True, help_text='Efecto/interacción de la celda')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='./cell_images/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text='Si la celda está activa')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_cells', null=True, blank=True)
    properties = models.JSONField(blank=True, default=dict, help_text='Propiedades extendidas en JSON')
    texture_url = models.URLField(blank=True, help_text='URL de la textura/imagen')
    opacity = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text='Opacidad (0.0-1.0)')
    density = models.DecimalField(max_digits=5, decimal_places=2, default=2.4, help_text='Densidad en g/cm³')
    friction = models.DecimalField(max_digits=3, decimal_places=2, default=0.5, help_text='Coeficiente de fricción')
    restitution = models.DecimalField(max_digits=3, decimal_places=2, default=0.3, help_text='Coeficiente de restitución (rebote)')
    health = models.IntegerField(default=100, help_text='Salud/durabilidad (0-100)')
    temperature = models.DecimalField(max_digits=5, decimal_places=1, default=22.0, help_text='Temperatura en °C')
    lighting_intensity = models.IntegerField(default=50, help_text='Intensidad de iluminación (0-100)')
    sound_ambient = models.CharField(max_length=100, blank=True, help_text='Sonido ambiente')
    pitch = models.IntegerField(default=0)
    yaw = models.IntegerField(default=0)
    roll = models.IntegerField(default=0)

    class Meta:
        ordering = ['cell_type', 'name']

    def get_room(self):
        """Devuelve la celda ROOM ancestra más cercana."""
        current = self
        while current:
            if current.cell_type == 'ROOM':
                return current
            current = current.parent
        return None

    def get_all_children(self):
        children = list(self.children.all())
        for child in self.children.all():
            children.extend(child.get_all_children())
        return children

    def get_depth(self):
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def get_full_path(self):
        path = []
        current = self
        while current:
            path.append(current.name)
            current = current.parent
        return ' / '.join(reversed(path))

    def is_container(self):
        return self.cell_type in ['CONTAINER', 'FURNITURE', 'OBJECT', 'ITEM']

    def can_open(self, player_profile=None):
        if not self.is_locked:
            return True, "Se puede abrir"
        if self.required_key and self.required_key in getattr(player_profile, 'inventory', []):
            return True, "Llave correcta"
        return False, "Cerrado con llave"

    def open(self):
        if not self.is_open:
            self.is_open = True
            self.save()

    def close(self):
        if self.is_open:
            self.is_open = False
            self.save()

    def add_item(self, item):
        if self.capacity is None:
            return False
        contents = self.contents or []
        if len(contents) < self.capacity:
            contents.append(item)
            self.contents = contents
            self.save()
            return True
        return False

    def remove_item(self, item_id):
        if self.contents is None:
            return None
        contents = list(self.contents)
        for index, item in enumerate(contents):
            if item.get('id') == item_id:
                contents.pop(index)
                self.contents = contents
                self.save()
                return item
        return None

    def __str__(self):
        return f"{self.name} ({self.get_cell_type_display()})"


class CellMembership(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_MEMBER = 'member'
    ROLE_VIEWER = 'viewer'
    ROLE_CHOICES = [
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MEMBER, 'Member'),
        (ROLE_VIEWER, 'Viewer'),
    ]

    cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cell_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cell', 'user')
        ordering = ['cell', 'role']

    def __str__(self):
        return f"{self.user.username} -> {self.cell.name} ({self.role})"


class CellConnection(models.Model):
    from_cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='outgoing_connections')
    to_cell = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='incoming_connections')
    entrance = models.ForeignKey(Cell, on_delete=models.CASCADE, related_name='cell_connections')
    bidirectional = models.BooleanField(default=True)
    energy_cost = models.IntegerField(default=0)

    class Meta:
        unique_together = ('from_cell', 'to_cell', 'entrance')

    def __str__(self):
        return f"{self.from_cell.name} -> {self.to_cell.name} via {self.entrance.name}"


class Message(models.Model):
    room = models.ForeignKey(Cell, related_name='messages', on_delete=models.CASCADE)
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


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Cell, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Evaluation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Cell, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


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
    related_room = models.ForeignKey(Cell, on_delete=models.CASCADE, null=True, blank=True)
    related_message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    action_url = models.CharField(max_length=500, blank=True)

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
