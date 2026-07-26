from django.conf import settings
import os
from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

# Modelo para los estados del evento
class Status(models.Model):
    status_name = models.CharField(max_length=50)
    icon = models.CharField(max_length=30, blank=True, null=True)
    active = models.BooleanField(default=True)
    color = models.CharField(max_length=30, default="white")
    
    def __str__(self):
        return self.status_name

class ProjectStatus(models.Model):
    status_name = models.CharField(max_length=50)
    icon = models.CharField(max_length=30, blank=True, null=True)
    active = models.BooleanField(default=True)
    color = models.CharField(max_length=30, default="white")
    
    def __str__(self):
        return self.status_name

class TaskStatus(models.Model):
    status_name = models.CharField(max_length=50)
    icon = models.CharField(max_length=30, blank=True, null=True)
    active = models.BooleanField(default=True)
    color = models.CharField(max_length=30, default="white")
    
    def __str__(self):
        return self.status_name

# Classificationes
class Classification(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre

# Modelo para registrar los estados por los que pasa cada proyecto
class ProjectState(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    status = models.ForeignKey('ProjectStatus', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si es un nuevo estado, establecer la hora de inicio
        if not self.id:
            self.start_time = timezone.now()
        # Si se está finalizando un estado, establecer la hora de finalización
        else:
            self.end_time = timezone.now()
        super(ProjectState, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.status.status_name} ({self.start_time} - {self.end_time})"
    
# Modelo para registrar las ediciones realizadas en los campos del proyecto
class ProjectHistory(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    edited_at = models.DateTimeField(auto_now_add=True)
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.project.id} - {self.field_name} - {self.editor.username} : - ({self.old_value} - {self.new_value})"

# Modelo para los proyectos    
class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    done = models.BooleanField(default=False)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, null=True, blank=True)
    project_status = models.ForeignKey(ProjectStatus, on_delete=models.CASCADE)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_projects')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_projets') 
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ProjectAttendee', related_name='collaborating_projects',blank=True) 
    ticket_price = models.DecimalField(default=0, max_digits=6, decimal_places=2)

    # Generic relation for reverse querying from InboxItem
    processed_inbox_items = GenericRelation(
        'InboxItem',
        related_name='processed_projects',
        content_type_field='processed_to_content_type',
        object_id_field='processed_to_object_id',
        blank=True
    )

    def change_status(self, new_status_id):
        # Obtener el nuevo estado
        new_status = ProjectStatus.objects.get(id=new_status_id)
        
        # Finalizar el estado actual
        current_state = self.projectstate_set.filter(end_time__isnull=True).last()
        if current_state:
            current_state.end_time = timezone.now()
            current_state.save()
        
        # Crear un nuevo estado con el nuevo estado proporcionado
        ProjectState.objects.create(project=self, status=new_status)
        
        # Actualizar el estado del proyecto
        self.project_status = new_status
        self.updated_at = timezone.now()
        self.save()

    def record_edit(self, editor, field_name, old_value, new_value):
        # Registrar la edición en el historial
        project_history = ProjectHistory.objects.create(
            project=self,
            editor=editor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value
        )
        print(f"Registro de edición creado: {project_history}")
        
        # Si el campo editado es 'projects_status', ejecutar change_status
        if field_name == 'project_status':
            new_status = ProjectStatus.objects.get(status_name=new_value)
            self.change_status(new_status.id)
   
    def __str__(self):
        return f"{self.title} - {self.event}"

# Modelo para registrar los asistentes al Proyecto
class ProjectAttendee(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    registration_time = models.DateTimeField(auto_now_add=True)
    has_paid = models.BooleanField(default=False)  # Campo nuevo para el pago
    notes = models.TextField(blank=True, null=True)  # Campo nuevo para notas adicionales

# Modelo para registrar los estados por los que pasa cada tarea
class TaskState(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    status = models.ForeignKey('TaskStatus', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si es un nuevo estado, establecer la hora de inicio
        if not self.id:
            self.start_time = timezone.now()
        # Si se está finalizando un estado, establecer la hora de finalización
        else:
            self.end_time = timezone.now()
        super(TaskState, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.status.status_name} ({self.start_time} - {self.end_time})"
    
# Modelo para registrar las ediciones realizadas en los campos de la tarea
class TaskHistory(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    edited_at = models.DateTimeField(auto_now_add=True)
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.task.id} - {self.field_name} - {self.editor.username} : - ({self.old_value} - {self.new_value})"

# Modelo para las tareas
class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Agregar blank=True para permitir que el campo sea opcional en formularios
    done = models.BooleanField(default=False)
    project = models.ForeignKey('Project', on_delete=models.CASCADE, blank=True, null=True)  # Usa comillas si Project está definido más abajo en el mismo archivo
    event = models.ForeignKey('Event', on_delete=models.CASCADE, blank=True, null=True)
    task_status = models.ForeignKey(TaskStatus, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_tasks')
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_tasks')  # Asegúrate de que esta línea esté presente
    ticket_price = models.DecimalField(default=0, max_digits=6, decimal_places=2)
    tags = models.ManyToManyField('Tag', blank=True)

    # Generic relation for reverse querying from InboxItem
    processed_inbox_items = GenericRelation(
        'InboxItem',
        related_name='processed_tasks',
        content_type_field='processed_to_content_type',
        object_id_field='processed_to_object_id',
        blank=True
    )

    def change_status(self, new_status_id, user=None):
        # Obtener el nuevo estado
        new_status = TaskStatus.objects.get(id=new_status_id)

        # Guardar el estado anterior para el historial
        old_status_name = self.task_status.status_name if self.task_status else None

        # Finalizar el estado actual
        current_state = self.taskstate_set.filter(end_time__isnull=True).last()
        if current_state:
            current_state.end_time = timezone.now()
            current_state.save()

        # Crear un nuevo estado con el nuevo estado proporcionado
        TaskState.objects.create(task=self, status=new_status)

        # Actualizar el estado del evento
        self.task_status = new_status
        self.updated_at = timezone.now()
        self.save()

        # Registrar en el historial si se proporciona un usuario
        if user:
            TaskHistory.objects.create(
                task=self,
                editor=user,
                field_name='task_status',
                old_value=old_status_name,
                new_value=new_status.status_name
            )

    def record_edit(self, editor, field_name, old_value, new_value):
        # Registrar la edición en el historial
        task_history = TaskHistory.objects.create(
            task=self,
            editor=editor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value
        )
        print(f"Registro de edición creado: {task_history}")
        
        # Si el campo editado es 'task_status', ejecutar change_status
        if field_name == 'task_status':
            new_status = TaskStatus.objects.get(status_name=new_value)
            self.change_status(new_status.id)

    def __str__(self):
        return f"{self.title} - {self.event}"

from django.core.exceptions import ValidationError

class TaskProgram(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_programs')
    task = models.ForeignKey('Task', on_delete=models.CASCADE)

    def clean(self):
        # Ensure end_time is after start_time
        if self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Task Program"
        verbose_name_plural = "Task Programs"

# Modelo para programaciones recurrentes de tareas
class TaskSchedule(models.Model):
    """Modelo para programaciones recurrentes de tareas"""
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Configuración de recurrencia
    recurrence_type = models.CharField(max_length=20, choices=[
        ('weekly', 'Semanal'),
        ('daily', 'Diaria'),
        ('custom', 'Personalizada')
    ], default='weekly')
    interval_days = models.PositiveIntegerField(default=1, help_text="Cantidad de días entre ocurrencias (solo para recurrencia personalizada)")

    # Días de la semana (para recurrencia semanal)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)

    # Horarios
    start_time = models.TimeField()  # Hora de inicio
    duration = models.DurationField(default='01:00:00')  # Duración por defecto 1 hora

    # Período de validez
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # Null = indefinido

    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def _should_schedule_on_date(self, date):
        """Determina si la tarea debe programarse en una fecha específica"""
        if self.recurrence_type == 'daily':
            return True

        if self.recurrence_type == 'custom':
            if not self.interval_days or self.interval_days < 1:
                return False
            days_since_start = (date - self.start_date).days
            return days_since_start >= 0 and days_since_start % self.interval_days == 0

        weekday = date.weekday()  # 0=lunes, 6=domingo
        weekday_map = {
            0: self.monday,
            1: self.tuesday,
            2: self.wednesday,
            3: self.thursday,
            4: self.friday,
            5: self.saturday,
            6: self.sunday
        }

        return weekday_map.get(weekday, False)

    def get_selected_days_display(self):
        """Retorna una representación legible de los días seleccionados"""
        if self.recurrence_type == 'custom':
            return f"Cada {self.interval_days} día(s)"

        days = []
        if self.monday: days.append('Lun')
        if self.tuesday: days.append('Mar')
        if self.wednesday: days.append('Mié')
        if self.thursday: days.append('Jue')
        if self.friday: days.append('Vie')
        if self.saturday: days.append('Sáb')
        if self.sunday: days.append('Dom')

        if not days:
            return "Ningún día seleccionado"

        return ", ".join(days)

    def generate_occurrences(self, limit=10):
        """
        Genera una lista de ocurrencias futuras basadas en la configuración recurrente
        """
        from datetime import datetime, timedelta
        occurrences = []
        current_date = max(self.start_date, timezone.now().date())

        while len(occurrences) < limit:
            if self.end_date and current_date > self.end_date:
                break

            if self._should_schedule_on_date(current_date):
                start_datetime = timezone.make_aware(datetime.combine(current_date, self.start_time))
                end_datetime = start_datetime + self.duration
                occurrences.append({
                    'date': current_date,
                    'start_time': start_datetime,
                    'end_time': end_datetime
                })

            current_date += timedelta(days=1)

        return occurrences

    def create_task_programs(self, occurrences=None):
        """
        Crea instancias de TaskProgram para las ocurrencias especificadas
        """
        if occurrences is None:
            occurrences = self.generate_occurrences()

        created_programs = []
        for occurrence in occurrences:
            # Crear TaskProgram
            program, created = TaskProgram.objects.get_or_create(
                task=self.task,
                host=self.host,  # Usar el host de la programación, no de la tarea
                start_time=occurrence['start_time'],
                defaults={
                    'title': f"{self.task.title} - {occurrence['start_time'].strftime('%d/%m/%Y %H:%M')}",
                    'end_time': occurrence['end_time'],
                }
            )

            if created:
                created_programs.append(program)

        return created_programs

    def get_next_occurrence(self):
        """
        Obtiene la próxima ocurrencia futura
        """
        occurrences = self.generate_occurrences(limit=1)
        return occurrences[0] if occurrences else None

    def is_active_schedule(self):
        """
        Verifica si la programación está activa (no ha expirado)
        """
        if not self.is_active:
            return False

        if self.end_date and timezone.now().date() > self.end_date:
            return False

        return True

    def __str__(self):
        return f"{self.task.title} - {self.get_recurrence_type_display()} a las {self.start_time}"

    class Meta:
        verbose_name = "Programación de Tarea"
        verbose_name_plural = "Programaciones de Tareas"
        ordering = ['start_time']

# Modelo para registrar los estados por los que pasa cada evento
class EventState(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE)
    status = models.ForeignKey('Status', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si es un nuevo estado, establecer la hora de inicio
        if not self.id:
            self.start_time = timezone.now()
        # Si se está finalizando un estado, establecer la hora de finalización
        else:
            self.end_time = timezone.now()
        super(EventState, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.status.status_name} ({self.start_time} - {self.end_time})"
    
# Modelo para registrar las ediciones realizadas en los campos del evento
class EventHistory(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE)
    edited_at = models.DateTimeField(auto_now_add=True)
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.event.id} - {self.field_name} - {self.editor.username} : - ({self.old_value} - {self.new_value})"

# Sistema de etiquetas mejorado para múltiples metodologías
class TagCategory(models.Model):
    name = models.CharField(max_length=50, help_text="GTD, Priority, Context, Custom")
    description = models.TextField()
    color = models.CharField(max_length=7, default="#007bff")
    icon = models.CharField(max_length=50, blank=True)
    is_system = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Tag Categories"

class Tag(models.Model):
    name = models.CharField(max_length=50)
    category = models.ForeignKey(TagCategory, on_delete=models.CASCADE)
    color = models.CharField(max_length=7, default="#6c757d")
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)  # Para etiquetas predefinidas
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category.name}: {self.name}"

    class Meta:
        unique_together = ['name', 'category']

# Modelo principal del evento
class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    event_status = models.ForeignKey(Status, on_delete=models.CASCADE)
    venue = models.CharField(max_length=200, blank=True)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_events')
    event_category = models.CharField(max_length=50, blank=True)
    max_attendees = models.IntegerField(default=0)
    ticket_price = models.DecimalField(default=0, max_digits=6, decimal_places=2)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_events') 
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, through='EventAttendee', related_name='collaborating_events', blank=True) 
    tags = models.ManyToManyField(Tag, blank=True)
    links = models.ManyToManyField('self', blank=True, symmetrical=False)
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True, blank=True)

    def change_status(self, new_status_id):
        # Obtener el nuevo estado
        new_status = Status.objects.get(id=new_status_id)
        
        # Finalizar el estado actual
        current_state = self.eventstate_set.filter(end_time__isnull=True).last()
        if current_state:
            current_state.end_time = timezone.now()
            current_state.save()
        
        # Crear un nuevo estado con el nuevo estado proporcionado
        EventState.objects.create(event=self, status=new_status)
        
        # Actualizar el estado del evento
        self.event_status = new_status
        self.updated_at = timezone.now()
        self.save()

    def record_edit(self, editor, field_name, old_value, new_value):
        # Registrar la edición en el historial
        event_history = EventHistory.objects.create(
            event=self,
            editor=editor,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value
        )
        print(f"Registro de edición creado: {event_history}")
    
        # Si el campo editado es 'event_status', ejecutar change_status
        if field_name == 'event_status':
            new_status = Status.objects.get(status_name=new_value)
            self.change_status(new_status.id)
            
    def __str__(self):
        return f"{self.title}"

# Modelo para registrar los asistentes al evento
class EventAttendee(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    registration_time = models.DateTimeField(auto_now_add=True)
    has_paid = models.BooleanField(default=False)  # Campo nuevo para el pago
    notes = models.TextField(blank=True, null=True)  # Campo nuevo para notas adicionales



class CreditAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.user.username} - {self.balance} créditos"

    def add_credits(self, amount):
        if not isinstance(amount, Decimal):
            amount = Decimal(amount)
        self.balance += amount
        self.save()

    def subtract_credits(self, amount):
        if not isinstance(amount, Decimal):
            amount = Decimal(amount)
        if amount > self.balance:
            raise ValueError("No hay suficientes créditos")
        self.balance -= amount
        self.save()


# Dependencias entre tareas
class TaskDependency(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='blocking')
    dependency_type = models.CharField(max_length=20, choices=[
        ('finish_to_start', 'Finalizar para comenzar'),
        ('start_to_start', 'Comenzar para comenzar'),
        ('finish_to_finish', 'Finalizar para finalizar'),
        ('start_to_finish', 'Comenzar para finalizar')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.title} depende de {self.depends_on.title}"

    class Meta:
        unique_together = ['task', 'depends_on']

# Plantillas de proyectos
class ProjectTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    estimated_duration = models.IntegerField(help_text="Duración en días")
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class TemplateTask(models.Model):
    template = models.ForeignKey(ProjectTemplate, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField()
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2)
    required_skills = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return f"{self.template.name}: {self.title}"

    class Meta:
        ordering = ['order']

# Inbox para GTD (Getting Things Done)
class InboxItem(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Generic foreign key para apuntar a Task o Project
    processed_to_content_type = models.ForeignKey('contenttypes.ContentType', null=True, blank=True, on_delete=models.SET_NULL)
    processed_to_object_id = models.PositiveIntegerField(null=True, blank=True)
    processed_to = GenericForeignKey('processed_to_content_type', 'processed_to_object_id')

    tags = models.ManyToManyField(Tag, blank=True)

    # Campos GTD mejorados
    gtd_category = models.CharField(max_length=20, choices=[
        ('accionable', 'Accionable'),
        ('no_accionable', 'No Accionable'),
        ('pendiente', 'Pendiente de Categorizar')
    ], default='pendiente', help_text="Categorización GTD principal")

    action_type = models.CharField(max_length=20, choices=[
        ('hacer', 'Hacer'),
        ('delegar', 'Delegar'),
        ('posponer', 'Posponer'),
        ('proyecto', 'Convertir en Proyecto'),
        ('eliminar', 'Eliminar'),
        ('archivar', 'Archivar para Referencia'),
        ('incubar', 'Incubar (Algún Día)'),
        ('esperar', 'Esperar Más Información')
    ], blank=True, null=True, help_text="Tipo de acción específica")

    priority = models.CharField(max_length=10, choices=[
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
    ], default='media', help_text="Prioridad del item")

    context = models.CharField(max_length=50, blank=True, help_text="Contexto donde se puede ejecutar (ej: @casa, @trabajo, @teléfono)")

    estimated_time = models.IntegerField(blank=True, null=True, help_text="Tiempo estimado en minutos")

    due_date = models.DateTimeField(blank=True, null=True, help_text="Fecha límite si aplica")

    energy_required = models.CharField(max_length=20, choices=[
        ('baja', 'Baja Energía'),
        ('media', 'Media Energía'),
        ('alta', 'Alta Energía')
    ], default='media', help_text="Nivel de energía mental requerido")

    notes = models.TextField(blank=True, help_text="Notas adicionales para el procesamiento")

    # Sistema de clasificación colaborativa
    is_public = models.BooleanField(default=False, help_text="¿Puede ser visto por otros usuarios?")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_inbox_items',
        help_text="Usuario asignado para procesar este item"
    )
    authorized_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='InboxItemAuthorization',
        through_fields=('inbox_item', 'user'),
        related_name='authorized_inbox_items',
        blank=True,
        help_text="Usuarios autorizados para ver y clasificar este item"
    )

    # Campos para consenso de clasificación
    classification_votes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='InboxItemClassification',
        through_fields=('inbox_item', 'user'),
        related_name='classified_inbox_items',
        blank=True,
        help_text="Usuarios que han votado en la clasificación"
    )

    # Campos para seguimiento de actividad
    last_activity = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0, help_text="Número de veces que ha sido visto")

    # Sistema "Waiting For" - para tareas que esperan respuesta externa
    waiting_for = models.TextField(blank=True, help_text="¿Qué se está esperando? (ej: respuesta de cliente)")
    waiting_for_date = models.DateTimeField(blank=True, null=True, help_text="Fecha esperada de respuesta")

    # Sistema de revisión GTD
    next_review_date = models.DateTimeField(blank=True, null=True, help_text="Próxima fecha de revisión")
    review_notes = models.TextField(blank=True, help_text="Notas de revisiones anteriores")

    # Metadatos adicionales para análisis
    created_during = models.CharField(max_length=20, choices=[
        ('morning', 'Mañana (6-12)'),
        ('afternoon', 'Tarde (12-18)'),
        ('evening', 'Noche (18-24)'),
        ('night', 'Madrugada (0-6)')
    ], blank=True, help_text="Horario de creación para análisis de patrones")

    # Campo para almacenar contexto específico del usuario
    user_context = models.JSONField(blank=True, null=True, help_text="Contexto personalizado del usuario")

    def __str__(self):
        return f"{self.title} [{self.gtd_category}]"

    class Meta:
        ordering = ['-created_at']

    def get_classification_consensus(self):
        """Obtiene el consenso de clasificación basado en votos"""
        classifications = self.inboxitemclassification_set.values('gtd_category').annotate(
            count=models.Count('gtd_category')
        ).order_by('-count')

        if classifications:
            return classifications[0]['gtd_category']
        return self.gtd_category

    def get_action_type_consensus(self):
        """Obtiene el consenso de tipo de acción basado en votos"""
        action_types = self.inboxitemclassification_set.values('action_type').annotate(
            count=models.Count('action_type')
        ).order_by('-count')

        if action_types:
            return action_types[0]['action_type']
        return self.action_type

    def increment_views(self):
        """Incrementa el contador de vistas"""
        self.view_count += 1
        self.save(update_fields=['view_count', 'last_activity'])

    def assign_to_available_user(self):
        """
        Asigna automáticamente el item a un usuario disponible
        basado en carga de trabajo y especialización
        """
        from django.contrib.auth.models import User
        from django.db.models import Count

        # Obtener usuarios disponibles (con perfiles activos)
        available_users = User.objects.filter(
            is_active=True,
            profile__isnull=False
        ).exclude(
            profile__role__in=['SU']  # Excluir superusuarios de asignación automática
        )

        if not available_users.exists():
            return False

        # Calcular carga actual de cada usuario
        user_workloads = {}
        for user in available_users:
            # Contar items asignados no procesados
            assigned_count = InboxItem.objects.filter(
                assigned_to=user,
                is_processed=False
            ).count()

            # Bonus por especialización (usuarios CX tienen prioridad para emails)
            specialization_bonus = 0
            if hasattr(user, 'profile') and user.profile:
                if 'CX' in str(user.profile.role or ''):
                    specialization_bonus = -2  # Prioridad para CX
                elif 'FTE' in str(user.profile.role or ''):
                    specialization_bonus = -1  # Prioridad para FTE

            user_workloads[user.id] = {
                'user': user,
                'workload': assigned_count + specialization_bonus,
                'role': getattr(user.profile, 'role', None) if hasattr(user, 'profile') else None
            }

        # Ordenar por carga de trabajo (menor primero)
        sorted_users = sorted(user_workloads.values(), key=lambda x: x['workload'])

        # Asignar al usuario con menor carga
        best_user = sorted_users[0]['user']
        self.assigned_to = best_user
        self.save(update_fields=['assigned_to'])

        # Registrar en historial
        InboxItemHistory.objects.create(
            inbox_item=self,
            user=best_user,  # O el usuario del sistema
            action='auto_assigned',
            new_values={
                'assigned_to': best_user.username,
                'assignment_method': 'automatic'
            }
        )

        return True

