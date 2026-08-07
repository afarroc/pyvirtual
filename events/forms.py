from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.db.models import Q
from django.utils import timezone
from .models import Task, Event, Status, ProjectStatus, TaskStatus, Classification, Project, ProjectTemplate, TemplateTask, Tag, TaskSchedule, Reminder

class CreateNewEvent(forms.ModelForm):

    class Meta:
        model = Event
        fields = ['title', 'description', 'attendees', 'venue', 'event_status', 'event_category', 'max_attendees', 'ticket_price', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'attendees': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'venue': forms.TextInput(attrs={'class': 'form-control'}),
            'event_status': forms.Select(attrs={'class': 'form-select'}),
            'event_category': forms.TextInput(attrs={'class': 'form-control'}),
            'max_attendees': forms.NumberInput(attrs={'class': 'form-control'}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }

class AssignAttendeesForm(forms.Form):
    attendees = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

class CreateNewTask(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].required = False
        self.fields['event'].required = False
        self.fields['project'].required = False
        self.fields['ticket_price'].required = False

    class Meta:
        model = Task
        fields = ['title', 'description', 'important', 'project', 'task_status', 'event', 'assigned_to','ticket_price']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'important': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'task_status': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control'}),

        }

class CreateNewProject(forms.ModelForm):
    

    class Meta:
        model = Project
        fields = ['title', 'description', 'event', 'assigned_to', 'attendees', 'project_status', 'ticket_price', ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'attendees': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'project_status': forms.Select(attrs={'class': 'form-select'}),
            'ticket_price': forms.NumberInput(attrs={'class': 'form-control'}),

        }
       
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_status', 'venue', 'host', 'event_category', 'max_attendees', 'ticket_price']

class EventEditForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'event_status']




class EventStatusForm(forms.ModelForm):
    color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color'}),
        required=False,
    )
    class Meta:
        model = Status
        fields = ['status_name', 'icon', 'active', 'color']

class TaskStatusForm(forms.ModelForm):
    color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color'}),
        required=False,
    )
    class Meta:
        model = TaskStatus
        fields = ['status_name', 'icon', 'active', 'color']

class ProjectStatusForm(forms.ModelForm):
    color = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'color'}),
        required=False,
    )
    class Meta:
        model = ProjectStatus
        fields = ['status_name', 'icon', 'active', 'color']



class EditClassificationForm(forms.ModelForm):
    class Meta:
        model = Classification
        fields = ['nombre', 'descripcion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].label = "Nombre de la Tipificación"
        self.fields['descripcion'].label = "Descripción de la Tipificación"


# Formularios para plantillas de proyectos
class ProjectTemplateForm(forms.ModelForm):
    class Meta:
        model = ProjectTemplate
        fields = ['name', 'description', 'category', 'estimated_duration', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Lanzamiento de Producto, Desarrollo Web, etc.'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe qué tipo de proyecto cubre esta plantilla...'
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Marketing, Desarrollo, Diseño, etc.'
            }),
            'estimated_duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Duración en días'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'name': 'Nombre de la Plantilla',
            'description': 'Descripción',
            'category': 'Categoría',
            'estimated_duration': 'Duración Estimada (días)',
            'is_public': '¿Es pública?',
        }
        help_texts = {
            'is_public': 'Si está marcada, otros usuarios podrán usar esta plantilla',
        }


class TemplateTaskForm(forms.ModelForm):
    class Meta:
        model = TemplateTask
        fields = ['title', 'description', 'estimated_hours', 'required_skills']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la tarea'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descripción de la tarea...'
            }),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.5',
                'step': '0.5',
                'placeholder': 'Horas estimadas'
            }),
            'required_skills': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '3'
            }),
        }
        labels = {
            'title': 'Título de la Tarea',
            'description': 'Descripción',
            'estimated_hours': 'Horas Estimadas',
            'required_skills': 'Habilidades Requeridas',
        }


