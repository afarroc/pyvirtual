# events/templates_views.py
# ============================================================================
# VISTAS DE PLANTILLAS DE PROYECTOS
# ============================================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone

from ..models import (
    ProjectTemplate, TemplateTask, 
    Project, Task, TaskStatus, Status, Event
)
from ..forms import ProjectTemplateForm, TemplateTaskFormSet, CreateNewProject
from ..management.task_manager import TaskManager

# ============================================================================
# VISTAS DE LISTADO Y FILTRADO
# ============================================================================

@login_required
def project_templates(request):
    """
    Vista para mostrar todas las plantillas de proyectos disponibles
    """
    # Obtener filtros
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('search', '')

    # Base queryset
    templates = ProjectTemplate.objects.all()

    # Aplicar filtros
    if category_filter:
        templates = templates.filter(category=category_filter)

    if search_query:
        templates = templates.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Obtener categorías únicas para el filtro
    categories = ProjectTemplate.objects.values_list('category', flat=True).distinct()

    # Separar plantillas públicas y privadas
    public_templates = templates.filter(is_public=True)
    user_templates = templates.filter(created_by=request.user)

    context = {
        'title': 'Plantillas de Proyectos',
        'public_templates': public_templates,
        'user_templates': user_templates,
        'categories': categories,
        'category_filter': category_filter,
        'search_query': search_query,
    }

    return render(request, 'events/project_templates.html', context)


# ============================================================================
# VISTAS CRUD DE PLANTILLAS
# ============================================================================

