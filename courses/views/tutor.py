from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()
from django.http import JsonResponse
from django.db import models
from django.db.models import Q, Avg, Count, Prefetch, OuterRef, Subquery
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from courses.models import (
    Course, Module, Lesson, Enrollment,
    Progress, Review, CourseCategory, ContentBlock,
    CourseLevelChoices, EnrollmentStatusChoices, LessonTypeChoices
)
from courses.forms import CourseForm, ModuleForm, LessonForm, ReviewForm, CategoryForm

# ======================
# VISTAS PÚBLICAS
# ======================


@login_required
def manage_courses(request):
    """Gestión de cursos para tutores"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor')
        return redirect('cv:cv_detail')

    courses = Course.objects.filter(tutor=request.user).annotate(
        student_count=Count('enrollments', filter=Q(enrollments__status=EnrollmentStatusChoices.ACTIVE)),
        avg_rating=Avg('reviews__rating')
    )

    # Calcular estadísticas agregadas
    total_students = sum(course.student_count for course in courses)
    total_duration = sum(course.duration_hours for course in courses)
    avg_rating = 0
    if courses:
        ratings = [course.avg_rating for course in courses if course.avg_rating is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)

    context = {
        'courses': courses,
        'total_students': total_students,
        'total_duration': total_duration,
        'avg_rating': avg_rating
    }

    return render(request, 'courses/tutor/manage_courses.html', context)


@login_required
def create_course(request):
    """Crear un nuevo curso"""
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            course = form.save(commit=False)
            course.tutor = request.user
            course.save()
            messages.success(request, 'Curso creado exitosamente')
            return redirect('courses:manage_content', slug=course.slug)
    else:
        form = CourseForm(user=request.user)

    return render(request, 'courses/tutor/course_form.html', {
        'form': form,
        'title': 'Crear Nuevo Curso',
    })


@login_required
def create_course_wizard(request):
    """Asistente paso a paso para crear un curso"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor para crear cursos')
        return redirect('cv:cv_detail')

    step = int(request.GET.get('step', 1))

    if request.method == 'POST':
        if step == 1:
            # Paso 1: Información básica del curso
            form = CourseForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                course = form.save(commit=False)
                course.tutor = request.user
                course.save()
                return redirect(f'{request.path}?step=2&course_id={course.id}')
        elif step == 2:
            # Paso 2: Crear primer módulo
            course_id = request.POST.get('course_id')
            course = get_object_or_404(Course, id=course_id, tutor=request.user)

            form = ModuleForm(request.POST)
            if form.is_valid():
                module = form.save(commit=False)
                module.course = course
                module.save()
                messages.success(request, f'Curso "{course.title}" creado con el módulo "{module.title}"')
                return redirect('courses:manage_content', slug=course.slug)

    # Preparar formulario según el paso
    if step == 1:
        form = CourseForm(user=request.user)
        template = 'courses/course_wizard_step1.html'
        title = 'Crear Curso - Paso 1: Información Básica'
    elif step == 2:
        course_id = request.GET.get('course_id')
        if course_id:
            course = get_object_or_404(Course, id=course_id, tutor=request.user)
            form = ModuleForm()
            template = 'courses/course_wizard_step2.html'
            title = f'Crear Curso - Paso 2: Primer Módulo para "{course.title}"'
        else:
            return redirect('courses:create_course_wizard')
    else:
        return redirect('courses:create_course_wizard')

    context = {
        'form': form,
        'title': title,
        'step': step,
        'course': locals().get('course'),
    }

    return render(request, template, context)