# FormSet para tareas de plantilla
TemplateTaskFormSet = inlineformset_factory(
    ProjectTemplate,
    TemplateTask,
    form=TemplateTaskForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# Formulario para recordatorios
class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ['title', 'description', 'remind_at', 'task', 'project', 'event', 'reminder_type']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Revisar proyecto, Recordar reunión, etc.'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detalles adicionales del recordatorio...'
            }),
            'remind_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'task': forms.Select(attrs={
                'class': 'form-select'
            }),
            'project': forms.Select(attrs={
                'class': 'form-select'
            }),
            'event': forms.Select(attrs={
                'class': 'form-select'
            }),
            'reminder_type': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'title': 'Título del Recordatorio',
            'description': 'Descripción',
            'remind_at': 'Fecha y Hora del Recordatorio',
            'task': 'Tarea Relacionada (Opcional)',
            'project': 'Proyecto Relacionado (Opcional)',
            'event': 'Evento Relacionado (Opcional)',
            'reminder_type': 'Tipo de Notificación',
        }
        help_texts = {
            'remind_at': 'Selecciona cuándo quieres recibir el recordatorio',
            'reminder_type': 'Elige cómo quieres recibir la notificación',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Importar aquí para evitar circular imports
        from .models import Task, Project, Event

        # Filtrar querysets por usuario si es necesario
        if self.user:
            from .models import Task, Project, Event
            self.fields['task'].queryset = Task.objects.filter(
                Q(host=self.user) | Q(assigned_to=self.user)
            ).distinct()
            self.fields['project'].queryset = Project.objects.filter(
                Q(host=self.user) | Q(assigned_to=self.user) | Q(attendees=self.user)
            ).distinct()
            self.fields['event'].queryset = Event.objects.filter(
                Q(host=self.user) | Q(assigned_to=self.user) | Q(attendees=self.user)
            ).distinct()

        # Hacer los campos de relación opcionales
        self.fields['task'].required = False
        self.fields['task'].empty_label = "Sin tarea específica"
        self.fields['project'].required = False
        self.fields['project'].empty_label = "Sin proyecto específico"
        self.fields['event'].required = False
        self.fields['event'].empty_label = "Sin evento específico"

    def clean_remind_at(self):
        remind_at = self.cleaned_data.get('remind_at')
        if remind_at and remind_at <= timezone.now():
            raise forms.ValidationError('La fecha del recordatorio debe ser futura.')
        return remind_at

    def save(self, user=None):
        """Crear un recordatorio desde el formulario"""
        from .models import Reminder

        reminder = Reminder.objects.create(
            title=self.cleaned_data['title'],
            description=self.cleaned_data.get('description', ''),
            remind_at=self.cleaned_data['remind_at'],
            task=self.cleaned_data.get('task'),
            project=self.cleaned_data.get('project'),
            event=self.cleaned_data.get('event'),
            reminder_type=self.cleaned_data['reminder_type'],
            created_by=user
        )
        return reminder


# Formulario para programaciones recurrentes de tareas
class TaskScheduleForm(forms.ModelForm):
    """
    Formulario para crear y editar programaciones recurrentes de tareas
    """
    # Campo adicional para duración en horas
    duration_hours = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0.25,
        max_value=24,
        initial=1.0,
        help_text="Duración en horas (ej: 1.5 para 1 hora y 30 minutos)",
        error_messages={
            'required': 'La duración es obligatoria.',
            'min_value': 'La duración mínima permitida es de 15 minutos (0.25 horas).',
            'max_value': 'La duración máxima permitida es de 24 horas.',
            'invalid': 'Ingrese una duración válida en horas (ej: 1.5).'
        }
    )
    interval_days = forms.IntegerField(
        min_value=1,
        initial=1,
        required=False,
        help_text="Cantidad de días entre repeticiones (solo para recurrencia personalizada).",
        error_messages={
            'required': 'Para recurrencia personalizada debes indicar cada cuántos días se repite.',
            'min_value': 'El intervalo debe ser de al menos 1 día.'
        }
    )

    class Meta:
        model = TaskSchedule
        fields = [
            'task', 'recurrence_type', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday', 'start_time',
            'start_date', 'end_date', 'is_active', 'interval_days'
        ]
        widgets = {
            'task': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'recurrence_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_recurrence_type'
            }),
            'monday': forms.CheckboxInput(attrs={
                'class': 'form-check-input day-checkbox'
            }),
            'tuesday': forms.CheckboxInput(attrs={
                'class': 'form-check-input day-checkbox'
            }),
            'wednesday': forms.CheckboxInput(attrs={
                'class': 'form-check-input day-checkbox'
            }),
            'thursday': forms.CheckboxInput(attrs={
                'class': 'form-check-input day-checkbox'
            }),
            'friday': forms.CheckboxInput(attrs={
                'class': 'form-check-input day-checkbox'
            }),
            'saturday': forms.CheckboxInput(attrs={
                'class': 'form-check-input day-checkbox'
            }),
            'sunday': forms.CheckboxInput(attrs={
                'class': 'form-check-input day-checkbox'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        },
        error_messages = {
            'task': {
                'required': 'Debes seleccionar una tarea para programar.',
                'invalid_choice': 'La tarea seleccionada no es válida.'
            },
            'recurrence_type': {
                'required': 'Debes seleccionar un tipo de recurrencia.',
                'invalid_choice': 'El tipo de recurrencia seleccionado no es válido.'
            },
            'start_time': {
                'required': 'La hora de inicio es obligatoria.',
                'invalid': 'Ingresa una hora válida en formato HH:MM.'
            },
            'start_date': {
                'required': 'La fecha de inicio es obligatoria.',
                'invalid': 'Ingresa una fecha válida en formato YYYY-MM-DD.'
            },
            'end_date': {
                'invalid': 'Ingresa una fecha válida en formato YYYY-MM-DD.'
            }
        }
        labels = {
            'task': 'Tarea a Programar',
            'recurrence_type': 'Tipo de Recurrencia',
            'monday': 'Lunes',
            'tuesday': 'Martes',
            'wednesday': 'Miércoles',
            'thursday': 'Jueves',
            'friday': 'Viernes',
            'saturday': 'Sábado',
            'sunday': 'Domingo',
            'start_time': 'Hora de Inicio',
            'start_date': 'Fecha de Inicio',
            'end_date': 'Fecha de Fin (Opcional)',
            'is_active': 'Programación Activa',
            'interval_days': 'Intervalo de días',
        }
        help_texts = {
            'recurrence_type': 'Selecciona cómo se repetirá esta tarea',
            'start_date': 'Fecha desde la que comenzarán las programaciones',
            'end_date': 'Fecha hasta la que se repetirán las programaciones (deja vacío para indefinido)',
            'is_active': 'Desmarca para pausar temporalmente esta programación',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Importar aquí para evitar circular imports
        from .models import Task

        # Filtrar tareas por usuario
        if self.user:
            self.fields['task'].queryset = Task.objects.filter(
                Q(host=self.user) | Q(assigned_to=self.user)
            ).distinct().order_by('title')

        # Configurar campos condicionales
        if self.instance and self.instance.pk:
            # Si es edición, poblar el campo duration_hours
            if hasattr(self.instance, 'duration'):
                self.fields['duration_hours'].initial = self.instance.duration.total_seconds() / 3600

        # Configurar tipos de datos específicos para mejor UX
        self.fields['start_date'].widget.attrs.update({
            'type': 'date',
            'min': timezone.now().date().isoformat()
        })
        self.fields['end_date'].widget.attrs.update({
            'type': 'date'
        })
        self.fields['start_time'].widget.attrs.update({
            'type': 'time'
        })

    def clean(self):
        cleaned_data = super().clean()
        recurrence_type = cleaned_data.get('recurrence_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        duration_hours = cleaned_data.get('duration_hours')

        # Validar fecha de inicio no sea en el pasado
        if start_date and start_date < timezone.now().date():
            raise forms.ValidationError({
                'start_date': 'La fecha de inicio debe ser hoy o una fecha futura. No se permiten fechas pasadas.'
            })

        # Validar fechas
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError({
                'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio. Corrige las fechas para continuar.'
            })

        # Validar duración razonable
        if duration_hours and (duration_hours < 0.25 or duration_hours > 24):
            raise forms.ValidationError({
                'duration_hours': 'La duración debe estar entre 15 minutos (0.25 horas) y 24 horas. Ajusta el tiempo estimado.'
            })

        # Validar que al menos un día esté seleccionado para recurrencia semanal
        if recurrence_type == 'weekly':
            days_selected = [
                cleaned_data.get('monday', False),
                cleaned_data.get('tuesday', False),
                cleaned_data.get('wednesday', False),
                cleaned_data.get('thursday', False),
                cleaned_data.get('friday', False),
                cleaned_data.get('saturday', False),
                cleaned_data.get('sunday', False)
            ]
            if not any(days_selected):
                raise forms.ValidationError({
                    'monday': 'Para la recurrencia semanal, debes seleccionar al menos un día de la semana.',
                    'tuesday': 'Marca al menos un día para que la tarea se repita semanalmente.',
                    'wednesday': 'Selecciona los días en que quieres que se ejecute esta tarea.',
                    'thursday': 'Es obligatorio elegir al menos un día de la semana.',
                    'friday': 'Por favor, indica qué días debe repetirse la tarea.',
                    'saturday': 'Selecciona al menos un día para continuar con la configuración.',
                    'sunday': 'Debes marcar al menos un día para la programación semanal.'
                })

        # Validar intervalo en días para recurrencia personalizada
        if recurrence_type == 'custom':
            interval_days = cleaned_data.get('interval_days')
            if not interval_days or interval_days < 1:
                raise forms.ValidationError({
                    'interval_days': 'Para la recurrencia personalizada debes indicar un intervalo mayor o igual a 1 día.'
                })

        # Validar que la tarea no tenga ya una programación activa
        task = cleaned_data.get('task')
        if task:
            from .models import TaskSchedule
            existing_schedule = TaskSchedule.objects.filter(
                task=task,
                is_active=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            if existing_schedule.exists():
                raise forms.ValidationError({
                    'task': f'La tarea "{task.title}" ya tiene una programación activa. Para crear una nueva, primero desactiva la programación existente.'
                })

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Asignar el usuario host
        if self.user:
            instance.host = self.user

        # Convertir duration_hours a DurationField
        duration_hours = self.cleaned_data.get('duration_hours', 1.0)
        from datetime import timedelta
        instance.duration = timedelta(hours=float(duration_hours))

        if commit:
            instance.save()

        return instance