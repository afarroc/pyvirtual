# Django imports
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.forms import formset_factory
from django.views import View
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from .forms import EditStatusForm
from .models import Status

# Local imports from .models
from .models import Project, Task, Event, Status, EventAttendee, EventState, Profile

# Local imports from .forms
from .forms import (
    CreateNewTask, CreateNewProject, CreateNewEvent, EventEditForm,
    ProfileForm, ExperienceForm, EducationForm, SkillForm
)

ExperienceFormSet = formset_factory(ExperienceForm, extra=1, can_delete=True)
EducationFormSet = formset_factory(EducationForm, extra=1, can_delete=True)
SkillFormSet = formset_factory(SkillForm, extra=1, can_delete=True)
# Create your views here.

# Principal

def index(request):
    title="Pagina Pricipal"
    return render(request, "index/index.html",{
        'title':title
    })

def about(request):
    username = "Nano"
    return render(request, "about/about.html",{
        'username':username
    })

# Sessions

def signup(request):
    
    if request.method=="GET":
        return render(request, 'session/signup.html', {
            'form':UserCreationForm
        })       
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                # register user
                user = User.objects.create_user(username=request.POST['username'], password=request.POST['password1'])
                user.save()
                login(request, user)
                return(redirect('events'))
            
            except IntegrityError:
                
                return render(request, 'signup.html', {
                    'form': UserCreationForm,
                    "error": "User already exist"
                })       
        return render(request, 'signup.html', { 
            'form': UserCreationForm,
            "error": "Password do not match"
        })    
    
def signout(request):
    logout(request)
    return(redirect('index'))

def signin(request):
    if request.method == "GET":
        return render(request,'session/signin.html',{
            'form':AuthenticationForm,
            })
    else:
        user = authenticate(
            request, username=request.POST['username'], password=request.POST['password'])
        if user is None:
            print('user is none')
            return render(request,'session/signin.html',{
                'form':AuthenticationForm,
                'error':'Username or password is incorrect'
            })
        else:
            login(request, user)
            return redirect('events')

# Proyects
            
def projects(request):
    projects = Project.objects.all()
    return render(request, "projects/projects.html",{
        'projects':projects
    })

def create_project(request):
    if request.method == 'GET':
        return render(request, 'projects/create_project.html', {
            'form':CreateNewProject()
        })
    else:

        Project.objects.create(name=request.POST['name'])
        return redirect('projects')

def project_detail(request, id):
    project = get_object_or_404(Project, id=id)
    tasks=Task.objects.filter(project_id=id)
    return render(request, 'projects/detail.html', {
        'project' : project,
        'tasks':tasks
    })

# Tasks
     
def task(request):
    tasks = Task.objects.all()
    return render(request, "tasks/tasks.html",{
        'tasks':tasks
    })

@login_required
def create_task(request):
    if request.method == 'GET':
        form = CreateNewTask()
    else:
        form = CreateNewTask(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user  # Asignar el usuario actual como el creador de la tarea
            task.project = form.cleaned_data['project']
            try:
                with transaction.atomic():
                    task.save()
                    messages.success(request, 'Task created successfully!')
                    return redirect('tasks')
            except IntegrityError:
                messages.error(request, 'There was a problem saving the task.')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'tasks/create_task.html', {'form': form})

# Events

def events(request):
    print("Inicio vista Events")

    # Obtener todos los eventos y ordenarlos por fecha de actualización
    # Filtrar los eventos por el usuario logueado
    events = Event.objects.filter(assigned_to=request.user).order_by('-updated_at')

    statuses = Status.objects.all().order_by('status_name')

    
    # Imprimir el estado y el ícono de cada estado
    for status in statuses:
        print(status, status.icon)

    if request.method == 'POST':
        print("Solicitud POST")
        print(request.POST)
        status = request.POST.get('status')
        date = request.POST.get('date')
        cerrado = request.POST.get('cerrado')

        # Filtrar eventos basados en si están cerrados o no
        if cerrado:
            events = events.exclude(event_status_id=3)
            request.session['filtered_cerrado'] = "true"
            print("Filtrado por <> cerrado", cerrado)
        else:
            request.session['filtered_cerrado'] = ""

        # Filtrar eventos basados en el estado seleccionado
        if status:
            events = events.filter(event_status_id=status)
            request.session['filtered_status'] = status
            print("Filtrado por id de estado", status)
        else:
            request.session['filtered_status'] = ""

        # Filtrar eventos basados en la fecha seleccionada
        if date:
            events = events.filter(created_at__date=date)
            request.session['filtered_date'] = date
            print("Filtrado por fecha", date)
        else:
            request.session['filtered_date'] = ""

        print("Fin vista Events")
        return render(request, 'events/events.html', {
            'events': events,
            'statuses': statuses,
        })

    else:
        print("Solicitud GET")
        print(request.GET)
        status = request.session.get('filtered_status')
        date = request.session.get('filtered_date')
        cerrado = request.session.get('filtered_cerrado') == "true"

        # Filtrar eventos basados en si están cerrados o no
        if cerrado:
            events = events.exclude(event_status_id=3)

        # Filtrar eventos basados en el estado seleccionado
        if status:
            events = events.filter(event_status_id=status)
            print("Filtrado por id de estado", status)

        # Filtrar eventos basados en la fecha seleccionada
        if date:
            events = events.filter(created_at__date=date)
            print("Filtrado por fecha", date)

        print(status, date)
        print("Fin vista Events")
        return render(request, 'events/events.html', {
            'events': events,
            'statuses': statuses,
        })