@login_required
def create_project_template(request):
    """
    Vista para crear una nueva plantilla de proyecto
    """
    if request.method == 'POST':
        template_form = ProjectTemplateForm(request.POST)
        task_formset = TemplateTaskFormSet(request.POST)

        if template_form.is_valid() and task_formset.is_valid():
            try:
                with transaction.atomic():
                    # Crear la plantilla
                    template = template_form.save(commit=False)
                    template.created_by = request.user
                    template.save()

                    # Crear las tareas de plantilla
                    tasks = task_formset.save(commit=False)
                    for i, task in enumerate(tasks):
                        task.template = template
                        task.order = i + 1
                        task.save()

                    # Guardar las relaciones many-to-many
                    task_formset.save_m2m()

                    messages.success(request, f'Plantilla "{template.name}" creada exitosamente')
                    return redirect('events:project_template_detail', template_id=template.id)

            except Exception as e:
                messages.error(request, f'Error al crear la plantilla: {e}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        template_form = ProjectTemplateForm()
        task_formset = TemplateTaskFormSet()

    context = {
        'title': 'Crear Plantilla de Proyecto',
        'template_form': template_form,
        'task_formset': task_formset,
    }

    return render(request, 'events/create_project_template.html', context)


@login_required
def project_template_detail(request, template_id):
    """
    Vista para mostrar los detalles de una plantilla de proyecto
    """
    try:
        template = ProjectTemplate.objects.get(id=template_id)

        # Verificar permisos
        if not template.is_public and template.created_by != request.user:
            messages.error(request, 'No tienes permisos para ver esta plantilla.')
            return redirect('events:project_templates')

        context = {
            'title': f'Plantilla: {template.name}',
            'template': template,
            'can_edit': template.created_by == request.user,
            'can_use': True,  # Cualquier usuario puede usar plantillas públicas
        }

        return render(request, 'events/project_template_detail.html', context)

    except ProjectTemplate.DoesNotExist:
        messages.error(request, 'Plantilla no encontrada.')
        return redirect('events:project_templates')


@login_required
def edit_project_template(request, template_id):
    """
    Vista para editar una plantilla de proyecto existente
    """
    try:
        template = ProjectTemplate.objects.get(id=template_id)

        # Verificar permisos
        if template.created_by != request.user:
            messages.error(request, 'No tienes permisos para editar esta plantilla.')
            return redirect('events:project_templates')

        if request.method == 'POST':
            template_form = ProjectTemplateForm(request.POST, instance=template)
            task_formset = TemplateTaskFormSet(request.POST, instance=template)

            if template_form.is_valid() and task_formset.is_valid():
                try:
                    with transaction.atomic():
                        template_form.save()

                        # Eliminar tareas existentes y crear nuevas
                        TemplateTask.objects.filter(template=template).delete()

                        tasks = task_formset.save(commit=False)
                        for i, task in enumerate(tasks):
                            task.template = template
                            task.order = i + 1
                            task.save()

                        task_formset.save_m2m()

                        messages.success(request, f'Plantilla "{template.name}" actualizada exitosamente')
                        return redirect('events:project_template_detail', template_id=template.id)

                except Exception as e:
                    messages.error(request, f'Error al actualizar la plantilla: {e}')
            else:
                messages.error(request, 'Por favor, corrige los errores en el formulario.')
        else:
            template_form = ProjectTemplateForm(instance=template)
            task_formset = TemplateTaskFormSet(instance=template)

        context = {
            'title': f'Editar Plantilla: {template.name}',
            'template': template,
            'template_form': template_form,
            'task_formset': task_formset,
        }

        return render(request, 'events/edit_project_template.html', context)

    except ProjectTemplate.DoesNotExist:
        messages.error(request, 'Plantilla no encontrada.')
        return redirect('events:project_templates')


@login_required
def delete_project_template(request, template_id):
    """
    Vista para eliminar una plantilla de proyecto
    """
    try:
        template = ProjectTemplate.objects.get(id=template_id)

        # Verificar permisos
        if template.created_by != request.user:
            messages.error(request, 'No tienes permisos para eliminar esta plantilla.')
            return redirect('events:project_templates')

        if request.method == 'POST':
            template_name = template.name
            template.delete()

            messages.success(request, f'Plantilla "{template_name}" eliminada exitosamente')
            return redirect('events:project_templates')

        context = {
            'title': 'Eliminar Plantilla',
            'template': template,
        }

        return render(request, 'events/delete_project_template.html', context)

    except ProjectTemplate.DoesNotExist:
        messages.error(request, 'Plantilla no encontrada.')
        return redirect('events:project_templates')


# ============================================================================
# VISTA PARA USAR PLANTILLAS
# ============================================================================

@login_required
def use_project_template(request, template_id):
    """
    Vista para usar una plantilla para crear un nuevo proyecto
    """
    try:
        template = ProjectTemplate.objects.get(id=template_id)

        # Verificar permisos
        if not template.is_public and template.created_by != request.user:
            messages.error(request, 'No tienes permisos para usar esta plantilla.')
            return redirect('events:project_templates')

        if request.method == 'POST':
            project_form = CreateNewProject(request.POST)

            if project_form.is_valid():
                try:
                    with transaction.atomic():
                        # Crear el proyecto
                        project = project_form.save(commit=False)
                        project.host = request.user
                        project.event = project_form.cleaned_data.get('event')

                        project.save()
                        project_form.save_m2m()

                        # Crear tareas basadas en la plantilla usando TaskManager
                        template_tasks = template.templatetask_set.all().order_by('order')

                        # Crear TaskManager para el usuario
                        task_manager = TaskManager(request.user)

                        for template_task in template_tasks:
                            # Usar TaskManager para crear tareas con procedimientos correctos
                            task_manager.create_task(
                                title=template_task.title,
                                description=template_task.description,
                                important=False,
                                project=project,
                                event=project.event,  # Asignar el evento del proyecto
                                task_status=None,  # Usará 'To Do' por defecto
                                assigned_to=request.user,
                                ticket_price=0.07
                            )

                        messages.success(request,
                            f'Proyecto "{project.title}" creado exitosamente usando la plantilla "{template.name}"')
                        return redirect('events:project_detail', project_id=project.id)

                except Exception as e:
                    messages.error(request, f'Error al crear el proyecto: {e}')
            else:
                messages.error(request, 'Por favor, corrige los errores en el formulario.')
        else:
            # Pre-llenar el formulario con datos de la plantilla
            initial_data = {
                'title': f"{template.name} - {timezone.now().strftime('%Y-%m-%d')}",
                'description': template.description,
            }
            project_form = CreateNewProject(initial=initial_data)

        context = {
            'title': f'Usar Plantilla: {template.name}',
            'template': template,
            'project_form': project_form,
            'task_count': template.templatetask_set.count(),
        }

        return render(request, 'events/use_project_template.html', context)

    except ProjectTemplate.DoesNotExist:
        messages.error(request, 'Plantilla no encontrada.')
        return redirect('events:project_templates')