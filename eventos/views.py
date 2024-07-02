# Django imports
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.forms import formset_factory
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import FormView
from django.core.files.storage import FileSystemStorage

# Local imports from .models
from .models import Classification, Document, Event, EventAttendee, EventState, Image, Profile, Project, Status, Task

# Local imports from .forms
from .forms import (CreateNewEvent, CreateNewProject, CreateNewTask, DocumentForm, EditClassificationForm, EducationForm,  ExperienceForm, ImageForm, ProfileForm, SkillForm, EditStatusForm)

# Formsets
EducationFormSet = formset_factory(EducationForm, extra=1, can_delete=True)
ExperienceFormSet = formset_factory(ExperienceForm, extra=1, can_delete=True)
SkillFormSet = formset_factory(SkillForm, extra=1, can_delete=True)


# Create your views here.



# Principal

def index(request):
    title="Pagina Pricipal"
    return render(request, "index/index.html",{
        'title':title
    })

def home(request):
    return render(request, 'layouts/main.html')

def about(request):
    username = "Nano"
    return render(request, "about/about.html",{
        'username':username
    })

# Sessions

def signup(request):
    if request.method=="GET":
        return render(request, 'accounts/signup.html', {
            'form':UserCreationForm
        })       
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                # register user
                user = User.objects.create_user(username=request.POST['username'], password=request.POST['password1'])
                user.save()
                login(request, user)
                return(redirect('index'))  # Modificado aquí
            
            except IntegrityError:
                
                return render(request, 'accounts/signup.html', {
                    'form': UserCreationForm,
                    "error": "User already exist"
                })       
        return render(request, 'accounts/signup.html', { 
            'form': UserCreationForm,
            "error": "Password do not match"
        })    
    
def signout(request):
    logout(request)
    return(redirect('index'))

def signin(request):
    if request.method == "GET":
        return render(request,'accounts/signin.html',{
            'form':AuthenticationForm,
            })
    else:
        user = authenticate(
            request, username=request.POST['username'], password=request.POST['password'])
        if user is None:
            print('user is none')
            return render(request,'accounts/signin.html',{
                'form':AuthenticationForm,
                'error':'Username or password is incorrect'
            })
        else:
            login(request, user)
            request.session.setdefault('first_session', True)
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
@login_required
def events(request):
    if request.session['first_session'] == True:
        print('Esta la primera sesión')
        try:
            status_en_curso = Status.objects.get(status_name='En curso').id
        except ObjectDoesNotExist:
            status_en_curso = None
        cerrado = request.session.setdefault('filtered_cerrado', True)
        status = request.session.setdefault('filtered_status', status_en_curso)
        date = request.session.setdefault('filtered_date', timezone.now().date().isoformat())
        request.session['first_session'] = False  
        print(cerrado, status, date)
        print(request.session['filtered_cerrado'])
        print(request.session['filtered_status'])
        print(request.session['filtered_date'])
        
    try:
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'SU':
                events = Event.objects.all().order_by('-updated_at')
                
            else:
                events = Event.objects.filter(Q(assigned_to=request.user) | Q(attendees=request.user)).distinct().order_by('-updated_at')
                
        else:
            events = Event.objects.filter(Q(assigned_to=request.user) | Q(attendees=request.user)).distinct().order_by('-updated_at')
            
        statuses = Status.objects.all().order_by('status_name')
        
        if request.method == 'POST':
            print('solicitud post')

            cerrado = request.POST.get('cerrado') == 'True'
            status = int(request.POST.get('status')) if request.POST.get('status') else None
            date = request.POST.get('date')
            
            print('post:', cerrado, status, date)
            
            try:
                if cerrado:
                    status_cerrado = Status.objects.get(status_name='Cerrado')
                    events = events.exclude(event_status_id=status_cerrado.id)
                    request.session['filtered_cerrado'] = True
                else:
                    request.session['filtered_cerrado'] = False

            except Status.DoesNotExist:
                messages.error(request, f'Ha ocurrido un error al filtrar los eventos: {e}')
                
            if status:
                events = events.filter(event_status_id=status)
                request.session['filtered_status'] = status
            else:
                request.session['filtered_status'] = status
                
                
            if date:
                events = events.filter(updated_at__date=date)
                request.session['filtered_date'] = date
            else:
                request.session['filtered_date'] = date
            
            print("session cerrado:", request.session['filtered_cerrado'], type(request.session['filtered_cerrado']))
            print("session estado:", request.session['filtered_status'], type(request.session['filtered_status']))
            print("session fecha:", request.session['filtered_date'], type(request.session['filtered_date']))
            
            return render(request, 'events/events.html', {
                'events': events,
                'statuses': statuses,
            })
            
        else:
            print('solcitud get')
            status = request.session['filtered_status'] 
            date = request.session['filtered_date']
            cerrado = request.session['filtered_cerrado']
            print(cerrado, status, date)

            
            try:
                if cerrado:
                    status_cerrado = Status.objects.get(status_name='Cerrado')
                    events = events.exclude(event_status_id=status_cerrado.id)
                    print("filtrado los estados cerrados")
                    
                if status:
                    events = events.filter(event_status_id=status)
                    print("Filtrado por estado", status)                    
                if date:
                    events = events.filter(updated_at__date=date)
                    print("Filtrado por fecha", date)
                    
            except Status.DoesNotExist:
                messages.error(request, f'Ha ocurrido un error al filtrar los eventos: {e}')
                
            except Exception as e:
                messages.error(request, f'Ha ocurrido un error al filtrar los eventos: {e}')
                return redirect('index')
            
            print("session cerrado:", request.session['filtered_cerrado'], type(request.session['filtered_cerrado']))
            print("session estado:", request.session['filtered_status'], type(request.session['filtered_status']))
            print("session fecha:", request.session['filtered_date'], type(request.session['filtered_date']))
            
            return render(request, 'events/events.html', {
                'events': events,
                'statuses': statuses,
            })
            
    except Exception as e:
        messages.error(request, 'Ha ocurrido un error al obtener los eventos: {}'.format(e))
        return redirect('index')