@login_required
def assign_attendee_to_event(request, event_id, user_id):
    # Obtén el evento y el usuario basado en los IDs proporcionados
    event = get_object_or_404(Event, pk=event_id)
    user = get_object_or_404(User, pk=user_id)

    # Crea una nueva instancia de EventAttendee
    event_attendee, created = EventAttendee.objects.get_or_create(
        user=user,
        event=event
    )

    if created:
        # El asistente fue asignado al evento exitosamente
        messages.success(request, 'Asistente asignado al evento con éxito.')
    else:
        # El asistente ya estaba asignado al evento
        messages.info(request, 'El asistente ya estaba asignado a este evento.')

    # Redirige a la página que desees, por ejemplo, la página de detalles del evento
    return redirect('event_detail', event_id=event_id)

from django.http import HttpResponseForbidden

@login_required
def create_event(request):
    if request.method == 'GET':
        form = CreateNewEvent()
    else:
        form = CreateNewEvent(request.POST)
        if form.is_valid():
            try:
                # Determinar el estado inicial basado en la solicitud
                initial_status_id = '19' if 'inbound' in request.POST else '16'
                initial_status = Status.objects.get(id=initial_status_id)

                # Crear el evento con los datos validados del formulario
                new_event = form.save(commit=False)
                new_event.event_status = initial_status
                new_event.host = request.user  # El host es siempre el creador del evento
                new_event.save()

                # Si el usuario es un supervisor, puede asignar el evento a cualquier usuario
                if request.user.profile.role == 'SU':
                    attendee = form.cleaned_data.get('attendee')
                # Si el usuario es un usuario estándar, solo puede asignarse el evento a sí mismo
                else:
                    attendee = request.user

                # Asignar el usuario asignado como atendedor
                EventAttendee.objects.create(
                    user=attendee,
                    event=new_event
                )

                # Crear el estado inicial para el evento
                EventState.objects.create(
                    event=new_event,
                    status=initial_status
                )

                messages.success(request, 'Evento creado con éxito.')
                return redirect('events')
            except IntegrityError as e:
                messages.error(request, f'Hubo un error al crear el evento: {e}')

    return render(request, 'events/create_event.html', {'form': form})

def event_detail(request, id):
    event = get_object_or_404(Event, id=id)
    return render(request, 'events/detail.html', {
        'event' :event,
        'events':events
    })