# Recordatorios mejorados
class Reminder(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    remind_at = models.DateTimeField()
    task = models.ForeignKey('Task', null=True, blank=True, on_delete=models.CASCADE)
    project = models.ForeignKey('Project', null=True, blank=True, on_delete=models.CASCADE)
    event = models.ForeignKey('Event', null=True, blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_sent = models.BooleanField(default=False)
    reminder_type = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('both', 'Email y Push')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.remind_at}"

    class Meta:
        ordering = ['remind_at']

# Sistema de autorización para items del inbox
class InboxItemAuthorization(models.Model):
    inbox_item = models.ForeignKey('InboxItem', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='granted_authorizations')
    granted_at = models.DateTimeField(auto_now_add=True)
    permission_level = models.CharField(max_length=20, choices=[
        ('view', 'Solo Vista'),
        ('classify', 'Vista y Clasificación'),
        ('edit', 'Vista, Clasificación y Edición'),
        ('admin', 'Administrador Completo')
    ], default='classify')

    def __str__(self):
        return f"{self.user.username} -> {self.inbox_item.title} ({self.permission_level})"

    class Meta:
        unique_together = ['inbox_item', 'user']

# Sistema de clasificación colaborativa para items del inbox
class InboxItemClassification(models.Model):
    inbox_item = models.ForeignKey('InboxItem', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gtd_category = models.CharField(max_length=20, choices=[
        ('accionable', 'Accionable'),
        ('no_accionable', 'No Accionable'),
        ('pendiente', 'Pendiente de Categorizar')
    ])
    action_type = models.CharField(max_length=20, choices=[
        ('hacer', 'Hacer'),
        ('delegar', 'Delegar'),
        ('posponer', 'Posponer'),
        ('proyecto', 'Convertir en Proyecto'),
        ('eliminar', 'Eliminar'),
        ('archivar', 'Archivar para Referencia'),
        ('incubar', 'Incubar (Algún Día)'),
        ('esperar', 'Esperar Más Información')
    ], blank=True, null=True)
    priority = models.CharField(max_length=10, choices=[
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
    ], default='media')
    confidence = models.IntegerField(
        default=50,
        help_text="Nivel de confianza en la clasificación (0-100%)"
    )
    notes = models.TextField(blank=True, help_text="Notas sobre la clasificación")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.inbox_item.title} -> {self.gtd_category}"

    class Meta:
        unique_together = ['inbox_item', 'user']
        ordering = ['-updated_at']

# Historial de cambios en items del inbox
class InboxItemHistory(models.Model):
    inbox_item = models.ForeignKey('InboxItem', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=[
        ('created', 'Creado'),
        ('viewed', 'Visto'),
        ('classified', 'Clasificado'),
        ('edited', 'Editado'),
        ('processed', 'Procesado'),
        ('shared', 'Compartido'),
        ('authorized', 'Autorización Cambiada')
    ])
    old_values = models.JSONField(blank=True, null=True, help_text="Valores anteriores")
    new_values = models.JSONField(blank=True, null=True, help_text="Nuevos valores")
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, help_text="Browser/client info")

    def __str__(self):
        return f"{self.user.username}: {self.action} - {self.inbox_item.title}"

    class Meta:
        ordering = ['-timestamp']

