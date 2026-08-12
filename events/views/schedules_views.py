# events/schedules_views.py
# ============================================================================
# VISTAS DE PROGRAMACIONES Y HORARIOS DE TAREAS
# ============================================================================

from datetime import datetime, timedelta
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()
from django.db import models
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from ..models import TaskProgram, TaskSchedule
from ..forms import TaskScheduleForm

# ============================================================================
# VISTAS DE HORARIOS Y CALENDARIOS
# ============================================================================

@login_required
def planning_task(request):
    """
    Vista mejorada para mostrar el horario de tareas programadas con seguridad y funcionalidad avanzada
    """
    # Verificar permisos - solo usuarios autenticados pueden ver su horario
    user = request.user

    # Obtener parámetros de filtro
    start_date_param = request.GET.get('start_date')
    days_param = request.GET.get('days', 7)

    try:
        days_param = int(days_param)
        if days_param < 1 or days_param > 31:
            days_param = 7  # Valor por defecto si está fuera de rango
    except (ValueError, TypeError):
        days_param = 7

    # Determinar fecha de inicio
    if start_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
        except ValueError:
            start_date = timezone.now().date()
    else:
        start_date = timezone.now().date()

    end_date = start_date + timedelta(days=days_param)

    # Obtener tareas programadas del usuario dentro del rango de fechas
    task_programs = TaskProgram.objects.filter(
        host=user,
        start_time__date__range=(start_date, end_date)
    ).select_related('task', 'task__task_status', 'task__project').order_by('start_time')

    # Crear una matriz para el horario
    days = [(start_date + timedelta(days=i)) for i in range(days_param)]
    schedule = {day: {hour: [] for hour in range(24)} for day in days}

    # Estadísticas del horario
    total_programs = task_programs.count()
    total_hours = 0
    programs_by_day = {day: 0 for day in days}

    # Llenar la matriz con las tareas programadas
    for program in task_programs:
        day = program.start_time.date()
        hour = program.start_time.hour

        if day in schedule and hour in schedule[day]:
            schedule[day][hour].append(program)
            programs_by_day[day] += 1

            # Calcular duración si hay end_time
            if program.end_time:
                duration = (program.end_time - program.start_time).total_seconds() / 3600
                total_hours += duration

    # Determinar horas activas (con al menos una tarea programada)
    active_hours = set()
    for day_schedule in schedule.values():
        for hour, programs in day_schedule.items():
            if programs:
                active_hours.add(hour)

    hours = sorted(list(active_hours)) if active_hours else range(9, 18)  # 9 AM - 6 PM por defecto

    # Preparar navegación de fechas
    prev_start = start_date - timedelta(days=days_param)
    next_start = start_date + timedelta(days=days_param)

    context = {
        'title': f'Horario de Tareas - {start_date.strftime("%d/%m/%Y")} a {(end_date - timedelta(days=1)).strftime("%d/%m/%Y")}',
        'schedule': schedule,
        'days': days,
        'hours': hours,
        'start_date': start_date,
        'end_date': end_date,
        'days_param': days_param,
        'prev_start': prev_start,
        'next_start': next_start,

        # Estadísticas
        'total_programs': total_programs,
        'total_hours': round(total_hours, 1),
        'programs_by_day': programs_by_day,

        # URLs de navegación
        'urls': {
            'today': f'/events/planning_task/?start_date={timezone.now().date()}&days={days_param}',
            'this_week': f'/events/planning_task/?start_date={timezone.now().date() - timedelta(days=timezone.now().weekday())}&days=7',
            'next_week': f'/events/planning_task/?start_date={start_date + timedelta(days=7)}&days={days_param}',
        }
    }

    return render(request, 'program/program.html', context)