def event_edit(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        form = EventEditForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            print("Guardado")# Redirige a otra página o muestra un mensaje de éxito
    else:
        print(request.GET)
        form = EventEditForm(instance=event)
    return render(request, 'events/event_edit.html', {
        'form': form
        })

def change_event_status(request, event_id):
    # Obtener evento desde el event_id
    print("\n ---- Vista 'Cambio de estado' ----")
    print("Cambiando estado del evento con ID:", str(event_id))
    
    # Obtener evento
    event = get_object_or_404(Event, pk=event_id)
    
    print("Título:", str(event.title))
    print("Estado:", str(event.event_status.status_name))
    
    # Cambiar al nuevo estado el evento seleccionado
    print("Nuevo ID de estado:", str(request.POST.get('new_status_id')))
    
    new_status_id = request.POST.get('new_status_id')
    new_status = get_object_or_404(Status, pk=new_status_id)
    event.event_status = new_status
    
    # Guardar cambios
    event.save()
    print('Actualizado')
    
    # Guardar el estado del filtro en la sesión


    print("---- Fin de vista 'cambio de estado' ----\n")
    
    print("contenido de post antes de redireccionar: ", request.POST )
    
    # Devolver la redirección a la página de eventos
    return redirect(reverse('events'))
 
def delete_event(request, event_id):
    # Asegúrate de que solo se pueda acceder a esta vista mediante POST
    if request.method == 'POST':
        event = get_object_or_404(Event, pk=event_id)
        event.delete()
        messages.success(request, 'El evento ha sido eliminado exitosamente.')
    else:
        messages.error(request, 'Método no permitido.')
    return redirect(reverse('events'))


# Panel

def panel(request):
    events = Event.objects.all().order_by('-created_at')
    #events = events.filter(event_status_id = 5)
    return render(request, 'panel/panel.html', {'events': events})    

# Vistas para perfil de usuario

class ProfileView(View):
    def get(self, request, user_id=None):
        try:
            if user_id:
                profile = Profile.objects.get(user_id=user_id)
                profile_form = ProfileForm(instance=profile)
                experience_formset = ExperienceFormSet(prefix='experiences', queryset=profile.experiences.all())
                education_formset = EducationFormSet(prefix='education', queryset=profile.education.all())
                skill_formset = SkillFormSet(prefix='skills', queryset=profile.skills.all())
            else:
                profile_form = ProfileForm()
                experience_formset = ExperienceFormSet(prefix='experiences')
                education_formset = EducationFormSet(prefix='education')
                skill_formset = SkillFormSet(prefix='skills')

            return render(request, 'profiles/profile_form.html', {
                'profile_form': profile_form,
                'experience_formset': experience_formset,
                'education_formset': education_formset,
                'skill_formset': skill_formset
            })
        except Exception as e:
            return render(request, 'profiles/error.html', {'message': str(e)})

    @transaction.atomic
    def post(self, request, user_id=None):
        try:
            profile = Profile.objects.get(user_id=user_id) if user_id else None
            profile_form = ProfileForm(request.POST, instance=profile)
            experience_formset = ExperienceFormSet(request.POST, prefix='experiences')
            education_formset = EducationFormSet(request.POST, prefix='education')
            skill_formset = SkillFormSet(request.POST, prefix='skills')

            if profile_form.is_valid() and all(formset.is_valid() for formset in [experience_formset, education_formset, skill_formset]):
                profile = profile_form.save(commit=False)
                profile.user = request.user
                profile.save()

                for form in experience_formset:
                    if form.cleaned_data.get('DELETE'):
                        if form.instance.pk:
                            form.instance.delete()
                    else:
                        experience = form.save(commit=False)
                        experience.profile = profile
                        experience.save()

                for form in education_formset:
                    if form.cleaned_data.get('DELETE'):
                        if form.instance.pk:
                            form.instance.delete()
                    else:
                        education = form.save(commit=False)
                        education.profile = profile
                        education.save()

                for form in skill_formset:
                    if form.cleaned_data.get('DELETE'):
                        if form.instance.pk:
                            form.instance.delete()
                    else:
                        skill = form.save(commit=False)
                        skill.profile = profile
                        skill.save()

                return redirect('view_profile')

            return render(request, 'profiles/profile_form.html', {
                'profile_form': profile_form,
                'experience_formset': experience_formset,
                'education_formset': education_formset,
                'skill_formset': skill_formset
            })
        except IntegrityError as e:
            return render(request, 'error.html', {'message': f"An error occurred. Please make sure all fields are filled out correctly. Error: {e}"})
        except Exception as e:
            return render(request, 'error.html', {'message': str(e)})

class ViewProfileView(View):
    def get(self, request, user_id):
        profile = Profile.objects.get(user_id=user_id)
        experiences = profile.experiences.all()
        education = profile.education.all()
        skills = profile.skills.all()

        return render(request, 'profiles/view_profile.html', {
            'profile': profile,
            'experiences': experiences,
            'education': education,
            'skills': skills
        })


# Estatuses

def create_status(request):
    if request.method == 'POST':
        form = EditStatusForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('status_list')
    else:
        form = EditStatusForm()
    return render(request, 'configuration/create_status.html', {'form': form})

def edit_status(request, status_id):
    status = get_object_or_404(Status, id=status_id)
    if request.method == 'POST':
        form = EditStatusForm(request.POST, instance=status)
        if form.is_valid():
            form.save()
            return redirect('status_list')
    else:
        form = EditStatusForm(instance=status)
    return render(request, 'configuration/edit_status.html', {'form': form})

def delete_status(request, status_id):
    status = get_object_or_404(Status, id=status_id)
    if request.method == 'POST':
        status.delete()
        return redirect('status_list')
    return render(request, 'configuration/confirm_delete.html', {'object': status})

def status_list(request):
    statuses = Status.objects.all()
    return render(request, 'configuration/status_list.html', {'statuses': statuses})

