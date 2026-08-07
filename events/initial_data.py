# initial_data.py
from faker import Faker
import random
import string
from django.contrib.auth import get_user_model

User = get_user_model()
from .models import Status, ProjectStatus, TaskStatus  # Añade esta importación

fake_en = Faker()
fake_es = Faker('es_ES')

def generate_random_username():
    """Genera un nombre de usuario aleatorio."""
    return 'setup_user_' + ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def generate_random_name(language, format='full'):
    """Genera un nombre aleatorio en el idioma especificado."""
    if language == 'english':
        fake = fake_en
    elif language == 'spanish':
        fake = fake_es
    else:
        raise ValueError('Idioma no soportado')

    if format == 'full':
        return fake.name()
    elif format == 'first_last':
        return f"{fake.first_name()} {fake.last_name()}"
    else:
        raise ValueError('Formato no soportado')


def generate_random_password(length=12):
    """Genera una contraseña aleatoria con la longitud especificada."""
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(chars, k=length))

DOMAIN_BASE = 'localhost'

def create_default_users():
    """Crea usuarios predeterminados."""
    user_data = []

    su_username = 'su'
    su_first_name = 'Superusuario'
    su_email = f'{su_username}@{DOMAIN_BASE}'
    su_password = generate_random_password()

    if not User.objects.filter(username=su_username).exists():
        User.objects.create_superuser(su_username, su_email, su_password)
        user_data.append({
        'username': su_username,
        'email': su_email,
        'password': su_password,
        'first_name': su_first_name,
        })

    user_username = generate_random_username()
    user_first_name = generate_random_name('spanish', format='first_last').split()[0]
    user_last_name = generate_random_name('spanish', format='first_last').split()[1]
    user_email = f'{user_username}@{DOMAIN_BASE}'
    user_password = generate_random_password()

    if not User.objects.filter(username=user_username).exists():
        User.objects.create_user(user_username, user_email, user_password)
        user_data.append({
        'username': user_username,
        'first_name': user_first_name,
        'last_name': user_last_name,
        'email': user_email,
        'password': user_password,
        })

        return user_data
        
# initial_data.py (add this function)
def create_initial_statuses():
    """Create default statuses for Events, Projects and Tasks if they don't exist"""
    status_data = {
        'Event': [
            {'status_name': 'Created', 'color': '#3498db', 'icon': 'bi-file-earmark-plus'},
            {'status_name': 'In Progress', 'color': '#f39c12', 'icon': 'bi-arrow-repeat'},
            {'status_name': 'Paused', 'color': '#e74c3c', 'icon': 'bi-pause-fill'},
            {'status_name': 'Completed', 'color': '#2ecc71', 'icon': 'bi-check-circle'},
            {'status_name': 'Cancelled', 'color': '#95a5a6', 'icon': 'bi-x-circle'},
        ],
        'Project': [
            {'status_name': 'Draft', 'color': '#bdc3c7', 'icon': 'bi-file-earmark-text'},
            {'status_name': 'Planning', 'color': '#9b59b6', 'icon': 'bi-kanban'},
            {'status_name': 'In Progress', 'color': '#f39c12', 'icon': 'bi-arrow-repeat'},
            {'status_name': 'On Hold', 'color': '#e74c3c', 'icon': 'bi-pause-fill'},
            {'status_name': 'Completed', 'color': '#2ecc71', 'icon': 'bi-check-circle'},
        ],
        'Task': [
            {'status_name': 'To Do', 'color': '#bdc3c7', 'icon': 'bi-list-task'},
            {'status_name': 'In Progress', 'color': '#f39c12', 'icon': 'bi-arrow-repeat'},
            {'status_name': 'In Review', 'color': '#fd7e14', 'icon': 'bi-eye'},
            {'status_name': 'Blocked', 'color': '#e74c3c', 'icon': 'bi-exclamation-triangle'},
            {'status_name': 'Completed', 'color': '#2ecc71', 'icon': 'bi-check-circle'},
            {'status_name': 'Verified', 'color': '#27ae60', 'icon': 'bi-shield-check'},
        ]
    }
    
    created_statuses = []
    
    # Create Event Statuses
    for status in status_data['Event']:
        obj, created = Status.objects.get_or_create(
            status_name=status['status_name'],
            defaults={'color': status['color'], 'icon': status['icon']}
        )
        if created:
            created_statuses.append(f"Event Status: {status['status_name']}")
    
    # Create Project Statuses
    for status in status_data['Project']:
        obj, created = ProjectStatus.objects.get_or_create(
            status_name=status['status_name'],
            defaults={'color': status['color'], 'icon': status['icon']}
        )
        if created:
            created_statuses.append(f"Project Status: {status['status_name']}")
    
    # Create Task Statuses
    for status in status_data['Task']:
        obj, created = TaskStatus.objects.get_or_create(
            status_name=status['status_name'],
            defaults={'color': status['color'], 'icon': status['icon']}
        )
        if created:
            created_statuses.append(f"Task Status: {status['status_name']}")
    
    return created_statuses