# Sistema de patrones de clasificación automática GTD
class GTDClassificationPattern(models.Model):
    name = models.CharField(max_length=100, help_text="Nombre descriptivo del patrón")
    description = models.TextField(help_text="Descripción de cuándo aplicar este patrón")

    # Condiciones del patrón
    keywords = models.JSONField(help_text="Lista de palabras clave que activan este patrón")
    keywords_operator = models.CharField(max_length=10, choices=[
        ('AND', 'Todas las palabras'),
        ('OR', 'Cualquier palabra'),
        ('NOT', 'Ninguna de las palabras')
    ], default='OR')

    # Resultados de clasificación
    gtd_category = models.CharField(max_length=20, choices=[
        ('accionable', 'Accionable'),
        ('no_accionable', 'No Accionable'),
        ('pendiente', 'Pendiente de Categorizar')
    ])

    action_type = models.CharField(max_length=20, choices=[
        ('hacer', 'Hacer'),
        ('delegar', 'Delegar'),
        ('posponer', 'Posponer'),
        ('proyecto', 'Convertir en Proyecto'),
        ('eliminar', 'Eliminar'),
        ('archivar', 'Archivar para Referencia'),
        ('incubar', 'Incubar (Algún Día)'),
        ('esperar', 'Esperar Más Información')
    ])

    priority = models.CharField(max_length=10, choices=[
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja')
    ], default='media')

    energy_required = models.CharField(max_length=20, choices=[
        ('baja', 'Baja Energía'),
        ('media', 'Media Energía'),
        ('alta', 'Alta Energía')
    ], default='media')

    # Configuración del patrón
    is_active = models.BooleanField(default=True)
    confidence_score = models.IntegerField(default=70, help_text="Nivel de confianza (0-100%)")
    usage_count = models.IntegerField(default=0, help_text="Veces que se ha usado este patrón")

    # Metadatos
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.gtd_category} -> {self.action_type})"

    class Meta:
        verbose_name = "Patrón de Clasificación GTD"
        verbose_name_plural = "Patrones de Clasificación GTD"