@login_required
def edit_course(request, slug):
    """Editar un curso existente"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Curso actualizado exitosamente')
            return redirect('courses:manage_courses')
    else:
        form = CourseForm(instance=course, user=request.user)

    return render(request, 'courses/tutor/course_form.html', {
        'form': form,
        'title': 'Editar Curso',
        'course': course,
    })


@login_required
def delete_course(request, slug):
    """Eliminar un curso con validación de dependencias"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)

    # Validaciones de dependencias
    dependencies = {}

    # Contar estudiantes inscritos activos
    active_enrollments = course.enrollments.filter(status=EnrollmentStatusChoices.ACTIVE).count()
    if active_enrollments > 0:
        dependencies['active_enrollments'] = active_enrollments

    # Contar estudiantes que completaron el curso
    completed_enrollments = course.enrollments.filter(status=EnrollmentStatusChoices.COMPLETED).count()
    if completed_enrollments > 0:
        dependencies['completed_enrollments'] = completed_enrollments

    # Contar módulos
    modules_count = course.modules.count()
    if modules_count > 0:
        dependencies['modules'] = modules_count

    # Contar lecciones totales
    lessons_count = Lesson.objects.filter(module__course=course).count()
    if lessons_count > 0:
        dependencies['lessons'] = lessons_count

    # Contar reseñas
    reviews_count = course.reviews.count()
    if reviews_count > 0:
        dependencies['reviews'] = reviews_count

    if request.method == 'POST':
        # Si hay estudiantes activos, no permitir eliminación
        if active_enrollments > 0:
            messages.error(request, f'No se puede eliminar el curso porque tiene {active_enrollments} estudiante(s) activo(s) inscrito(s).')
            return redirect('courses:manage_courses')

        # Confirmar eliminación
        try:
            course_title = course.title
            course.delete()
            messages.success(request, f'Curso "{course_title}" eliminado exitosamente.')
            return redirect('courses:manage_courses')
        except Exception as e:
            messages.error(request, f'Error al eliminar el curso: {str(e)}')
            return redirect('courses:manage_courses')

    # Mostrar página de confirmación
    context = {
        'course': course,
        'dependencies': dependencies,
        'has_blocking_dependencies': active_enrollments > 0,
        'can_delete': active_enrollments == 0,
    }

    return render(request, 'courses/tutor/delete_course.html', context)


@login_required
def course_analytics(request, slug):
    """Analíticas de un curso para el tutor"""
    course = get_object_or_404(
        Course.objects.annotate(
            total_students=Count('enrollments', filter=Q(enrollments__status=EnrollmentStatusChoices.ACTIVE)),
            completed_students=Count('enrollments', filter=Q(enrollments__status=EnrollmentStatusChoices.COMPLETED))
        ),
        slug=slug, 
        tutor=request.user
    )
    
    # Progreso de estudiantes
    progress_data = []
    enrollments = course.enrollments.filter(
        status=EnrollmentStatusChoices.ACTIVE
    ).select_related('student').prefetch_related(
        Prefetch('progress', queryset=Progress.objects.filter(completed=True))
    )
    
    total_lessons = Lesson.objects.filter(module__course=course).count()
    
    for enrollment in enrollments:
        completed_lessons = enrollment.progress.count()
        progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        
        progress_data.append({
            'student': enrollment.student,
            'progress': progress_percentage,
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'enrollment_date': enrollment.enrolled_at,  # Usar enrolled_at en lugar de updated_at
            'status': enrollment.get_status_display()
        })
    
    # Ordenar por progreso (descendente)
    progress_data.sort(key=lambda x: x['progress'], reverse=True)
    
    return render(request, 'courses/tutor/course_analytics.html', {
        'course': course,
        'progress_data': progress_data,
        'total_lessons': total_lessons,
    })

# ======================
# VISTAS PARA GESTIÓN DE CONTENIDO
# ======================


@login_required
def manage_content(request, slug):
    """Vista para gestionar el contenido de un curso (módulos y lecciones)"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)

    # Obtener estadísticas del curso
    total_modules = course.modules.count()
    total_lessons = Lesson.objects.filter(module__course=course).count()

    # Obtener módulos con estadísticas calculadas
    modules = course.modules.prefetch_related('lessons').annotate(
        lessons_count=Count('lessons'),
        total_duration=Count('lessons') * 30  # Asumiendo 30 min por lección
    )

    context = {
        'course': course,
        'modules': modules,
        'total_modules': total_modules,
        'total_lessons': total_lessons,
        'categories': CourseCategory.objects.all(),
    }
    return render(request, 'courses/tutor/manage_content.html', context)


@login_required
def create_module(request, slug):
    """Crear un nuevo módulo para un curso"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)

    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            messages.success(request, 'Módulo creado exitosamente')
            return redirect('courses:manage_content', slug=course.slug)
    else:
        form = ModuleForm()

    return render(request, 'courses/tutor/module_form.html', {
        'form': form,
        'course': course,
        'title': 'Crear Nuevo Módulo',
        'module': None,
    })


@login_required
def edit_module(request, slug, module_id):
    """Editar un módulo existente"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)

    if request.method == 'POST':
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            messages.success(request, 'Módulo actualizado exitosamente')
            return redirect('courses:manage_content', slug=course.slug)
    else:
        form = ModuleForm(instance=module)

    return render(request, 'courses/tutor/module_form.html', {
        'form': form,
        'course': course,
        'title': 'Editar Módulo',
        'module': module,
    })


@login_required
def delete_module(request, slug, module_id):
    """Eliminar un módulo"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)

    if request.method == 'POST':
        module.delete()
        messages.success(request, 'Módulo eliminado exitosamente')
        return redirect('courses:manage_content', slug=course.slug)

    return render(request, 'courses/tutor/delete_module.html', {
        'course': course,
        'module': module,
    })


