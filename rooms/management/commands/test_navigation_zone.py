from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()
from rooms.models import Room, EntranceExit, Portal, RoomConnection, Cell

class Command(BaseCommand):
    help = 'Test the navigation test zone creation'

    def handle(self, *args, **kwargs):
        self.stdout.write('=== Testing Navigation Test Zone Creation ===\n')

        # Get a user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()

        self.stdout.write(f'Using user: {user.username}\n')

        # Simulate the view logic
        from django.db import transaction

        with transaction.atomic():
            # Check if already exists
            root_room = Room.objects.filter(name='Navigation Test Zone').first()
            if root_room:
                self.stdout.write(self.style.WARNING('Navigation Test Zone already exists'))
                return

            # Create root room
            root_room = Room.objects.create(
                name='Navigation Test Zone',
                description='Zona de pruebas para testing de navegación por habitaciones interconectadas',
                owner=user,
                creator=user,
                permissions='public',
                room_type='OFFICE',
                x=0, y=0, z=0,
                length=20, width=20, height=5,
                color_primary='#4CAF50',
                color_secondary='#2196F3',
                material_type='CONCRETE',
                lighting_intensity=80,
                temperature=22.0
            )

            self.stdout.write(f'Created root room: {root_room.name}')

            # Create level 2 sectors
            alpha_sector = Room.objects.create(
                name='Alpha Sector',
                description='Sector Alpha - Área de desarrollo y testing',
                owner=user,
                creator=user,
                permissions='public',
                room_type='OFFICE',
                parent_room=root_room,
                x=25, y=0, z=0,
                length=15, width=15, height=4,
                color_primary='#FF9800',
                color_secondary='#F44336',
                material_type='METAL',
                lighting_intensity=70
            )

            self.stdout.write(f'Created sector: {alpha_sector.name}')

            # Count total rooms created
            total_rooms = Room.objects.filter(parent_room__isnull=False).count()
            self.stdout.write(f'\nTotal rooms in hierarchy: {total_rooms}')

            # Check connections
            total_doors = EntranceExit.objects.all().count()
            total_portals = Portal.objects.all().count()
            total_objects = Cell.objects.all().count()

            self.stdout.write(f'Connections - Doors: {total_doors}, Portals: {total_portals}, Objects: {total_objects}')

        self.stdout.write(self.style.SUCCESS('\nNavigation Test Zone creation test completed!'))