@login_required
def assign_attendee_to_event(request, event_id, user_id):
    try:
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
    except Exception as e:
        # Si ocurre un error, muestra un mensaje de alerta y redirige al usuario a la página de inicio
        messages.error(request, 'Ha ocurrido un error al asignar el asistente al evento: {}'.format(e))
        return redirect('index')

@login_required
def create_event(request):
    try:
        if request.method == 'GET':
            try:
                default_status = Status.objects.get(status_name='Creado').id
            except Status.DoesNotExist:
                messages.error(request, 'El estado "Creado" no existe. ')
                return redirect('index')

            default = {
                'assigned_to': request.user.id,
                'host': request.user.id,
                'event_status': default_status
            }
            form = CreateNewEvent(initial=default)
            # El resto del código sigue aquí...

        else:
            form = CreateNewEvent(request.POST)
            if form.is_valid():
                try:
                    # Obtén el estado inicial basado en la solicitud
                    if 'inbound' in request.POST or (hasattr(request.user, 'profile') and hasattr(request.user.profile, 'role') and request.user.profile.role == 'SU'):
                        initial_status_id = request.POST.get('event_status')
                    else:
                        initial_status_id = Status.objects.get(status_name='Creado').id

                    try:
                        initial_status = Status.objects.get(id=initial_status_id)
                    except Status.DoesNotExist:
                        messages.error(request, f'El estado con el ID "{initial_status_id}" no existe.')
                        return redirect('index')
                    
                    # El resto de tu código sigue aquí...
                    
                    # Crear el evento con los datos validados del formulario
                    new_event = form.save(commit=False)
                    new_event.event_status = initial_status
                    new_event.host = request.user  # El host es siempre el creador del evento
                    if not hasattr(request.user, 'profile') or not hasattr(request.user.profile, 'role') or request.user.profile.role != 'SU':
                        new_event.assigned_to = request.user  # Establecer automáticamente assigned_to como el usuario actual si el usuario no es un 'SU'
                    new_event.save()

                    # Si el usuario es un supervisor, puede asignar el evento a cualquier usuario
                    attendees = form.cleaned_data.get('attendees')
                    for attendee in attendees:
                        # Asignar el usuario asignado como atendedor
                        EventAttendee.objects.create(
                            user=attendee,
                            event=new_event
                        )

                    messages.success(request, 'Evento creado con éxito.')
                    return redirect('events')
                except IntegrityError as e:
                    messages.error(request, f'Hubo un error al crear el evento: {e}')
            else:
                # Si el formulario no es válido, agregar los errores del formulario a los mensajes
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'Error en el campo {field}: {error}')

        return render(request, 'events/create_event.html', {'form': form})
    
    except ObjectDoesNotExist:
        messages.error(request, 'El objeto solicitado no existe.')
        return redirect('index')
    except Exception as e:
        messages.error(request, f'Ha ocurrido un error inesperado: {e}')
        return redirect('index')

def event_detail(request, id):
    event = get_object_or_404(Event, id=id)
    return render(request, 'events/detail.html', {
        'event' :event,
        'events':events
    })

