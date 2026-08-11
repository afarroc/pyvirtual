from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()
from rooms.models import Cell, CellConnection


class Command(BaseCommand):
    help = 'Create a test room Cell with ID 1'

    def handle(self, *args, **kwargs):
        cell, created = Cell.objects.get_or_create(
            id=1,
            defaults={
                'name': 'Test Room',
                'description': 'This is a test room.',
                'cell_type': 'ROOM',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Test room created successfully.'))
        else:
            self.stdout.write(self.style.WARNING('Test room already exists.'))