@login_required
def duplicate_module(request, slug, module_id):
    """Duplicar un módulo con todas sus lecciones"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)

    if request.method == 'POST':
        # Crear nuevo módulo
        new_module = Module.objects.create(
            course=course,
            title=f"{module.title} (Copia)",
            description=module.description,
            order=module.order + 1
        )

        # Duplicar todas las lecciones
        for lesson in module.lessons.all():
            Lesson.objects.create(
                module=new_module,
                title=lesson.title,
                lesson_type=lesson.lesson_type,
                content=lesson.content,
                video_url=lesson.video_url,
                duration_minutes=lesson.duration_minutes,
                order=lesson.order,
                is_free=lesson.is_free,
                quiz_questions=lesson.quiz_questions,
                assignment_instructions=lesson.assignment_instructions,
                assignment_file=lesson.assignment_file,
                assignment_due_date=lesson.assignment_due_date
            )

        messages.success(request, f'Módulo "{module.title}" duplicado exitosamente')
        return redirect('courses:manage_content', slug=course.slug)

    return render(request, 'courses/tutor/duplicate_module.html', {
        'course': course,
        'module': module,
    })


@require_POST
@login_required
def reorder_modules(request, slug):
    """Reordenar módulos vía AJAX"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)

    module_order = request.POST.getlist('module_order[]')
    if module_order:
        for index, module_id in enumerate(module_order):
            try:
                module = Module.objects.get(id=module_id, course=course)
                module.order = index + 1
                module.save()
            except Module.DoesNotExist:
                continue

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def module_statistics(request, slug, module_id):
    """Ver estadísticas detalladas de un módulo"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)

    # Estadísticas del módulo
    total_lessons = module.lessons.count()
    total_students = course.enrollments.filter(status='active').count()

    # Progreso por lección
    lesson_stats = []
    for lesson in module.lessons.all():
        completed_count = Progress.objects.filter(
            lesson=lesson,
            completed=True
        ).count()

        completion_rate = (completed_count / total_students * 100) if total_students > 0 else 0

        lesson_stats.append({
            'lesson': lesson,
            'completed_count': completed_count,
            'completion_rate': completion_rate,
        })

    context = {
        'course': course,
        'module': module,
        'total_lessons': total_lessons,
        'total_students': total_students,
        'lesson_stats': lesson_stats,
    }

    return render(request, 'courses/tutor/module_statistics.html', context)


@login_required
def modules_overview(request):
    """Vista general de todos los módulos del tutor"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor')
        return redirect('home')

    # Obtener todos los cursos del tutor
    courses = Course.objects.filter(tutor=request.user).prefetch_related('modules__lessons')

    # Estadísticas generales
    total_courses = courses.count()
    total_modules = courses.aggregate(total=models.Count('modules'))['total'] or 0
    total_lessons = courses.aggregate(total=models.Count('modules__lessons'))['total'] or 0

    # Módulos recientes
    recent_modules = Module.objects.filter(
        course__tutor=request.user
    ).select_related('course').order_by('-id')[:10]

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_modules': total_modules,
        'total_lessons': total_lessons,
        'recent_modules': recent_modules,
    }

    return render(request, 'courses/tutor/modules_overview.html', context)


