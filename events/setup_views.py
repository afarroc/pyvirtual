from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model

from django.contrib.auth.models import Group
User = get_user_model()
from django.contrib import messages
from django.urls import reverse
from django.core.exceptions import ValidationError
from cv.models import Curriculum as Profile
from .utils import create_user_profile
from .initial_data import generate_random_name, generate_random_username, create_initial_statuses  # Añadir import aquí
from .models import Status, ProjectStatus, TaskStatus
import random
import string
import logging

DOMAIN_BASE = 'localhost'

def generate_random_password(length=12):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(chars, k=length))

class SetupView(View):
    template_name = 'setup/setup.html'

    def get(self, request):
        logger = logging.getLogger(__name__)
        logger.info("=== DEBUG GET REQUEST START ===")
        logger.info(f"Request user: {request.user}")
        logger.info(f"Request user authenticated: {request.user.is_authenticated}")
        logger.info(f"Request user is_superuser: {request.user.is_superuser}")
        logger.info(f"GET parameters: {dict(request.GET)}")

        if not request.user.is_authenticated:
            step = request.GET.get('step', '1')
            logger.info(f"User not authenticated, setting step to: {step}")
        elif request.user.is_superuser:
            step = request.GET.get('step', '5')
            logger.info(f"User is superuser, setting step to: {step}")
        else:
            step = 'login'
            logger.info(f"User authenticated but not superuser, setting step to: {step}")

        completed_steps = []
        logger.info(f"Initial completed_steps: {completed_steps}")

        # Check if superuser exists (handle missing table)
        try:
            if User.objects.filter(username='su').exists():
                completed_steps.append('1')
        except Exception as e:
            # Table might not exist yet, skip this check
            pass

        # Check if user profile exists
        try:
            if request.user.is_authenticated and Profile.objects.filter(user=request.user).exists():
                completed_steps.append('2')
        except Exception as e:
            # Table might not exist yet, skip this check
            pass

        # Get all groups and users (handle missing tables)
        try:
            all_groups = Group.objects.all()
        except Exception as e:
            all_groups = []

        try:
            all_users = User.objects.all()
        except Exception as e:
            all_users = []

        # Check if statuses exist
        try:
            if Status.objects.exists() and ProjectStatus.objects.exists() and TaskStatus.objects.exists():
                completed_steps.append('3')
        except Exception as e:
            # Tables might not exist yet, skip this check
            pass

        context = {
            'page_title': 'Setup',
            'step': step,
            'completed_steps': completed_steps,
            'all_groups': all_groups,
            'all_users': all_users,
        }
        logger.info(f"Final context: {context}")
        logger.info("=== DEBUG GET REQUEST END ===")
        return render(request, self.template_name, context)

    def post(self, request):
        logger = logging.getLogger(__name__)
        logger.info("=== DEBUG POST REQUEST START ===")
        logger.info(f"POST request received. Keys: {list(request.POST.keys())}")
        logger.info(f"POST data: {dict(request.POST)}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request user: {request.user}")
        logger.info(f"Request user authenticated: {request.user.is_authenticated}")
    
        # SIMPLIFICAR: Detección directa de acciones
        # Verificar si 'create_su' está en POST (sin valor específico, solo existencia)
        create_su_triggered = 'create_su' in request.POST
        
        logger.info(f"'create_su' in request.POST: {'create_su' in request.POST}")
        logger.info(f"'create_su' value: {request.POST.get('create_su', 'NOT FOUND')}")
        
        # Log de todas las claves para debug
        for key, value in request.POST.items():
            logger.info(f"POST[{key}] = {value}")
    
        if create_su_triggered:
            logger.info("SUPERUSER CREATION TRIGGERED - Processing...")
            try:
                if not User.objects.filter(username='su').exists():
                    username = 'su'
                    first_name = 'Superusuario'
                    last_name = ''  # Compatible con PostgreSQL
                    email = f'{username}@{DOMAIN_BASE}'
                    password = generate_random_password()
                    
                    logger.info(f"Creating superuser with: username={username}, email={email}")
                    
                    # Usar el método nativo de Django - más seguro y simple
                    superuser = User.objects.create_superuser(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name
                    )
                    
                    logger.info(f"Superuser created successfully: {username}")
                    messages.success(request, f'Superusuario creado: {username}, contraseña: {password}')
                    
                    # Autenticar y loguear automáticamente
                    user = authenticate(username=username, password=password)
                    if user is not None:
                        login(request, user)
                        request.session['first_session'] = True
                        logger.info(f"Superuser authenticated and logged in: {user}")
                        return redirect(reverse('events:setup') + '?step=2')
                    else:
                        logger.error("Failed to authenticate newly created superuser")
                        messages.error(request, 'Error al autenticar el superusuario creado.')
                else:
                    logger.info("Superuser already exists, redirecting to login")
                    messages.info(request, 'El superusuario ya existe. Por favor, inicie sesión.')
                    return redirect(reverse('events:setup') + '?step=login')
                    
            except Exception as e:
                logger.error(f"Error creating superuser: {str(e)}", exc_info=True)
                error_message = f'Error al crear superusuario: {str(e)}'
                
                # Verificar si es error de tabla
                if "doesn't exist" in str(e) or "no such table" in str(e):
                    error_message += '. Las migraciones pueden no haberse ejecutado aún.'
                
                messages.error(request, error_message)
                return redirect(reverse('events:setup'))
    
        elif 'login_su' in request.POST:
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(reverse('events:setup') + '?step=2')
            else:
                messages.error(request, 'Credenciales incorrectas.')
    
        elif 'create_profile' in request.POST:
            try:
                su = User.objects.get(username='su')
                # Create or update profile with essential fields only
                profile, created = Profile.objects.get_or_create(
                    user=su,
                    defaults={
                        'full_name': request.POST.get('full_name', ''),
                        'profession': request.POST.get('profession', ''),
                        'role': request.POST.get('role', 'US'),
                    }
                )
    
                if not created:
                    profile.full_name = request.POST.get('full_name', '')
                    profile.profession = request.POST.get('profession', '')
                    profile.role = request.POST.get('role', 'US')
    
                # Handle profile picture if provided
                if 'profile_picture' in request.FILES:
                    profile.profile_picture = request.FILES['profile_picture']
    
                profile.save()
                messages.success(request, 'Profile created successfully!')
                return redirect(reverse('events:setup') + '?step=3')
    
            except User.DoesNotExist:
                messages.error(request, 'Superuser does not exist. Please create one first.')
            except Exception as e:
                messages.error(request, f'Error creating profile: {str(e)}. Las tablas pueden no existir aún.')
            return redirect(reverse('events:setup') + '?step=2')
    
        elif 'create_random_users' in request.POST:
            try:
                domain = request.POST['domain']
                num_users = int(request.POST['num_users'])
                group_name = request.POST.get('new_group_name')  # Nombre del nuevo grupo (si se proporciona)
                group_id = request.POST.get('group_id')  # Grupo seleccionado para asignar usuarios
                user_data = []
    
                if group_name:
                    group, created = Group.objects.get_or_create(name=group_name)
                elif group_id:
                    group = Group.objects.get(id=group_id)
                else:
                    group = None
    
                for _ in range(num_users):
                    username = generate_random_username()
                    first_name = generate_random_name('spanish', format='first_last').split()[0]
                    last_name = generate_random_name('spanish', format='first_last').split()[1]
                    email = f'{username}@{domain}'
                    password = generate_random_password()
    
                    if not User.objects.filter(username=username).exists():
                        user = User.objects.create_user(username, email, password)
                        user.first_name = first_name
                        user.last_name = last_name
                        user.save()
                        user_data.append({
                            'username': username,
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'password': password,
                        })
    
                        # Asignar el usuario al grupo si se seleccionó uno
                        if group:
                            user.groups.add(group)
    
                messages.success(request, 'Usuarios creados con éxito.')
                completed_steps = ['1', '2', '3']
                all_groups = Group.objects.all()
                all_users = User.objects.all()
                return render(request, self.template_name, {
                    'page_title': 'Crear Usuarios Aleatorios',
                    'user_data': user_data,
                    'step': '4',
                    'completed_steps': completed_steps,
                    'all_groups': all_groups,
                    'all_users': all_users,
                })
            except Exception as e:
                messages.error(request, f'Error al crear usuarios: {str(e)}. Las tablas pueden no existir aún.')
                return redirect(reverse('events:setup'))
    
        elif 'create_group' in request.POST:
            try:
                # Logging inicial del proceso
                group_name = request.POST['group_name']
                usernames = request.POST.getlist('usernames')
                logger = logging.getLogger(__name__)
                logger.info(f"Iniciando creación de grupo: {group_name}")
                logger.info(f"Usuarios a asignar: {usernames}")
    
                # Crear o obtener grupo existente
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    logger.info(f"Grupo '{group_name}' creado exitosamente")
                else:
                    logger.info(f"Grupo '{group_name}' ya existía, se utilizará el existente")
    
                # Asignar usuarios al grupo
                assigned_users = []
                for username in usernames:
                    try:
                        user = User.objects.get(username=username)
                        user.groups.add(group)
                        assigned_users.append(username)
                        logger.info(f"Usuario '{username}' asignado al grupo '{group_name}'")
                    except User.DoesNotExist:
                        logger.warning(f"Usuario '{username}' no encontrado, se omite de la asignación")
                    except Exception as user_error:
                        logger.error(f"Error al asignar usuario '{username}' al grupo '{group_name}': {str(user_error)}")
    
                # Logging de resumen
                logger.info(f"Proceso completado. Grupo '{group_name}' creado y {len(assigned_users)}/{len(usernames)} usuarios asignados")
                logger.info(f"Usuarios asignados exitosamente: {assigned_users}")
    
                messages.success(request, f'Grupo {group_name} creado y usuarios asignados.')
                completed_steps = ['1', '2', '3', '4']
                logger.info(f"DEBUG: About to redirect to step 5. completed_steps: {completed_steps}")
                logger.info("=== DEBUG POST REQUEST END (SUCCESS) ===")
                return redirect(reverse('events:setup') + '?step=5')
    
            except Exception as e:
                # Logging de error detallado
                logger = logging.getLogger(__name__)
                logger.error(f"Error al crear grupo '{group_name}': {str(e)}")
                logger.error(f"Detalles del error: {type(e).__name__}")
                logger.error(f"Usuarios que se intentaban asignar: {usernames}")
    
                messages.error(request, f'Error al crear grupo: {str(e)}. Las tablas pueden no existir aún.')
                return redirect(reverse('events:setup'))
    
        elif 'create_another_su' in request.POST:
            try:
                su_username = request.POST['su_username']
                su_email = request.POST['su_email']
                su_password = generate_random_password()
                if not User.objects.filter(username=su_username).exists():
                    superuser = User.objects.create_superuser(su_username, su_email, su_password)
                    superuser.save()
                    messages.success(request, f'Superusuario creado: {su_username}, contraseña: {su_password}')
                else:
                    messages.error(request, 'El nombre de usuario ya existe.')
            except Exception as e:
                messages.error(request, f'Error al crear superusuario: {str(e)}. Las tablas pueden no existir aún.')
    
        elif 'create_initial_statuses' in request.POST:
            created_statuses = create_initial_statuses()
            if created_statuses:
                messages.success(request, 'Initial statuses created successfully:')
                for status in created_statuses:
                    messages.info(request, f'- {status}')
            else:
                messages.info(request, 'All initial statuses already exist.')
            return redirect(reverse('events:setup') + '?step=4')
    
        # Si llegamos aquí sin haber manejado ninguna acción, redirigir de vuelta
        logger.warning("No se manejó ninguna acción POST específica")
        return redirect(reverse('events:setup'))
        