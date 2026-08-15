"""
Management command to seed demo projects with related tasks.

Usage:
    python manage.py seed_projects_with_tasks
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from events.models import Project, Task, ProjectStatus, TaskStatus, Event

PROJECTS = [
    {
        'title': 'Website Redesign',
        'description': 'Rediseño completo del sitio corporativo incluyendo homepage, about, servicios y contacto.',
        'status': 'In Progress',
        'event_id': 1,
        'tasks': [
            ('Research & benchmarks', 'In Progress'),
            ('Wireframes homepage', 'To Do'),
            ('Copywriting', 'To Do'),
            ('Diseño UI secciones', 'In Progress'),
            ('Integración CMS', 'To Do'),
            ('QA y performance', 'To Do'),
        ],
    },
    {
        'title': 'Mobile App MVP',
        'description': 'Lanzamiento del MVP de la app móvil para clientes con login, catálogo y checkout.',
        'status': 'Planning',
        'event_id': 4,
        'tasks': [
            ('Definir flujo de onboarding', 'To Do'),
            ('Prototipo onboarding', 'To Do'),
            ('Backend auth', 'In Progress'),
            ('Integración pagos', 'Blocked'),
            ('Tests E2E', 'To Do'),
        ],
    },
    {
        'title': 'Data Analytics Pipeline',
        'description': 'Pipeline de analytics para ingestion, limpieza y visualización de métricas de ventas.',
        'status': 'Completed',
        'event_id': 5,
        'tasks': [
            ('Diseño de modelo de datos', 'Completed'),
            ('ETL ventas 2025', 'Completed'),
            ('Dashboard operativo', 'Completed'),
            ('Documentación', 'Completed'),
        ],
    },
    {
        'title': 'Security Hardening',
        'description': 'Refuerzo de seguridad, rotación de secretos y revisión de permisos.',
        'status': 'On Hold',
        'event_id': 1,
        'tasks': [
            ('Audit de dependencias', 'In Review'),
            ('Rotación de API keys', 'Verified'),
            ('Revisión de roles', 'To Do'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed demo projects with related tasks'

    @transaction.atomic
    def handle(self, *args, **options):
        users = list(get_user_model().objects.all())
        if not users:
            self.stdout.write(self.style.ERROR('No users found. Aborting.'))
            return

        host = users[0]
        assignee = users[1] if len(users) > 1 else users[0]

        statuses = {s.status_name: s for s in ProjectStatus.objects.all()}
        task_statuses = {s.status_name: s for s in TaskStatus.objects.all()}

        if not statuses:
            self.stdout.write(self.style.ERROR('No ProjectStatus found. Run ensure_statuses first.'))
            return

        created_projects = 0
        created_tasks = 0

        for data in PROJECTS:
            status_obj = statuses.get(data['status'])
            if not status_obj:
                self.stdout.write(self.style.WARNING(f"Missing status: {data['status']}"))
                continue

            event = Event.objects.filter(id=data['event_id']).first()

            project, created = Project.objects.get_or_create(
                title=data['title'],
                defaults={
                    'description': data['description'],
                    'project_status': status_obj,
                    'host': host,
                    'assigned_to': assignee,
                    'event': event,
                    'ticket_price': 0,
                },
            )
            if created:
                created_projects += 1

            for task_title, task_status_name in data['tasks']:
                task_status_obj = task_statuses.get(task_status_name)
                if not task_status_obj:
                    continue
                Task.objects.get_or_create(
                    title=task_title,
                    project=project,
                    defaults={
                        'description': data['description'],
                        'task_status': task_status_obj,
                        'assigned_to': assignee,
                        'host': host,
                        'event': event,
                        'ticket_price': 0,
                    },
                )
                created_tasks += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created_projects} projects with {created_tasks} tasks.'))