@login_required
def module_progress(request, slug, module_id):
    """Ver progreso detallado de estudiantes en un módulo"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)

    # Obtener estudiantes inscritos
    enrollments = course.enrollments.filter(status='active').select_related('student')

    # Calcular progreso por estudiante
    student_progress = []
    for enrollment in enrollments:
        completed_lessons = Progress.objects.filter(
            enrollment=enrollment,
            lesson__module=module,
            completed=True
        ).count()

        total_module_lessons = module.lessons.count()
        progress_percentage = (completed_lessons / total_module_lessons * 100) if total_module_lessons > 0 else 0

        student_progress.append({
            'enrollment': enrollment,
            'completed_lessons': completed_lessons,
            'total_lessons': total_module_lessons,
            'progress_percentage': progress_percentage,
        })

    # Ordenar por progreso descendente
    student_progress.sort(key=lambda x: x['progress_percentage'], reverse=True)

    context = {
        'course': course,
        'module': module,
        'student_progress': student_progress,
        'total_students': len(student_progress),
    }

    return render(request, 'courses/tutor/module_progress.html', context)


@login_required
def bulk_module_actions(request, slug):
    """Acciones masivas para módulos de un curso"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        module_ids = request.POST.getlist('module_ids')

        if action == 'delete_selected':
            Module.objects.filter(id__in=module_ids, course=course).delete()
            messages.success(request, f'Se eliminaron {len(module_ids)} módulos')
        elif action == 'duplicate_selected':
            duplicated_count = 0
            for module_id in module_ids:
                try:
                    module = Module.objects.get(id=module_id, course=course)
                    # Duplicar módulo
                    new_module = Module.objects.create(
                        course=course,
                        title=f"{module.title} (Copia)",
                        description=module.description,
                        order=module.order + 1
                    )
                    # Duplicar lecciones
                    for lesson in module.lessons.all():
                        Lesson.objects.create(
                            module=new_module,
                            title=lesson.title,
                            lesson_type=lesson.lesson_type,
                            content=lesson.content,
                            video_url=lesson.video_url,
                            duration_minutes=lesson.duration_minutes,
                            order=lesson.order,
                            is_free=lesson.is_free,
                        )
                    duplicated_count += 1
                except Module.DoesNotExist:
                    continue
            messages.success(request, f'Se duplicaron {duplicated_count} módulos')

        return redirect('courses:manage_content', slug=course.slug)

    modules = course.modules.all()
    return render(request, 'courses/tutor/bulk_module_actions.html', {
        'course': course,
        'modules': modules,
    })


@login_required
def create_lesson(request, slug, module_id):
    """Crear una nueva lección para un módulo con soporte para contenido estructurado"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.save()
            messages.success(request, 'Lección creada exitosamente')

            # Si es una petición AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Lección creada exitosamente',
                    'lesson': {
                        'id': lesson.id,
                        'title': lesson.title,
                        'lesson_type': lesson.lesson_type,
                        'has_structured_content': bool(lesson.structured_content),
                        'structured_content_count': len(lesson.structured_content) if lesson.structured_content else 0
                    }
                })

            return redirect('courses:manage_content', slug=course.slug)
        else:
            # Si es AJAX y hay errores, devolver errores
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = LessonForm()

    # Obtener bloques de contenido disponibles (propios y públicos)
    available_content_blocks = ContentBlock.objects.filter(
        models.Q(author=request.user) | models.Q(is_public=True)
    ).select_related('author').order_by('title')

    # Información adicional para el template
    context = {
        'form': form,
        'course': course,
        'module': module,
        'title': 'Crear Nueva Lección',
        'lesson': None,
        'lesson_types': LessonTypeChoices.choices,
        'available_content_blocks': available_content_blocks,
    }

    return render(request, 'courses/public/standalone_lesson_form.html', context)


@login_required
def edit_lesson(request, slug, module_id, lesson_id):
    """Editar una lección existente con soporte para contenido estructurado"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)
    lesson = get_object_or_404(Lesson, id=lesson_id, module=module)

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            # El formulario maneja automáticamente el contenido estructurado
            form.save()
            messages.success(request, 'Lección actualizada exitosamente')

            # Si es una petición AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Lección actualizada exitosamente',
                    'lesson': {
                        'id': lesson.id,
                        'title': lesson.title,
                        'lesson_type': lesson.lesson_type,
                        'has_structured_content': bool(lesson.structured_content),
                        'structured_content_count': len(lesson.structured_content) if lesson.structured_content else 0
                    }
                })

            return redirect('courses:manage_content', slug=course.slug)
        else:
            # Si es AJAX y hay errores, devolver errores
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = LessonForm(instance=lesson)

    # Obtener bloques de contenido disponibles (propios y públicos)
    available_content_blocks = ContentBlock.objects.filter(
        models.Q(author=request.user) | models.Q(is_public=True)
    ).select_related('author').order_by('title')

    # Información adicional para el template
    context = {
        'form': form,
        'course': course,
        'module': module,
        'title': 'Editar Lección',
        'lesson': lesson,
        'has_structured_content': bool(lesson.structured_content),
        'structured_content_count': len(lesson.structured_content) if lesson.structured_content else 0,
        'lesson_types': LessonTypeChoices.choices,
        'available_content_blocks': available_content_blocks,
    }

    return render(request, 'courses/public/standalone_lesson_form.html', context)


@login_required
def delete_lesson(request, slug, module_id, lesson_id):
    """Eliminar una lección"""
    course = get_object_or_404(Course, slug=slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)
    lesson = get_object_or_404(Lesson, id=lesson_id, module=module)

    if request.method == 'POST':
        lesson.delete()
        messages.success(request, 'Lección eliminada exitosamente')
        return redirect('courses:manage_content', slug=course.slug)

    return render(request, 'courses/tutor/delete_lesson.html', {
        'course': course,
        'module': module,
        'lesson': lesson,
    })