@login_required
def task_programs_calendar(request):
    """
    Vista de calendario semanal para programas de tareas creados
    """
    # Obtener parámetros de filtro
    start_date_param = request.GET.get('start_date')
    weeks_param = request.GET.get('weeks', 1)

    try:
        weeks_param = int(weeks_param)
        if weeks_param < 1 or weeks_param > 4:
            weeks_param = 1  # Valor por defecto si está fuera de rango
    except (ValueError, TypeError):
        weeks_param = 1

    # Determinar fecha de inicio (lunes de la semana actual)
    if start_date_param:
        try:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
        except ValueError:
            start_date = timezone.now().date()
    else:
        start_date = timezone.now().date()

    # Ajustar al lunes de la semana
    start_date = start_date - timedelta(days=start_date.weekday())

    end_date = start_date + timedelta(days=weeks_param * 7 - 1)

    # Obtener programas de tareas del usuario en el rango de fechas
    task_programs = TaskProgram.objects.filter(
        host=request.user,
        start_time__date__range=(start_date, end_date)
    ).select_related('task', 'task__task_status').order_by('start_time')

    # Crear estructura de calendario
    calendar_data = {}
    current_date = start_date

    while current_date <= end_date:
        calendar_data[current_date] = {
            'date': current_date,
            'weekday': current_date.strftime('%A'),
            'weekday_short': current_date.strftime('%a'),
            'programs': []
        }
        current_date += timedelta(days=1)

    # Llenar el calendario con programas
    for program in task_programs:
        program_date = program.start_time.date()
        if program_date in calendar_data:
            calendar_data[program_date]['programs'].append({
                'program': program,
                'start_time': program.start_time,
                'end_time': program.end_time,
                'duration': program.end_time - program.start_time if program.end_time else None,
                'task_title': program.task.title,
                'task_status': program.task.task_status.status_name,
                'task_status_color': program.task.task_status.color
            })

    # Estadísticas
    total_programs = task_programs.count()
    total_hours = sum(
        (p.end_time - p.start_time).total_seconds() / 3600
        for p in task_programs if p.end_time
    )

    # Navegación
    prev_week = start_date - timedelta(days=7)
    next_week = start_date + timedelta(days=7 * weeks_param)

    context = {
        'title': f'Calendario de Programas - Semana del {start_date.strftime("%d/%m/%Y")}',
        'calendar_data': calendar_data,
        'start_date': start_date,
        'end_date': end_date,
        'weeks_param': weeks_param,
        'prev_week': prev_week,
        'next_week': next_week,
        'total_programs': total_programs,
        'total_hours': round(total_hours, 1),
        'urls': {
            'today': f'/events/task_programs_calendar/?start_date={timezone.now().date() - timedelta(days=timezone.now().weekday())}&weeks={weeks_param}',
            'this_week': f'/events/task_programs_calendar/?start_date={timezone.now().date() - timedelta(days=timezone.now().weekday())}&weeks={weeks_param}',
            'next_week': f'/events/task_programs_calendar/?start_date={next_week}&weeks={weeks_param}',
        }
    }

    return render(request, 'events/task_programs_calendar.html', context)


# ============================================================================
# TASK SCHEDULING SYSTEM (Programaciones recurrentes de tareas)
# ============================================================================

@login_required
def task_schedules(request):
    """
    Vista para listar todas las programaciones recurrentes del usuario
    """
    # Obtener programaciones del usuario
    user_schedules = TaskSchedule.objects.filter(
        host=request.user
    ).select_related('task').order_by('-created_at')

    # Estadísticas
    total_schedules = user_schedules.count()
    active_schedules = user_schedules.filter(is_active=True).count()
    inactive_schedules = total_schedules - active_schedules

    # Próximas ocurrencias para cada programación
    schedules_with_next = []
    for schedule in user_schedules:
        next_occurrence = schedule.get_next_occurrence()
        schedules_with_next.append({
            'schedule': schedule,
            'next_occurrence': next_occurrence
        })

    context = {
        'title': 'Programaciones Recurrentes',
        'schedules': schedules_with_next,
        'total_schedules': total_schedules,
        'active_schedules': active_schedules,
        'inactive_schedules': inactive_schedules,
    }

    return render(request, 'events/task_schedules.html', context)