def edit_event(request, event_id=None):
    try:
        if event_id is not None:
            # Estamos editando un evento existente
            try:
                event = get_object_or_404(Event, pk=event_id)
            except Http404:
                messages.error(request, 'El evento con el ID "{}" no existe.'.format(event_id))
                return redirect('index')

            if request.method == 'POST':
                form = CreateNewEvent(request.POST, instance=event)
                if form.is_valid():
                    # Asigna el usuario autenticado como el editor
                    event.editor = request.user
                    print('gusardando via post si es valido')

                    # Guardar el evento con el editor actual (usuario que realiza la solicitud)
                    for field in form.changed_data:
                        old_value = getattr(event, field)
                        new_value = form.cleaned_data.get(field)
                        event.record_edit(
                            editor=request.user,
                            field_name=field,
                            old_value=str(old_value),
                            new_value=str(new_value)
                        )
                    form.save()

                    messages.success(request, 'Evento guardado con éxito.')
                    return redirect('edit_event')  # Redirige a la página de lista de edición
                else:
                    messages.error(request, 'Hubo un error al guardar el evento. Por favor, revisa el formulario.')
            else:
                form = CreateNewEvent(instance=event)
            return render(request, 'events/event_edit.html', {'form': form})
        else:
            # Estamos manejando una solicitud GET sin argumentos
            # Verificar el rol del usuario
            if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'role') and request.user.profile.role == 'SU':
                # Si el usuario es un 'SU', puede ver todos los eventos
                events = Event.objects.all().order_by('-updated_at')
            else:
                # Si no, solo puede ver los eventos que le están asignados o a los que asiste
                events = Event.objects.filter(Q(assigned_to=request.user) | Q(attendees=request.user)).distinct().order_by('-updated_at')
            return render(request, 'events/event_list.html', {'events': events})
    except Exception as e:
        messages.error(request, 'Ha ocurrido un error: {}'.format(e))
        return redirect('index')