# ======================
# VISTAS PARA GESTIÓN DE CATEGORÍAS
# ======================


@login_required
def manage_categories(request):
    """Vista para gestionar categorías de cursos con optimización de consultas"""
    # Solo administradores pueden gestionar categorías
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    # Optimizar consulta con prefetch_related para evitar N+1 queries
    categories = CourseCategory.objects.prefetch_related(
        'courses'  # Precargar cursos relacionados para contarlos eficientemente
    ).order_by('name')  # Ordenar alfabéticamente

    return render(request, 'courses/tutor/manage_categories.html', {
        'categories': categories,
    })


@login_required
def create_category(request):
    """Crear una nueva categoría"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, 'Categoría creada exitosamente')

            # Si es una petición AJAX, devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Categoría creada exitosamente',
                    'category': {
                        'id': category.id,
                        'name': category.name,
                        'description': category.description,
                        'slug': category.slug,
                        'courses_count': category.courses.count()
                    }
                })

            return redirect('courses:manage_categories')
        else:
            # Si es AJAX y hay errores, devolver errores
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = CategoryForm()

    return render(request, 'courses/tutor/category_form.html', {
        'form': form,
        'title': 'Crear Nueva Categoría',
    })


@login_required
def quick_create_category(request):
    """Crear categorías comunes de manera rápida"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    # Categorías predefinidas comunes
    common_categories = [
        {'name': 'Programación', 'description': 'Cursos de desarrollo de software y lenguajes de programación'},
        {'name': 'Diseño Gráfico', 'description': 'Herramientas y técnicas de diseño visual'},
        {'name': 'Marketing Digital', 'description': 'Estrategias de marketing en línea y redes sociales'},
        {'name': 'Negocios', 'description': 'Emprendimiento, gestión y administración de empresas'},
        {'name': 'Idiomas', 'description': 'Aprendizaje de idiomas extranjeros'},
        {'name': 'Matemáticas', 'description': 'Cursos de matemáticas y lógica'},
        {'name': 'Ciencias', 'description': 'Biología, química, física y otras ciencias'},
        {'name': 'Arte y Música', 'description': 'Cursos de arte, música y expresión creativa'},
        {'name': 'Salud y Bienestar', 'description': 'Nutrición, ejercicio y salud mental'},
        {'name': 'Tecnología', 'description': 'Innovación, IA, blockchain y nuevas tecnologías'},
    ]

    if request.method == 'POST':
        selected_categories = request.POST.getlist('categories')
        created_count = 0

        for category_name in selected_categories:
            # Verificar si ya existe
            if not CourseCategory.objects.filter(name=category_name).exists():
                # Encontrar la descripción correspondiente
                description = next(
                    (cat['description'] for cat in common_categories if cat['name'] == category_name),
                    f'Cursos relacionados con {category_name.lower()}'
                )

                CourseCategory.objects.create(
                    name=category_name,
                    description=description
                )
                created_count += 1

        if created_count > 0:
            messages.success(request, f'Se crearon {created_count} categorías exitosamente')
        else:
            messages.info(request, 'Todas las categorías seleccionadas ya existen')

        return redirect('courses:manage_categories')

    # Filtrar categorías que ya existen
    existing_categories = CourseCategory.objects.values_list('name', flat=True)
    available_categories = [
        cat for cat in common_categories
        if cat['name'] not in existing_categories
    ]

    return render(request, 'courses/tutor/quick_create_category.html', {
        'categories': available_categories,
        'title': 'Crear Categorías Rápidamente',
    })


@login_required
def edit_category(request, category_id):
    """Editar una categoría existente"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    category = get_object_or_404(CourseCategory, id=category_id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada exitosamente')
            return redirect('courses:manage_categories')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'courses/tutor/category_form.html', {
        'form': form,
        'title': 'Editar Categoría',
        'category': category,
    })


@login_required
def delete_category(request, category_id):
    """Eliminar una categoría"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    category = get_object_or_404(CourseCategory, id=category_id)

    if request.method == 'POST':
        # Verificar si la categoría tiene cursos asociados
        if category.courses.exists():
            messages.error(request, 'No se puede eliminar una categoría que tiene cursos asociados')
            return redirect('courses:manage_categories')

        category.delete()
        messages.success(request, 'Categoría eliminada exitosamente')
        return redirect('courses:manage_categories')

    return render(request, 'courses/tutor/delete_category.html', {
        'category': category,
    })

# ======================
# VISTAS DE ADMINISTRACIÓN
# ======================