@login_required
def create_task_schedule(request):
    """
    Vista para crear una nueva programación recurrente
    """
    if request.method == 'POST':
        form = TaskScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'Programación creada exitosamente para "{schedule.task.title}"')
            return redirect('events:task_schedule_detail', schedule_id=schedule.id)
    else:
        form = TaskScheduleForm(user=request.user)

    context = {
        'title': 'Crear Programación Recurrente',
        'form': form,
    }

    return render(request, 'events/create_task_schedule.html', context)


@login_required
def task_schedule_detail(request, schedule_id):
    """
    Vista detallada de una programación recurrente
    """
    try:
        schedule = TaskSchedule.objects.select_related('task').get(
            id=schedule_id,
            host=request.user
        )
    except TaskSchedule.DoesNotExist:
        messages.error(request, 'Programación no encontrada.')
        return redirect('events:task_schedules')

    # Generar próximas ocurrencias
    next_occurrences = schedule.generate_occurrences(limit=10)

    # Obtener programas creados por esta programación
    created_programs = TaskProgram.objects.filter(
        task=schedule.task,
        host=request.user,
        start_time__gte=schedule.start_date
    ).order_by('start_time')[:10]

    context = {
        'title': f'Programación: {schedule.task.title}',
        'schedule': schedule,
        'next_occurrences': next_occurrences,
        'created_programs': created_programs,
    }

    return render(request, 'events/task_schedule_detail.html', context)


@login_required
def edit_task_schedule(request, schedule_id):
    """
    Vista mejorada para editar una programación recurrente con funcionalidades avanzadas
    """
    try:
        schedule = TaskSchedule.objects.select_related('task').get(id=schedule_id, host=request.user)
    except TaskSchedule.DoesNotExist:
        messages.error(request, 'Programación no encontrada.')
        return redirect('events:task_schedules')

    if request.method == 'POST':
        form = TaskScheduleForm(request.POST, instance=schedule, user=request.user)
        if form.is_valid():
            # Store original values for logging
            field_mapping = {'duration_hours': 'duration'}
            original_values = {}
            for field in form.changed_data:
                model_field = field_mapping.get(field, field)
                original_values[model_field] = getattr(schedule, model_field)

            # Guardar cambios
            schedule = form.save()

            # Log de cambios para auditoría
            _log_schedule_changes(schedule, form.changed_data, original_values)

            messages.success(
                request,
                f'Programación "{schedule.task.title}" actualizada exitosamente. '
                f'Se generarán {len(schedule.generate_occurrences(limit=5))} próximas ocurrencias.'
            )
            return redirect('events:task_schedule_detail', schedule_id=schedule.id)
        else:
            # Mejor manejo de errores
            for field, errors in form.errors.items():
                if field != '__all__':
                    messages.error(request, f'{form.fields[field].label}: {errors[0]}')
    else:
        form = TaskScheduleForm(instance=schedule, user=request.user)

    # Próximas ocurrencias para preview
    next_occurrences = schedule.generate_occurrences(limit=10)

    # Estadísticas de la programación
    created_programs_count = TaskProgram.objects.filter(
        task=schedule.task,
        host=request.user,
        start_time__gte=schedule.start_date
    ).count()

    # Programas creados recientemente
    recent_programs = TaskProgram.objects.filter(
        task=schedule.task,
        host=request.user,
        start_time__gte=schedule.start_date
    ).select_related('task__task_status').order_by('-start_time')[:5]

    context = {
        'title': f'Editar Programación: {schedule.task.title}',
        'form': form,
        'schedule': schedule,
        'next_occurrences': next_occurrences,
        'created_programs_count': created_programs_count,
        'recent_programs': recent_programs,
        'can_preview': True,
        'preview_url': reverse('task_schedule_preview', kwargs={'schedule_id': schedule.id}),
    }

    return render(request, 'events/edit_task_schedule_enhanced.html', context)