def change_event_status(request, event_id):
    print("Inicio de vista change_event_status")
    try:
        if request.method != 'POST':
            print("solicitud GET")
            return HttpResponse("Método no permitido", status=405)
        print("solicitud Post:", request.POST)
        event = get_object_or_404(Event, pk=event_id)
        print("ID a cambiar:", str(event.id))
        new_status_id = request.POST.get('new_status_id')
        new_status = get_object_or_404(Status, pk=new_status_id)
        print("new_status_id", str(new_status))
        if request.user is None:
            print("User is none: Usuario no autenticado")
            messages.error(request, "User is none: Usuario no autenticado")
            return redirect('index')
        if event.host is not None and (event.host == request.user or request.user in event.attendees.all()):
            old_status = event.event_status
            print("old_status:", old_status)
            event.record_edit(
                editor=request.user,
                field_name='event_status',
                old_value=str(old_status),
                new_value=str(new_status)
            )
        else:
            return HttpResponse("No tienes permiso para editar este evento", status=403)
    except Exception as e:
        print(f"Error: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=500)

    return redirect('events')

def delete_event(request, event_id):
    # Asegúrate de que solo se pueda acceder a esta vista mediante POST
    if request.method == 'POST':
        event = get_object_or_404(Event, pk=event_id)

        # Verificar si el usuario es un 'SU'
        if request.user.profile.role != 'SU':
            messages.error(request, 'No tienes permiso para eliminar este evento.')
            return redirect(reverse('events'))

        event.delete()
        messages.success(request, 'El evento ha sido eliminado exitosamente.')
    else:
        messages.error(request, 'Método no permitido.')
    return redirect(reverse('events'))

# Panel

def panel(request):
    events = Event.objects.all().order_by('-created_at')
    #events = events.filter(event_status_id = 2)
    return render(request, 'panel/panel.html', {'events': events})    

# Vistas para perfil de usuario

class ProfileView(View):
    def get(self, request, user_id=None):
        print(request.GET,user_id)
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
            return render(request, 'profiles/error.html', {'message': f"An error occurred. Please make sure all fields are filled out correctly. Error: {e}"})
        except Exception as e:
            return render(request, 'profiles/error.html', {'message': str(e)})

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

def create_Classification(request):
    if request.method == 'POST':
        form = EditClassificationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('classification_list')
    else:
        form = EditClassificationForm()
    return render(request, 'configuration/create_classification.html', {'form': form})

def edit_Classification(request, Classification_id):
    # Obtén la tipificación o muestra un error 404 si no se encuentra
    classification = get_object_or_404(Classification, id=Classification_id)

    if request.method == 'POST':
        # Si el formulario se envía, rellena el formulario con los datos enviados
        form = EditClassificationForm(request.POST, instance=classification)
        if form.is_valid():
            # Si el formulario es válido, guárdalo y redirige al usuario a la lista de Classificationes
            form.save()
            return redirect('classification_list')
    else:
        # Si el formulario no se envía, rellena el formulario con los datos actuales de la tipificación
        form = EditClassificationForm(instance=classification)

    # Renderiza la plantilla con el formulario
    return render(request, 'configuration/edit_classification.html', {'form': form})

def delete_Classification(request, Classification_id):
    Classification = get_object_or_404(Classification, id=Classification_id)
    if request.method == 'POST':
        Classification.delete()
        return redirect('Classification_list')
    return render(request, 'configuration/confirm_delete.html', {'object': Classification})

def Classification_list(request):
    classifications = Classification.objects.all()
    for classification in classifications:
        print(classification)
    return render(request, 'configuration/classification_list.html', {'classifications': classifications})

# Document viewer

def document_view(request):
    documents = Document.objects.all()  # Obtiene todos los documentos
    images = Image.objects.all()        # Obtiene todas las imágenes
    context = {
        'documents': documents,
        'images': images
    }
    return render(request, 'documents/docsview.html', context)

def delete_file(request, file_id, file_type):
    if file_type == 'document':
        file_model = Document
    elif file_type == 'image':
        file_model = Image
    else:
        messages.error(request, 'Tipo de archivo no válido.')
        return redirect('docsview')

    file_instance = get_object_or_404(file_model, id=file_id)
    if request.method == 'POST':
        file_instance.upload.delete()  # Esto elimina el archivo del sistema de archivos.
        file_instance.delete()         # Esto elimina la instancia del modelo de la base de datos.
        messages.success(request, f'El {file_type} ha sido eliminado exitosamente.')
        return redirect('docsview')
    else:
        # Si no es una solicitud POST, muestra la página de confirmación.
        return render(request, 'documents/confirmar_eliminacion.html', {'file': file_instance, 'type': file_type})

# Vista para subir documentos
class DocumentUploadView(FormView):
    template_name = 'documents/upload.html' # El nombre del template que quieres usar
    form_class = DocumentForm # El formulario que quieres usar
    success_url = reverse_lazy('docsview')# La url a la que quieres redirigir después de subir el archivo
    def form_valid(self, form):
        # Este método se ejecuta si el formulario es válido
        # Aquí puedes guardar el archivo en tu modelo
        file = form.cleaned_data['file'] # Obtiene el archivo del formulario
        document = Document(upload=file) # Crea una instancia de tu modelo con el archivo
        document.save() # Guarda el archivo en la base de datos
        return super().form_valid(form) # Retorna la vista de éxito

# Vista para subir imágenes
class ImageUploadView(FormView):
    template_name = 'documents/upload.html' # El nombre del template que quieres usar
    form_class = ImageForm # El formulario que quieres usar
    success_url = reverse_lazy('docsview')# La url a la que quieres redirigir después de subir el archivo

    def form_valid(self, form):
        # Este método se ejecuta si el formulario es válido
        # Aquí puedes guardar el archivo en tu modelo
        file = form.cleaned_data['file'] # Obtiene el archivo del formulario
        image = Image(upload=file) # Crea una instancia de tu modelo con el archivo
        image.save() # Guarda el archivo en la base de datos
        return super().form_valid(form) # Retorna la vista de éxito

# about upload

def upload_image(request):
    if request.method == 'POST':
        try:
            image = request.FILES['image']
            fs = FileSystemStorage()
            filename = fs.save(image.name, image)
            uploaded_file_url = fs.url(filename)
            messages.success(request, 'Imagen subida con éxito.')
            return redirect('about')
        except KeyError:
            messages.error(request, 'Por favor, selecciona una imagen para subir.')
    return render(request, 'about/about.html')

# GTR

def management(request):
    # Obtén los eventos asignados al usuario logueado
    eventos_asignados = Event.objects.filter(assigned_to=request.user).order_by('-created_at')
    classifications = Classification.objects.all()

    if request.method == 'POST':
        # Obtén el evento y la clasificación del formulario
        evento_id = request.POST.get('evento')
        classification_id = request.POST.get('classification')
        comentario = request.POST.get('comentario')

        # Encuentra el evento y la clasificación en la base de datos
        evento = Event.objects.get(id=evento_id)
        classification = Classification.objects.get(id=classification_id)

        # Actualiza el evento
        evento.classification = classification
        evento.comentario = comentario
        evento.estado = 'Finalizado'
        evento.save()

        messages.success(request, 'Evento actualizado con éxito.')
        return redirect(reverse('manager'))

    return render(request, 'management/manager.html', {
        'eventos_asignados': eventos_asignados,
        'classifications': classifications
        })

# Añade esta función a tu vista
def update_event(request):
    if request.method == 'POST':
        # Obtén el ID del evento y si está seleccionado o no
        evento_id = request.POST.get('evento')
        selected = request.POST.get('selected') == 'true'

        # Encuentra el evento en la base de datos
        evento = Event.objects.get(id=evento_id)

        # Actualiza el estado del evento
        evento.estado = 'Finalizado' if selected else 'No finalizado'
        evento.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False})