# Sistema de aprendizaje automático simple para GTD
class GTDLearningEntry(models.Model):
    inbox_item = models.ForeignKey('InboxItem', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Lo que el usuario decidió
    user_gtd_category = models.CharField(max_length=20)
    user_action_type = models.CharField(max_length=20)
    user_priority = models.CharField(max_length=10)

    # Lo que el sistema predijo
    predicted_gtd_category = models.CharField(max_length=20, blank=True)
    predicted_action_type = models.CharField(max_length=20, blank=True)
    predicted_priority = models.CharField(max_length=10, blank=True)

    # Confianza de la predicción
    prediction_confidence = models.IntegerField(default=0)

    # Metadatos
    was_correct = models.BooleanField(default=False, help_text="¿La predicción fue correcta?")
    learned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Aprendizaje: {self.inbox_item.title[:50]}..."

    class Meta:
        verbose_name = "Entrada de Aprendizaje GTD"
        verbose_name_plural = "Entradas de Aprendizaje GTD"

# Configuraciones de procesamiento GTD para el panel de gestión
class GTDProcessingSettings(models.Model):
    """Configuraciones para el procesamiento automático de interacciones GTD"""

    # Configuraciones de procesamiento automático
    auto_email_processing = models.BooleanField(default=True, help_text="Procesamiento automático de emails")
    auto_call_queue = models.BooleanField(default=True, help_text="Cola automática de llamadas")
    auto_chat_routing = models.BooleanField(default=True, help_text="Enrutamiento automático de chats")

    # Configuraciones de rendimiento
    processing_interval = models.IntegerField(default=60, help_text="Intervalo de procesamiento en segundos")
    max_concurrent_items = models.IntegerField(default=5, help_text="Máximo de items concurrentes")

    # Configuraciones específicas por tipo
    email_batch_size = models.IntegerField(default=10, help_text="Tamaño del lote de emails")
    call_queue_timeout = models.IntegerField(default=30, help_text="Timeout de cola de llamadas en segundos")
    chat_response_timeout = models.IntegerField(default=300, help_text="Timeout de respuesta de chat en segundos")

    # Configuraciones de agentes/bot
    enable_bot_cx = models.BooleanField(default=True, help_text="Habilitar Bot CX")
    enable_bot_atc = models.BooleanField(default=True, help_text="Habilitar Bot ATC")
    enable_human_agents = models.BooleanField(default=True, help_text="Habilitar agentes humanos")

    # Configuraciones de prioridad
    auto_priority_assignment = models.BooleanField(default=True, help_text="Asignación automática de prioridades")
    priority_threshold_high = models.IntegerField(default=80, help_text="Umbral para prioridad alta")
    priority_threshold_medium = models.IntegerField(default=50, help_text="Umbral para prioridad media")

    # Metadatos
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Configuración activa")

    def __str__(self):
        return f"GTD Processing Settings - {self.created_by.username}"

    class Meta:
        verbose_name = "Configuración de Procesamiento GTD"
        verbose_name_plural = "Configuraciones de Procesamiento GTD"
        ordering = ['-updated_at']

    @classmethod
    def get_active_settings(cls):
        """Obtiene la configuración activa actual"""
        return cls.objects.filter(is_active=True).first()

    def save(self, *args, **kwargs):
        # Asegurar que solo haya una configuración activa por usuario
        if self.is_active:
            cls = self.__class__
            cls.objects.filter(created_by=self.created_by, is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