class TaskScheduleEditView(LoginRequiredMixin, UpdateView):
    """
    Vista mejorada basada en clases para editar programaciones recurrentes de tareas.
    Incluye funcionalidades avanzadas como preview, validación mejorada y mejor UX.
    """
    model = TaskSchedule
    form_class = None  # Se define dinámicamente
    template_name = 'events/edit_task_schedule_enhanced.html'
    context_object_name = 'schedule'

    def get_queryset(self):
        """Filtrar solo las programaciones del usuario actual"""
        return TaskSchedule.objects.filter(host=self.request.user)

    def get_form_class(self):
        """Obtener la clase del formulario dinámicamente"""
        return TaskScheduleForm

    def get_form_kwargs(self):
        """Pasar el usuario al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Añadir datos adicionales al contexto"""
        context = super().get_context_data(**kwargs)
        schedule = self.object

        # Próximas ocurrencias para preview
        next_occurrences = schedule.generate_occurrences(limit=10)

        # Estadísticas de la programación
        created_programs_count = TaskProgram.objects.filter(
            task=schedule.task,
            host=self.request.user,
            start_time__gte=schedule.start_date
        ).count()

        # Programaciones creadas recientemente
        recent_programs = TaskProgram.objects.filter(
            task=schedule.task,
            host=self.request.user,
            start_time__gte=schedule.start_date
        ).order_by('-start_time')[:5]

        context.update({
            'title': f'Editar Programación: {schedule.task.title}',
            'next_occurrences': next_occurrences,
            'created_programs_count': created_programs_count,
            'recent_programs': recent_programs,
            'can_preview': True,
            'preview_url': reverse_lazy('task_schedule_preview', kwargs={'schedule_id': schedule.id}),
        })

        return context

    def form_valid(self, form):
        """Procesar formulario válido con funcionalidades adicionales"""
        # Store original values for logging
        field_mapping = {'duration_hours': 'duration'}
        original_values = {}
        for field in form.changed_data:
            model_field = field_mapping.get(field, field)
            original_values[model_field] = getattr(form.instance, model_field)

        # Guardar cambios
        schedule = form.save()

        # Generar preview si se solicita
        if self.request.POST.get('action') == 'preview':
            # Redirigir a preview en lugar de guardar
            return redirect('events:task_schedule_preview', schedule_id=schedule.id)

        # Log de cambios para auditoría
        self._log_schedule_changes(schedule, form.changed_data, original_values)

        messages.success(
            self.request,
            f'Programación "{schedule.task.title}" actualizada exitosamente. '
            f'Se generarán {len(schedule.generate_occurrences(limit=5))} próximas ocurrencias.'
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        """Manejar formulario inválido con mejor feedback"""
        # Añadir contexto adicional para errores
        for field, errors in form.errors.items():
            if field != '__all__':
                messages.error(self.request, f'{form.fields[field].label}: {errors[0]}')

        return super().form_invalid(form)

    def get_success_url(self):
        """URL de éxito después de guardar"""
        return reverse_lazy('task_schedule_detail', kwargs={'schedule_id': self.object.id})

    def _log_schedule_changes(self, schedule, changed_fields, original_values=None):
        """Registrar cambios para auditoría"""
        if changed_fields:
            changes = []
            # Mapping for form fields that don't directly match model fields
            field_mapping = {
                'duration_hours': 'duration'
            }

            if original_values is None:
                original_values = {}

            for field in changed_fields:
                # Map form field to model field if necessary
                model_field = field_mapping.get(field, field)

                try:
                    old_value = original_values.get(model_field, 'N/A')
                    new_value = getattr(schedule, model_field)
                    changes.append(f"{field}: {old_value} → {new_value}")
                except AttributeError as e:
                    # Skip fields that don't exist on the model
                    print(f"Warning: Could not log change for field {field} (mapped to {model_field}): {e}")
                    continue

            # Aquí se podría guardar en un log de auditoría
            print(f"[AUDIT] Schedule {schedule.id} changed: {', '.join(changes)}")


@login_required
def task_schedule_preview(request, schedule_id):
    """
    Vista para previsualizar cambios en una programación antes de guardarlos
    """
    try:
        schedule = TaskSchedule.objects.get(id=schedule_id, host=request.user)
    except TaskSchedule.DoesNotExist:
        messages.error(request, 'Programación no encontrada.')
        return redirect('events:task_schedules')

    # Simular cambios basados en POST data
    if request.method == 'POST':
        form = TaskScheduleForm(request.POST, instance=schedule, user=request.user)

        if form.is_valid():
            # Crear preview sin guardar
            preview_schedule = TaskSchedule(
                task=form.cleaned_data['task'],
                recurrence_type=form.cleaned_data['recurrence_type'],
                monday=form.cleaned_data.get('monday', False),
                tuesday=form.cleaned_data.get('tuesday', False),
                wednesday=form.cleaned_data.get('wednesday', False),
                thursday=form.cleaned_data.get('thursday', False),
                friday=form.cleaned_data.get('friday', False),
                saturday=form.cleaned_data.get('saturday', False),
                sunday=form.cleaned_data.get('sunday', False),
                start_time=form.cleaned_data['start_time'],
                start_date=form.cleaned_data['start_date'],
                end_date=form.cleaned_data.get('end_date'),
                is_active=form.cleaned_data.get('is_active', True),
                host=request.user
            )

            # Calcular duración
            duration_hours = form.cleaned_data.get('duration_hours', 1.0)
            preview_schedule.duration = timedelta(hours=float(duration_hours))

            # Generar preview de ocurrencias
            preview_occurrences = preview_schedule.generate_occurrences(limit=15)

            context = {
                'title': f'Preview: {preview_schedule.task.title}',
                'original_schedule': schedule,
                'preview_schedule': preview_schedule,
                'preview_occurrences': preview_occurrences,
                'form_data': request.POST,
                'changes_detected': True,
            }

            return render(request, 'events/task_schedule_preview.html', context)
        else:
            messages.error(request, 'Datos inválidos para preview.')
            return redirect('events:edit_task_schedule', schedule_id=schedule_id)

    # GET request - mostrar preview actual
    current_occurrences = schedule.generate_occurrences(limit=10)

    context = {
        'title': f'Preview Actual: {schedule.task.title}',
        'original_schedule': schedule,
        'preview_schedule': schedule,
        'preview_occurrences': current_occurrences,
        'changes_detected': False,
    }

    return render(request, 'events/task_schedule_preview.html', context)


@login_required
def delete_task_schedule(request, schedule_id):
    """
    Vista para eliminar una programación recurrente
    """
    try:
        schedule = TaskSchedule.objects.get(id=schedule_id, host=request.user)
    except TaskSchedule.DoesNotExist:
        messages.error(request, 'Programación no encontrada.')
        return redirect('events:task_schedules')

    if request.method == 'POST':
        task_title = schedule.task.title
        schedule.delete()
        messages.success(request, f'Programación eliminada: "{task_title}"')
        return redirect('events:task_schedules')

    context = {
        'title': 'Eliminar Programación',
        'schedule': schedule,
    }

    return render(request, 'events/delete_task_schedule.html', context)


@login_required
def generate_schedule_occurrences(request, schedule_id):
    """
    Vista para generar ocurrencias manualmente para una programación
    """
    try:
        schedule = TaskSchedule.objects.get(id=schedule_id, host=request.user)
    except TaskSchedule.DoesNotExist:
        messages.error(request, 'Programación no encontrada.')
        return redirect('events:task_schedules')

    if request.method == 'POST':
        # Generar ocurrencias
        created_programs = schedule.create_task_programs()

        if created_programs:
            messages.success(request, f'Se generaron {len(created_programs)} nuevas programaciones')
        else:
            messages.info(request, 'No se generaron nuevas programaciones (ya existen o no hay fechas futuras)')

        return redirect('events:task_schedule_detail', schedule_id=schedule.id)

    # GET request - mostrar confirmación
    next_occurrences = schedule.generate_occurrences(limit=5)

    context = {
        'title': f'Generar Ocurrencias: {schedule.task.title}',
        'schedule': schedule,
        'next_occurrences': next_occurrences,
    }

    return render(request, 'events/generate_schedule_occurrences.html', context)


@login_required
def user_schedules_panel(request):
    """
    Panel para administrar los horarios y programaciones de todos los usuarios
    """
    # Verificar permisos de administrador
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para acceder al panel de administración de horarios.')
        return redirect('events:task_schedules')

    # Filtros
    user_filter = request.GET.get('user', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')

    # Obtener todos los usuarios que tienen programaciones o programas
    users_with_schedules = User.objects.filter(
        models.Q(taskschedule__isnull=False) |
        models.Q(hosted_programs__isnull=False)
    ).distinct().order_by('username')

    # Aplicar filtros
    if user_filter != 'all':
        users_with_schedules = users_with_schedules.filter(id=user_filter)

    if search_query:
        users_with_schedules = users_with_schedules.filter(
            models.Q(username__icontains=search_query) |
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(email__icontains=search_query)
        )

    # Preparar datos por usuario
    users_data = []
    for user in users_with_schedules:
        # Programaciones recurrentes del usuario
        user_schedules = TaskSchedule.objects.filter(host=user).select_related('task')

        # Aplicar filtro de estado
        if status_filter == 'active':
            user_schedules = user_schedules.filter(is_active=True)
        elif status_filter == 'inactive':
            user_schedules = user_schedules.filter(is_active=False)

        # Programas específicos del usuario
        user_programs = TaskProgram.objects.filter(host=user).select_related('task').order_by('-start_time')[:10]

        # Próximas ocurrencias para las programaciones
        schedules_with_next = []
        for schedule in user_schedules:
            next_occurrence = schedule.get_next_occurrence()
            schedules_with_next.append({
                'schedule': schedule,
                'next_occurrence': next_occurrence
            })

        # Estadísticas del usuario
        user_stats = {
            'total_schedules': user_schedules.count(),
            'active_schedules': user_schedules.filter(is_active=True).count(),
            'inactive_schedules': user_schedules.filter(is_active=False).count(),
            'total_programs': TaskProgram.objects.filter(host=user).count(),
            'weekly_schedules': user_schedules.filter(recurrence_type='weekly').count(),
            'daily_schedules': user_schedules.filter(recurrence_type='daily').count(),
            'custom_schedules': user_schedules.filter(recurrence_type='custom').count(),
        }

        users_data.append({
            'user': user,
            'schedules': schedules_with_next,
            'programs': user_programs,
            'stats': user_stats,
        })

    # Estadísticas generales
    total_stats = {
        'total_users': users_with_schedules.count(),
        'total_schedules': TaskSchedule.objects.count(),
        'active_schedules': TaskSchedule.objects.filter(is_active=True).count(),
        'total_programs': TaskProgram.objects.count(),
        'today_schedules': TaskSchedule.objects.filter(created_at__date=timezone.now().date()).count(),
        'this_week_schedules': TaskSchedule.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
    }

    context = {
        'title': 'Panel de Horarios y Programaciones',
        'users_data': users_data,
        'total_stats': total_stats,
        'user_filter': user_filter,
        'status_filter': status_filter,
        'search_query': search_query,
    }

    return render(request, 'events/user_schedules_panel.html', context)


@login_required
def schedule_admin_dashboard(request):
    """
    Panel de administración de programaciones recurrentes - Vista principal para gestionar schedules de todos los usuarios
    """
    # Verificar permisos de administrador
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para acceder al panel de administración de programaciones.')
        return redirect('events:task_schedules')

    # Filtros
    status_filter = request.GET.get('status', 'all')
    user_filter = request.GET.get('user', 'all')
    recurrence_filter = request.GET.get('recurrence', 'all')
    search_query = request.GET.get('search', '')

    # Base queryset
    schedules = TaskSchedule.objects.select_related(
        'task', 'host'
    ).prefetch_related(
        'task__task_status'
    ).order_by('-created_at')

    # Aplicar filtros
    if status_filter == 'active':
        schedules = schedules.filter(is_active=True)
    elif status_filter == 'inactive':
        schedules = schedules.filter(is_active=False)

    if user_filter != 'all':
        schedules = schedules.filter(host=user_filter)

    if recurrence_filter != 'all':
        schedules = schedules.filter(recurrence_type=recurrence_filter)

    if search_query:
        schedules = schedules.filter(
            models.Q(task__title__icontains=search_query) |
            models.Q(host__username__icontains=search_query) |
            models.Q(task__description__icontains=search_query)
        )

    # Estadísticas generales
    stats = {
        'total': TaskSchedule.objects.count(),
        'active': TaskSchedule.objects.filter(is_active=True).count(),
        'inactive': TaskSchedule.objects.filter(is_active=False).count(),
        'weekly': TaskSchedule.objects.filter(recurrence_type='weekly').count(),
        'daily': TaskSchedule.objects.filter(recurrence_type='daily').count(),
        'custom': TaskSchedule.objects.filter(recurrence_type='custom').count(),
        'today': TaskSchedule.objects.filter(created_at__date=timezone.now().date()).count(),
        'this_week': TaskSchedule.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
    }

    # Programaciones recientes
    recent_schedules = schedules[:10]

    # Próximas ocurrencias para las programaciones recientes
    schedules_with_next = []
    for schedule in recent_schedules:
        next_occurrence = schedule.get_next_occurrence()
        schedules_with_next.append({
            'schedule': schedule,
            'next_occurrence': next_occurrence
        })

    # Usuarios activos con programaciones
    active_users = User.objects.filter(
        models.Q(taskschedule__isnull=False)
    ).distinct().annotate(
        schedule_count=models.Count('taskschedule')
    ).order_by('-schedule_count')[:20]

    context = {
        'title': 'Administración de Programaciones Recurrentes',
        'schedules': schedules_with_next,
        'all_schedules': schedules,  # Para paginación si es necesario
        'stats': stats,
        'active_users': active_users,
        'status_filter': status_filter,
        'user_filter': user_filter,
        'recurrence_filter': recurrence_filter,
        'search_query': search_query,
    }

    return render(request, 'events/schedule_admin_dashboard.html', context)


@login_required
def schedule_admin_bulk_action(request):
    """
    Vista para acciones masivas en programaciones recurrentes
    """
    # Verificar permisos de administrador
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para realizar acciones masivas.')
        return redirect('events:schedule_admin_dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_schedules = request.POST.getlist('selected_schedules')

        if not selected_schedules:
            messages.error(request, 'No se seleccionaron programaciones.')
            return redirect('events:schedule_admin_dashboard')

        schedules = TaskSchedule.objects.filter(id__in=selected_schedules)

        if action == 'activate':
            count = schedules.update(is_active=True)
            messages.success(request, f'Se activaron {count} programaciones exitosamente.')

        elif action == 'deactivate':
            count = schedules.update(is_active=False)
            messages.success(request, f'Se desactivaron {count} programaciones exitosamente.')

        elif action == 'delete':
            if not request.user.is_superuser:
                messages.error(request, 'No tienes permiso para eliminar programaciones.')
                return redirect('events:schedule_admin_dashboard')

            count = schedules.count()
            schedules.delete()
            messages.success(request, f'Se eliminaron {count} programaciones exitosamente.')

        elif action == 'generate_occurrences':
            total_created = 0
            for schedule in schedules:
                created_programs = schedule.create_task_programs()
                total_created += len(created_programs)
            messages.success(request, f'Se generaron {total_created} nuevas programaciones.')

        else:
            messages.error(request, 'Acción no válida.')

    return redirect('events:schedule_admin_dashboard')