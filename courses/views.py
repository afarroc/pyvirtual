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
from .models import (
    Course, Module, Lesson, Enrollment,
    Progress, Review, CourseCategory, ContentBlock,
    CourseLevelChoices, EnrollmentStatusChoices, LessonTypeChoices
)
from .forms import CourseForm, ModuleForm, LessonForm, ReviewForm, CategoryForm

# ======================
# VISTAS PÚBLICAS
# ======================

def index(request):
    """Página principal de la app de cursos - Muestra contenido general, noticias, nuevos cursos, etc."""
    # Estadísticas generales
    total_courses = Course.objects.filter(is_published=True).count()
    total_students = sum(course.students_count for course in Course.objects.filter(is_published=True))
    total_categories = CourseCategory.objects.count()

    # Cursos destacados (featured)
    featured_courses = Course.objects.filter(
        is_published=True,
        is_featured=True
    ).select_related('category', 'tutor').order_by('-created_at')[:6]

    # Cursos más recientes
    recent_courses = Course.objects.filter(
        is_published=True
    ).select_related('category', 'tutor').order_by('-created_at')[:8]

    # Categorías populares
    popular_categories = CourseCategory.objects.annotate(
        course_count=Count('courses', filter=Q(courses__is_published=True))
    ).filter(course_count__gt=0).order_by('-course_count')[:6]

    # Estadísticas de usuarios (si hay usuarios autenticados)
    if request.user.is_authenticated:
        user_enrollments = Enrollment.objects.filter(
            student=request.user,
            status=EnrollmentStatusChoices.ACTIVE
        ).count()
        user_completed = Enrollment.objects.filter(
            student=request.user,
            status=EnrollmentStatusChoices.COMPLETED
        ).count()
    else:
        user_enrollments = 0
        user_completed = 0

    context = {
        'total_courses': total_courses,
        'total_students': total_students,
        'total_categories': total_categories,
        'featured_courses': featured_courses,
        'recent_courses': recent_courses,
        'popular_categories': popular_categories,
        'user_enrollments': user_enrollments,
        'user_completed': user_completed,
        'categories': CourseCategory.objects.all(),
    }
    return render(request, 'courses/home.html', context)


def course_list(request, category_slug=None):
    """Lista todos los cursos disponibles con optimización de consultas"""
    courses = Course.objects.filter(is_published=True).select_related(
        'category', 'tutor'
    ).prefetch_related(
        Prefetch('reviews', queryset=Review.objects.select_related('student'))
    )

    # Filtros
    category = request.GET.get('category') or category_slug
    level = request.GET.get('level')
    search = request.GET.get('search')

    if category:
        courses = courses.filter(category__slug=category)
    if level:
        courses = courses.filter(level=level)
    if search:
        courses = courses.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(short_description__icontains=search)
        )

    # Calcular estadísticas
    total_students = sum(course.students_count for course in courses)
    average_rating = 0
    if courses:
        ratings = [course.average_rating for course in courses if course.average_rating > 0]
        if ratings:
            average_rating = sum(ratings) / len(ratings)

    context = {
        'courses': courses,
        'categories': CourseCategory.objects.all(),
        'levels': CourseLevelChoices.choices,
        'selected_category': category,
        'selected_level': level,
        'search_query': search or '',
        'total_students': total_students,
        'average_rating': average_rating
    }
    return render(request, 'courses/course_list.html', context)


def course_detail(request, slug):
    """Detalle de un curso específico con optimización de consultas"""
    course = get_object_or_404(
        Course.objects.select_related('category', 'tutor').prefetch_related(
            Prefetch('modules__lessons', queryset=Lesson.objects.order_by('order'))
        ),
        slug=slug, 
        is_published=True
    )
    
    # Obtener reseñas por separado para evitar el problema del slice
    reviews = Review.objects.filter(
        course=course
    ).select_related('student').order_by('-created_at')[:5]
    
    # Verificar si el usuario está inscrito
    is_enrolled = False
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(
            student=request.user, 
            course=course, 
            status=EnrollmentStatusChoices.ACTIVE
        ).exists()
    
    context = {
        'course': course,
        'is_enrolled': is_enrolled,
        'reviews': reviews,
        'categories': CourseCategory.objects.all(),
    }
    return render(request, 'courses/course_detail.html', context)

# ======================
# VISTAS DE ESTUDIANTES
# ======================

@login_required
def enroll(request, course_id):
    """Inscribir a un usuario en un curso"""
    try:
        course = get_object_or_404(Course, id=course_id, is_published=True)

        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={'status': EnrollmentStatusChoices.ACTIVE}
        )

        if created:
            messages.success(request, f'Te has inscrito correctamente en "{course.title}"')
        else:
            messages.info(request, f'Ya estás inscrito en el curso "{course.title}"')

    except Exception as e:
        messages.error(request, 'Ha ocurrido un error al procesar tu inscripción. Por favor, intenta nuevamente.')
        return redirect('courses:courses_list')

    return redirect('courses:course_detail', slug=course.slug)


@login_required
def dashboard(request):
    """Dashboard personal del usuario - Panel de control con cursos inscritos y progreso"""
    # Cursos como estudiante
    user_enrollments = Enrollment.objects.filter(
        student=request.user,
        status=EnrollmentStatusChoices.ACTIVE
    ).select_related('course')

    total_lessons_qs = Lesson.objects.filter(
        module__course=OuterRef('course')
    ).order_by().values('module__course').annotate(total=Count('id')).values('total')[:1]

    completed_lessons_qs = Progress.objects.filter(
        enrollment=OuterRef('pk'),
        completed=True
    ).values('enrollment').annotate(total=Count('id')).values('total')[:1]

    user_enrollments = user_enrollments.annotate(
        total_lessons=Subquery(total_lessons_qs),
        completed_lessons=Subquery(completed_lessons_qs)
    )

    enrollment_stats = []
    for enrollment in user_enrollments:
        total_lessons = enrollment.total_lessons or 0
        completed_lessons = enrollment.completed_lessons or 0
        progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

        enrollment_stats.append({
            'enrollment': enrollment,
            'progress_percentage': progress_percentage,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons
        })

    # Cursos como tutor
    taught_courses = Course.objects.filter(tutor=request.user).annotate(
        student_count=Count('enrollments', filter=Q(enrollments__status=EnrollmentStatusChoices.ACTIVE)),
        avg_rating=Avg('reviews__rating')
    ).prefetch_related('modules__lessons')

    # Estadísticas específicas de cursos
    total_available_courses = Course.objects.filter(is_published=True).count()
    user_course_count = user_enrollments.count()
    completed_courses = sum(1 for stat in enrollment_stats if stat['progress_percentage'] == 100)

    # Funciones disponibles en la app de cursos
    course_functions = [
        {
            'name': 'Explorar Cursos',
            'description': 'Ver catálogo completo de cursos',
            'icon': 'fas fa-search',
            'url': 'courses_list',
            'color': 'primary'
        },
        {
            'name': 'Contenido Educativo',
            'description': 'Lecciones independientes, bloques y contenido gratuito',
            'icon': 'fas fa-collection',
            'url': 'standalone_lessons_list',
            'color': 'success'
        },
        {
            'name': 'Mis Cursos',
            'description': 'Cursos en los que estoy inscrito',
            'icon': 'fas fa-book-reader',
            'url': 'dashboard',
            'color': 'success'
        },
        {
            'name': 'Crear Curso',
            'description': 'Crear un nuevo curso como tutor',
            'icon': 'fas fa-plus',
            'url': 'create_course',
            'color': 'info'
        },
        {
            'name': 'Asistente de Cursos',
            'description': 'Crear curso paso a paso',
            'icon': 'fas fa-magic',
            'url': 'create_course_wizard',
            'color': 'primary'
        },
        {
            'name': 'Gestionar Cursos',
            'description': 'Administrar mis cursos como tutor',
            'icon': 'fas fa-cog',
            'url': 'manage_courses',
            'color': 'warning'
        },
        {
            'name': 'Categorías',
            'description': 'Gestionar categorías de cursos',
            'icon': 'fas fa-tags',
            'url': 'manage_categories',
            'color': 'secondary'
        },
        {
            'name': 'Módulos',
            'description': 'Vista general de módulos',
            'icon': 'fas fa-list',
            'url': 'modules_overview',
            'color': 'dark'
        },
        {
            'name': 'Panel de Administración',
            'description': 'Panel administrativo de cursos',
            'icon': 'fas fa-user-shield',
            'url': 'admin_dashboard',
            'color': 'danger'
        },
        {
            'name': 'Gestión de Usuarios',
            'description': 'Administrar usuarios del sistema',
            'icon': 'fas fa-users-cog',
            'url': 'admin_users',
            'color': 'info'
        },
        {
            'name': 'Gestor de Contenido',
            'description': 'CMS - Crear bloques de contenido reutilizable',
            'icon': 'fas fa-cubes',
            'url': 'content_manager',
            'color': 'dark'
        }
    ]

    context = {
        'enrollment_stats': enrollment_stats,
        'taught_courses': taught_courses,
        'course_functions': course_functions,
        'total_available_courses': total_available_courses,
        'user_course_count': user_course_count,
        'completed_courses': completed_courses,
        'categories': CourseCategory.objects.all(),
    }
    return render(request, 'courses/dashboard.html', context)

@login_required
def course_learning(request, slug, lesson_id=None):
    """Vista para aprender un curso con optimización de consultas"""
    course = get_object_or_404(
        Course.objects.select_related('tutor').prefetch_related(
            Prefetch('modules__lessons', queryset=Lesson.objects.order_by('order'))
        ),
        slug=slug
    )
    
    enrollment = get_object_or_404(
        Enrollment, 
        student=request.user, 
        course=course, 
        status=EnrollmentStatusChoices.ACTIVE
    )
    
    # Obtener todas las lecciones ordenadas
    all_lessons = Lesson.objects.filter(
        module__course=course
    ).select_related('module').order_by('module__order', 'order')
    
    # Obtener lección actual o redirigir a la primera
    if lesson_id:
        current_lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    else:
        first_lesson = all_lessons.first()
        if first_lesson:
            return redirect('courses:course_learning_lesson', slug=slug, lesson_id=first_lesson.id)
        messages.error(request, "Este curso no tiene lecciones disponibles.")
        return redirect('courses:course_detail', slug=slug)
    
    # Obtener progreso de la lección actual
    lesson_progress, created = Progress.objects.get_or_create(
        enrollment=enrollment,
        lesson=current_lesson
    )
    
    # Determinar lección anterior y siguiente
    lesson_list = list(all_lessons)
    current_index = lesson_list.index(current_lesson) if current_lesson in lesson_list else -1
    
    previous_lesson = lesson_list[current_index - 1] if current_index > 0 else None
    next_lesson = lesson_list[current_index + 1] if current_index < len(lesson_list) - 1 else None
    
    # Obtener lecciones completadas
    completed_lessons = Progress.objects.filter(
        enrollment=enrollment, 
        completed=True
    ).values_list('lesson_id', flat=True)
    
    # Manejar envío de formularios
    if request.method == 'POST':
        _handle_lesson_submission(request, current_lesson, lesson_progress)
    
    context = {
        'course': course,
        'modules': course.modules.all().prefetch_related('lessons'),
        'current_lesson': current_lesson,
        'lesson_progress': lesson_progress,
        'enrollment': enrollment,
        'previous_lesson': previous_lesson,
        'next_lesson': next_lesson,
        'completed_lessons': completed_lessons,
    }
    return render(request, 'courses/course_learning.html', context)


def _handle_lesson_submission(request, lesson, progress):
    """Manejar el envío de formularios según el tipo de lección"""
    if lesson.lesson_type == LessonTypeChoices.QUIZ:
        _handle_quiz_submission(request, lesson, progress)
    elif lesson.lesson_type == LessonTypeChoices.ASSIGNMENT:
        _handle_assignment_submission(request, progress)


def _handle_quiz_submission(request, lesson, progress):
    """Procesar envío de quiz"""
    score = 0
    total_questions = len(lesson.quiz_questions)
    
    for i, question in enumerate(lesson.quiz_questions):
        user_answer = request.POST.get(f'question_{i+1}')
        if user_answer and user_answer == question.get('correct_answer'):
            score += 1
    
    percentage = (score / total_questions * 100) if total_questions > 0 else 0
    progress.score = percentage
    progress.completed = True
    progress.completed_at = timezone.now()
    progress.save()
    
    messages.success(request, f"¡Quiz completado! Puntuación: {score}/{total_questions} ({percentage:.1f}%)")


def _handle_assignment_submission(request, progress):
    """Procesar envío de tarea"""
    if request.FILES.get('submission_file'):
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()
        messages.success(request, "¡Tarea enviada correctamente!")
    else:
        messages.error(request, "Debes subir un archivo para completar la tarea.")


@require_POST
@login_required
def mark_lesson_complete(request, lesson_id):
    """Marcar una lección como completada (AJAX/HTTP)"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    enrollment = get_object_or_404(
        Enrollment, 
        student=request.user, 
        course=lesson.module.course, 
        status=EnrollmentStatusChoices.ACTIVE
    )
    
    progress, created = Progress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    
    progress.completed = True
    progress.completed_at = timezone.now()
    progress.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    messages.success(request, f"¡Lección '{lesson.title}' completada!")
    return redirect('courses:course_learning_lesson', 
                   slug=lesson.module.course.slug, 
                   lesson_id=lesson.id)


@login_required
def add_review(request, course_id):
    """Añadir una reseña a un curso"""
    course = get_object_or_404(Course, id=course_id)
    enrollment = get_object_or_404(
        Enrollment, 
        student=request.user, 
        course=course, 
        status=EnrollmentStatusChoices.ACTIVE
    )
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.student = request.user
            review.course = course
            review.save()
            messages.success(request, 'Reseña publicada exitosamente')
            return redirect('courses:course_detail', slug=course.slug)
    else:
        form = ReviewForm()
    
    return render(request, 'courses/add_review.html', {
        'form': form,
        'course': course,
    })


# ======================
# VISTAS PARA TUTORES
# ======================

@login_required
def manage_courses(request):
    """Gestión de cursos para tutores"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor')
        return redirect('cv:detail')

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

    return render(request, 'courses/manage_courses.html', context)


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

    return render(request, 'courses/course_form.html', {
        'form': form,
        'title': 'Crear Nuevo Curso',
    })


@login_required
def create_course_wizard(request):
    """Asistente paso a paso para crear un curso"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor para crear cursos')
        return redirect('cv:detail')

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

    return render(request, 'courses/course_form.html', {
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

    return render(request, 'courses/delete_course.html', context)

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
    
    return render(request, 'courses/course_analytics.html', {
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
    return render(request, 'courses/manage_content.html', context)

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

    return render(request, 'courses/module_form.html', {
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

    return render(request, 'courses/module_form.html', {
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

    return render(request, 'courses/delete_module.html', {
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

    return render(request, 'courses/duplicate_module.html', {
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

    return render(request, 'courses/module_statistics.html', context)

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
    total_modules = sum(course.modules.count() for course in courses)
    total_lessons = sum(
        sum(module.lessons.count() for module in course.modules.all())
        for course in courses
    )

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

    return render(request, 'courses/modules_overview.html', context)

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

    return render(request, 'courses/module_progress.html', context)

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
    return render(request, 'courses/bulk_module_actions.html', {
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

    return render(request, 'courses/standalone_lesson_form.html', context)

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

    return render(request, 'courses/standalone_lesson_form.html', context)

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

    return render(request, 'courses/delete_lesson.html', {
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

    return render(request, 'courses/manage_categories.html', {
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

    return render(request, 'courses/category_form.html', {
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

    return render(request, 'courses/quick_create_category.html', {
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

    return render(request, 'courses/category_form.html', {
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

    return render(request, 'courses/delete_category.html', {
        'category': category,
    })

# ======================
# VISTAS DE ADMINISTRACIÓN
# ======================

@login_required
def admin_dashboard(request):
    """Panel de administración de cursos"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    # Estadísticas generales
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    total_enrollments = Enrollment.objects.count()

    # Cursos recientes
    recent_courses = Course.objects.select_related('tutor', 'category').order_by('-created_at')[:5]

    # Usuarios recientes
    recent_users = User.objects.order_by('-date_joined')[:5]

    context = {
        'total_courses': total_courses,
        'published_courses': published_courses,
        'total_users': total_users,
        'total_enrollments': total_enrollments,
        'recent_courses': recent_courses,
        'recent_users': recent_users,
    }
    return render(request, 'courses/admin/dashboard.html', context)

@login_required
def admin_users(request):
    """Vista de administración de usuarios"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')

    users = User.objects.all().order_by('-date_joined')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    if role_filter:
        if role_filter == 'none':
            users = users.filter(cv__isnull=True)
        else:
            users = users.filter(cv__role=role_filter)

    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
    }
    return render(request, 'courses/admin/users.html', context)

@login_required
def admin_user_detail(request, user_id):
    """Vista de detalle de un usuario para admin"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    user = get_object_or_404(User, id=user_id)

    # Información adicional del usuario
    user_courses = Course.objects.filter(tutor=user)
    user_enrollments = Enrollment.objects.filter(student=user).select_related('course')

    context = {
        'user_detail': user,
        'user_courses': user_courses,
        'user_enrollments': user_enrollments,
    }
    return render(request, 'courses/admin/user_detail.html', context)

@login_required
def edit_user(request, user_id):
    """Editar información de un usuario (admin)"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.is_active = request.POST.get('is_active') == 'on'
        user.save()
        messages.success(request, 'Usuario actualizado exitosamente')
        return redirect('courses:admin_user_detail', user_id=user.id)

    return render(request, 'courses/admin/edit_user.html', {
        'user': user,
    })

# ======================
# CONTENT MANAGEMENT SYSTEM VIEWS
# ======================

@login_required
def content_manager(request):
    """Panel principal de gestión de contenido - CMS integrado"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor para acceder al gestor de contenido')
        return redirect('home')

    # Obtener bloques del usuario y públicos
    user_blocks = ContentBlock.objects.filter(
        models.Q(author=request.user) | models.Q(is_public=True)
    ).select_related('author').order_by('-updated_at')

    # Estadísticas
    total_blocks = user_blocks.count()
    user_own_blocks = user_blocks.filter(author=request.user).count()
    featured_blocks = user_blocks.filter(is_featured=True).count()

    # Categorías disponibles
    categories = ContentBlock.objects.filter(
        models.Q(author=request.user) | models.Q(is_public=True)
    ).values_list('category', flat=True).distinct()

    # Funciones disponibles en el CMS
    cms_functions = [
        {
            'name': 'Crear Bloque HTML',
            'description': 'Crear un nuevo bloque de contenido HTML/Bootstrap',
            'icon': 'fas fa-code',
            'url': 'courses:create_content_block',
            'color': 'primary',
            'params': {'block_type': 'html'}
        },
        {
            'name': 'Crear Componente Bootstrap',
            'description': 'Crear un componente reutilizable con Bootstrap',
            'icon': 'fas fa-bootstrap',
            'url': 'courses:create_content_block',
            'color': 'info',
            'params': {'block_type': 'bootstrap'}
        },
        {
            'name': 'Crear Contenido Markdown',
            'description': 'Crear contenido usando sintaxis Markdown',
            'icon': 'fas fa-markdown',
            'url': 'courses:create_content_block',
            'color': 'success',
            'params': {'block_type': 'markdown'}
        },
        {
            'name': 'Mis Bloques',
            'description': 'Ver todos mis bloques de contenido',
            'icon': 'fas fa-folder',
            'url': 'courses:my_content_blocks',
            'color': 'secondary',
            'params': {}
        },
        {
            'name': 'Bloques Destacados',
            'description': 'Bloques destacados por la comunidad',
            'icon': 'fas fa-star',
            'url': 'courses:featured_content_blocks',
            'color': 'warning',
            'params': {}
        },
        {
            'name': 'Biblioteca Pública',
            'description': 'Bloques públicos disponibles para todos',
            'icon': 'fas fa-globe',
            'url': 'courses:public_content_blocks',
            'color': 'dark',
            'params': {}
        },
    ]

    context = {
        'user_blocks': user_blocks[:12],  # Mostrar últimos 12
        'total_blocks': total_blocks,
        'user_own_blocks': user_own_blocks,
        'featured_blocks': featured_blocks,
        'categories': categories,
        'cms_functions': cms_functions,
        'title': 'Gestor de Contenido - CMS',
    }

    return render(request, 'courses/content_manager.html', context)

@login_required
def create_content_block(request, block_type='html'):
    """Crear un nuevo bloque de contenido"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor para crear contenido')
        return redirect('cv:cv_detail')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category = request.POST.get('category', '')
        tags = request.POST.get('tags', '')
        is_public = request.POST.get('is_public') == 'on'

        # Crear el bloque según el tipo
        block = ContentBlock.objects.create(
            title=title,
            description=description,
            content_type=block_type,
            author=request.user,
            category=category,
            tags=tags,
            is_public=is_public
        )

        # Guardar contenido según el tipo
        if block_type in ['html', 'bootstrap']:
            block.html_content = request.POST.get('html_content', '')
        elif block_type == 'markdown':
            block.markdown_content = request.POST.get('markdown_content', '')
        elif block_type == 'json':
            # Procesar JSON si es necesario
            json_content = request.POST.get('json_content', '{}')
            try:
                import json
                block.json_content = json.loads(json_content)
            except:
                block.json_content = {}
        elif block_type == 'text':
            block.html_content = request.POST.get('text_content', '')
        elif block_type == 'image':
            block.json_content = {
                'url': request.POST.get('image_url', ''),
                'alt': request.POST.get('image_alt', ''),
                'caption': request.POST.get('image_caption', '')
            }
        elif block_type == 'video':
            block.json_content = {
                'url': request.POST.get('video_url', ''),
                'description': request.POST.get('video_description', ''),
                'duration': request.POST.get('video_duration', '')
            }
        elif block_type == 'quote':
            block.json_content = {
                'text': request.POST.get('quote_text', ''),
                'author': request.POST.get('quote_author', '')
            }
        elif block_type == 'code':
            block.json_content = {
                'language': request.POST.get('code_language', 'text'),
                'title': request.POST.get('code_title', ''),
                'code': request.POST.get('code_content', '')
            }
        elif block_type == 'list':
            block.json_content = {
                'type': request.POST.get('list_type', 'unordered'),
                'items': [item.strip() for item in request.POST.get('list_items', '').split('\n') if item.strip()]
            }
        elif block_type == 'table':
            headers = [h.strip() for h in request.POST.get('table_headers', '').split(',') if h.strip()]
            rows = []
            for row in request.POST.get('table_rows', '').split('\n'):
                if row.strip():
                    cells = [cell.strip() for cell in row.split(',') if cell.strip()]
                    if cells:
                        rows.append(cells)
            block.json_content = {
                'headers': headers,
                'rows': rows
            }
        elif block_type == 'card':
            block.json_content = {
                'header': request.POST.get('card_header', ''),
                'title': request.POST.get('card_title', ''),
                'text': request.POST.get('card_text', ''),
                'button': {
                    'url': request.POST.get('card_button_url', ''),
                    'text': request.POST.get('card_button_text', 'Ver más')
                }
            }
        elif block_type == 'alert':
            block.json_content = {
                'type': request.POST.get('alert_type', 'info'),
                'message': request.POST.get('alert_message', '')
            }
        elif block_type == 'button':
            block.json_content = {
                'url': request.POST.get('button_url', ''),
                'text': request.POST.get('button_text', ''),
                'style': request.POST.get('button_style', 'primary'),
                'size': request.POST.get('button_size', 'md'),
                'icon': request.POST.get('button_icon', '')
            }
        elif block_type == 'form':
            try:
                import json
                fields = json.loads(request.POST.get('form_fields', '[]'))
            except:
                fields = []
            block.json_content = {
                'action': request.POST.get('form_action', ''),
                'fields': fields,
                'submit_text': request.POST.get('form_submit_text', 'Enviar')
            }
        elif block_type == 'divider':
            block.json_content = {}
        elif block_type == 'icon':
            block.json_content = {
                'icon': request.POST.get('icon_name', ''),
                'color': request.POST.get('icon_color', 'primary'),
                'text': request.POST.get('icon_text', '')
            }
        elif block_type == 'progress':
            block.json_content = {
                'value': int(request.POST.get('progress_value', 50)),
                'color': request.POST.get('progress_color', 'primary')
            }
        elif block_type == 'badge':
            block.json_content = {
                'text': request.POST.get('badge_text', ''),
                'color': request.POST.get('badge_color', 'primary'),
                'icon': request.POST.get('badge_icon', '')
            }
        elif block_type == 'timeline':
            try:
                import json
                items = json.loads(request.POST.get('timeline_items', '[]'))
            except:
                items = []
            block.json_content = {
                'items': items
            }

        block.save()

        messages.success(request, f'Bloque "{title}" creado exitosamente')
        return redirect('courses:edit_content_block', slug=block.slug)

    # Preparar datos según el tipo
    context = {
        'block_type': block_type,
        'title': f'Crear Bloque - {dict(ContentBlock.CONTENT_TYPES)[block_type]}',
        'content_types': ContentBlock.CONTENT_TYPES,
    }

    return render(request, 'courses/content_block_form.html', context)

@login_required
def edit_content_block(request, slug):
    """Editar un bloque de contenido existente"""
    block = get_object_or_404(ContentBlock, slug=slug)

    # Verificar permisos
    if block.author != request.user and not block.is_public:
        messages.error(request, 'No tienes permisos para editar este bloque')
        return redirect('courses:content_manager')

    if request.method == 'POST':
        block.title = request.POST.get('title')
        block.description = request.POST.get('description')
        block.category = request.POST.get('category', '')
        block.tags = request.POST.get('tags', '')
        block.is_public = request.POST.get('is_public') == 'on'
        block.is_featured = request.POST.get('is_featured') == 'on'

        # Actualizar contenido según el tipo
        if block.content_type in ['html', 'bootstrap']:
            block.html_content = request.POST.get('html_content', '')
        elif block.content_type == 'markdown':
            block.markdown_content = request.POST.get('markdown_content', '')
        elif block.content_type == 'json':
            json_content = request.POST.get('json_content', '{}')
            try:
                import json
                block.json_content = json.loads(json_content)
            except:
                messages.error(request, 'Contenido JSON inválido')
                return redirect('courses:edit_content_block', slug=block.slug)
        elif block.content_type == 'text':
            block.html_content = request.POST.get('text_content', '')
        elif block.content_type == 'image':
            block.json_content = {
                'url': request.POST.get('image_url', ''),
                'alt': request.POST.get('image_alt', ''),
                'caption': request.POST.get('image_caption', '')
            }
        elif block.content_type == 'video':
            block.json_content = {
                'url': request.POST.get('video_url', ''),
                'description': request.POST.get('video_description', ''),
                'duration': request.POST.get('video_duration', '')
            }
        elif block.content_type == 'quote':
            block.json_content = {
                'text': request.POST.get('quote_text', ''),
                'author': request.POST.get('quote_author', '')
            }
        elif block.content_type == 'code':
            block.json_content = {
                'language': request.POST.get('code_language', 'text'),
                'title': request.POST.get('code_title', ''),
                'code': request.POST.get('code_content', '')
            }
        elif block.content_type == 'list':
            block.json_content = {
                'type': request.POST.get('list_type', 'unordered'),
                'items': [item.strip() for item in request.POST.get('list_items', '').split('\n') if item.strip()]
            }
        elif block.content_type == 'table':
            headers = [h.strip() for h in request.POST.get('table_headers', '').split(',') if h.strip()]
            rows = []
            for row in request.POST.get('table_rows', '').split('\n'):
                if row.strip():
                    cells = [cell.strip() for cell in row.split(',') if cell.strip()]
                    if cells:
                        rows.append(cells)
            block.json_content = {
                'headers': headers,
                'rows': rows
            }
        elif block.content_type == 'card':
            block.json_content = {
                'header': request.POST.get('card_header', ''),
                'title': request.POST.get('card_title', ''),
                'text': request.POST.get('card_text', ''),
                'button': {
                    'url': request.POST.get('card_button_url', ''),
                    'text': request.POST.get('card_button_text', 'Ver más')
                }
            }
        elif block.content_type == 'alert':
            block.json_content = {
                'type': request.POST.get('alert_type', 'info'),
                'message': request.POST.get('alert_message', '')
            }
        elif block.content_type == 'button':
            block.json_content = {
                'url': request.POST.get('button_url', ''),
                'text': request.POST.get('button_text', ''),
                'style': request.POST.get('button_style', 'primary'),
                'size': request.POST.get('button_size', 'md'),
                'icon': request.POST.get('button_icon', '')
            }
        elif block.content_type == 'form':
            try:
                import json
                fields = json.loads(request.POST.get('form_fields', '[]'))
            except:
                fields = []
            block.json_content = {
                'action': request.POST.get('form_action', ''),
                'fields': fields,
                'submit_text': request.POST.get('form_submit_text', 'Enviar')
            }
        elif block.content_type == 'divider':
            block.json_content = {}
        elif block.content_type == 'icon':
            block.json_content = {
                'icon': request.POST.get('icon_name', ''),
                'color': request.POST.get('icon_color', 'primary'),
                'text': request.POST.get('icon_text', '')
            }
        elif block.content_type == 'progress':
            block.json_content = {
                'value': int(request.POST.get('progress_value', 50)),
                'color': request.POST.get('progress_color', 'primary')
            }
        elif block.content_type == 'badge':
            block.json_content = {
                'text': request.POST.get('badge_text', ''),
                'color': request.POST.get('badge_color', 'primary'),
                'icon': request.POST.get('badge_icon', '')
            }
        elif block.content_type == 'timeline':
            try:
                import json
                items = json.loads(request.POST.get('timeline_items', '[]'))
            except:
                items = []
            block.json_content = {
                'items': items
            }

        block.save()
        messages.success(request, f'Bloque "{block.title}" actualizado exitosamente')
        return redirect('courses:edit_content_block', slug=block.slug)

    context = {
        'content_block': block,
        'title': f'Editar Bloque - {block.title}',
        'content_types': ContentBlock.CONTENT_TYPES,
    }

    return render(request, 'courses/content_block_form.html', context)

@login_required
def delete_content_block(request, slug):
    """Eliminar un bloque de contenido"""
    block = get_object_or_404(ContentBlock, slug=slug)

    # Verificar permisos
    if block.author != request.user:
        messages.error(request, 'No tienes permisos para eliminar este bloque')
        return redirect('courses:content_manager')

    if request.method == 'POST':
        title = block.title
        block.delete()
        messages.success(request, f'Bloque "{title}" eliminado exitosamente')
        return redirect('courses:content_manager')

    return render(request, 'courses/delete_content_block.html', {
        'block': block,
    })

@login_required
def my_content_blocks(request):
    """Ver bloques de contenido del usuario actual"""
    blocks = ContentBlock.objects.filter(author=request.user).order_by('-updated_at')

    # Filtros
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    search = request.GET.get('search')

    if category_filter:
        blocks = blocks.filter(category=category_filter)
    if type_filter:
        blocks = blocks.filter(content_type=type_filter)
    if search:
        blocks = blocks.filter(
            models.Q(title__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(tags__icontains=search)
        )

    # Estadísticas
    total_blocks = blocks.count()
    public_blocks = blocks.filter(is_public=True).count()
    featured_blocks = blocks.filter(is_featured=True).count()

    context = {
        'blocks': blocks,
        'total_blocks': total_blocks,
        'public_blocks': public_blocks,
        'featured_blocks': featured_blocks,
        'categories': ContentBlock.objects.filter(author=request.user).values_list('category', flat=True).distinct(),
        'content_types': ContentBlock.CONTENT_TYPES,
        'title': 'Mis Bloques de Contenido',
    }

    return render(request, 'courses/content_blocks_list.html', context)

def public_content_blocks(request):
    """Ver bloques de contenido públicos disponibles"""
    blocks = ContentBlock.objects.filter(is_public=True).select_related('author').order_by('-updated_at')

    # Filtros
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    author_filter = request.GET.get('author')
    search = request.GET.get('search')

    if category_filter:
        blocks = blocks.filter(category=category_filter)
    if type_filter:
        blocks = blocks.filter(content_type=type_filter)
    if author_filter:
        blocks = blocks.filter(author__username=author_filter)
    if search:
        blocks = blocks.filter(
            models.Q(title__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(tags__icontains=search)
        )

    # Estadísticas
    total_blocks = blocks.count()
    featured_blocks = blocks.filter(is_featured=True).count()

    # Autores únicos
    authors = blocks.values_list('author__username', 'author__first_name', 'author__last_name').distinct()

    context = {
        'blocks': blocks,
        'total_blocks': total_blocks,
        'featured_blocks': featured_blocks,
        'categories': CourseCategory.objects.all(),
        'authors': authors,
        'content_types': ContentBlock.CONTENT_TYPES,
        'title': 'Biblioteca Pública de Contenido',
    }

    return render(request, 'courses/public_content_blocks.html', context)


def public_content_detail(request, slug):
    """Vista pública de detalle de un bloque, accesible sin login"""
    block = get_object_or_404(ContentBlock, slug=slug)
    if not block.is_public and (not request.user.is_authenticated or block.author != request.user):
        from django.contrib import messages
        messages.error(request, 'Este contenido no es público.')
        return redirect('courses:public_content_blocks')

    force_css = """
    <style id="public-overflow-fix">
      #public-overflow-fix + .public-card, .public-card { overflow-x: auto !important; }
      #public-overflow-fix + .public-card table, #public-overflow-fix ~ .public-card table, .public-card table { display: block !important; overflow-x: auto !important; width: auto !important; max-width: 100%; }
      #public-overflow-fix + .public-card th, #public-overflow-fix + .public-card td,
      #public-overflow-fix ~ .public-card th, #public-overflow-fix ~ .public-card td,
      .public-card th, .public-card td { white-space: nowrap !important; }
      #public-overflow-fix + .public-card img, #public-overflow-fix ~ .public-card img, .public-card img { max-width: 100% !important; height: auto !important; }
    </style>
    """

    context = {
        'block': block,
        'title': block.title,
        'force_css': force_css,
        'categories': CourseCategory.objects.all(),
    }

    response = render(request, 'courses/public_content_detail.html', context)
    return response


@login_required
def featured_content_blocks(request):
    """Ver bloques de contenido destacados"""
    blocks = ContentBlock.objects.filter(is_featured=True).select_related('author').order_by('-updated_at')

    context = {
        'blocks': blocks,
        'title': 'Bloques Destacados',
    }

    return render(request, 'courses/content_blocks_list.html', context)

@login_required
def duplicate_content_block(request, slug):
    """Duplicar un bloque de contenido"""
    original_block = get_object_or_404(ContentBlock, slug=slug)

    # Verificar que el usuario pueda acceder al bloque
    if original_block.author != request.user and not original_block.is_public:
        messages.error(request, 'No tienes permisos para duplicar este bloque')
        return redirect('courses:content_manager')

    if request.method == 'POST':
        # Crear copia
        new_block = ContentBlock.objects.create(
            title=f"{original_block.title} (Copia)",
            description=original_block.description,
            content_type=original_block.content_type,
            html_content=original_block.html_content,
            json_content=original_block.json_content,
            markdown_content=original_block.markdown_content,
            author=request.user,
            category=original_block.category,
            tags=original_block.tags,
            is_public=False,  # Las copias son privadas por defecto
        )

        messages.success(request, f'Bloque "{original_block.title}" duplicado exitosamente')
        return redirect('courses:edit_content_block', slug=new_block.slug)

    return render(request, 'courses/duplicate_content_block.html', {
        'content_block': original_block,
    })

@require_POST
@login_required
def toggle_block_featured(request, slug):
    """Alternar estado destacado de un bloque (solo para el autor)"""
    block = get_object_or_404(ContentBlock, slug=slug)

    if block.author != request.user:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    block.is_featured = not block.is_featured
    block.save()

    return JsonResponse({
        'success': True,
        'is_featured': block.is_featured
    })

@require_POST
@login_required
def toggle_block_public(request, slug):
    """Alternar visibilidad pública de un bloque"""
    block = get_object_or_404(ContentBlock, slug=slug)

    if block.author != request.user:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    block.is_public = not block.is_public
    block.save()

    return JsonResponse({
        'success': True,
        'is_public': block.is_public
    })

@login_required
def preview_content_block(request, slug):
    """Vista previa de un bloque de contenido"""
    block = get_object_or_404(ContentBlock, slug=slug)

    # Verificar permisos
    if block.author != request.user and not block.is_public:
        messages.error(request, 'No tienes permisos para ver este bloque')
        return redirect('courses:content_manager')

    context = {
        'content_block': block,
        'title': f'Vista Previa - {block.title}',
    }

    return render(request, 'courses/content_block_preview.html', context)

# ======================
# STANDALONE LESSONS VIEWS
# ======================

@login_required
def standalone_lessons_list(request):
    """Lista todas las lecciones independientes, bloques de contenido y lecciones gratuitas disponibles"""
    # Lecciones independientes
    standalone_lessons = Lesson.objects.filter(
        module__isnull=True,
        is_published=True
    ).select_related('author').order_by('-created_at')

    # Lecciones gratuitas de cursos
    free_course_lessons = Lesson.objects.filter(
        module__isnull=False,
        is_free=True,
        module__course__is_published=True
    ).select_related('author', 'module__course').order_by('-created_at')

    # Combinar todas las lecciones
    all_lessons = list(standalone_lessons) + list(free_course_lessons)

    # Bloques de contenido públicos y destacados
    content_blocks = ContentBlock.objects.filter(
        models.Q(is_public=True) | models.Q(is_featured=True)
    ).select_related('author').order_by('-updated_at')

    # Filtros
    content_type = request.GET.get('content_type', 'all')  # all, lessons, blocks
    author_filter = request.GET.get('author')
    search = request.GET.get('search')

    # Filtrar lecciones
    filtered_lessons = all_lessons
    if author_filter:
        filtered_lessons = [l for l in filtered_lessons if l.author.username == author_filter]
    if search:
        search_lower = search.lower()
        filtered_lessons = [l for l in filtered_lessons if
                           search_lower in l.title.lower() or
                           (l.description and search_lower in l.description.lower())]

    # Filtrar bloques
    filtered_blocks = content_blocks
    if author_filter:
        filtered_blocks = filtered_blocks.filter(author__username=author_filter)
    if search:
        filtered_blocks = filtered_blocks.filter(
            models.Q(title__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(tags__icontains=search)
        )

    # Aplicar filtro de tipo de contenido
    if content_type == 'lessons':
        filtered_blocks = ContentBlock.objects.none()
    elif content_type == 'blocks':
        filtered_lessons = []

    # Autores únicos de lecciones
    lesson_authors = set()
    for lesson in all_lessons:
        if lesson.author:  # Verificar que el autor no sea None
            lesson_authors.add((lesson.author.username, lesson.author.first_name, lesson.author.last_name))

    # Autores únicos de bloques
    block_authors = set(filtered_blocks.values_list('author__username', 'author__first_name', 'author__last_name'))

    # Combinar autores
    all_authors = lesson_authors.union(block_authors)

    context = {
        'lessons': filtered_lessons,
        'content_blocks': filtered_blocks,
        'authors': all_authors,
        'title': 'Contenido Educativo Disponible',
        'content_type': content_type,
        'total_lessons': len(filtered_lessons),
        'total_blocks': filtered_blocks.count(),
    }

    return render(request, 'courses/standalone_lessons_list.html', context)

@login_required
def standalone_lesson_detail(request, slug):
    """Vista detallada de una lección independiente"""
    lesson = get_object_or_404(
        Lesson.objects.select_related('author'),
        slug=slug,
        module__isnull=True,
        is_published=True
    )

    context = {
        'lesson': lesson,
        'title': lesson.title,
    }

    return render(request, 'courses/standalone_lesson_detail.html', context)

@login_required
def my_standalone_lessons(request):
    """Lista las lecciones independientes del usuario actual"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor para crear lecciones independientes')
        return redirect('cv:detail')

    lessons = Lesson.objects.filter(
        author=request.user,
        module__isnull=True
    ).order_by('-updated_at')

    # Calcular estadísticas
    published_count = lessons.filter(is_published=True).count()
    draft_count = lessons.filter(is_published=False).count()
    featured_count = lessons.filter(is_featured=True).count()

    context = {
        'lessons': lessons,
        'title': 'Mis Lecciones Independientes',
        'published_count': published_count,
        'draft_count': draft_count,
        'featured_count': featured_count,
    }

    return render(request, 'courses/my_standalone_lessons.html', context)

@login_required
def create_standalone_lesson(request):
    """Crear una nueva lección independiente"""
    if not hasattr(request.user, 'cv'):
        messages.error(request, 'Necesitas un perfil de tutor para crear lecciones independientes')
        return redirect('cv:detail')

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.author = request.user
            lesson.is_published = False  # Las nuevas lecciones empiezan como borrador
            lesson.save()
            messages.success(request, 'Lección independiente creada exitosamente')
            return redirect('courses:edit_standalone_lesson', slug=lesson.slug)
    else:
        form = LessonForm()

    # Obtener bloques de contenido disponibles
    available_content_blocks = ContentBlock.objects.filter(
        models.Q(author=request.user) | models.Q(is_public=True)
    ).select_related('author').order_by('title')

    context = {
        'form': form,
        'title': 'Crear Lección Independiente',
        'lesson': None,
        'lesson_types': LessonTypeChoices.choices,
        'available_content_blocks': available_content_blocks,
        'is_standalone': True,
    }

    return render(request, 'courses/standalone_lesson_form.html', context)

@login_required
def edit_standalone_lesson(request, slug):
    """Editar una lección independiente existente"""
    lesson = get_object_or_404(
        Lesson,
        slug=slug,
        author=request.user,
        module__isnull=True
    )

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lección independiente actualizada exitosamente')
            return redirect('courses:edit_standalone_lesson', slug=lesson.slug)
    else:
        form = LessonForm(instance=lesson)

    # Obtener bloques de contenido disponibles
    available_content_blocks = ContentBlock.objects.filter(
        models.Q(author=request.user) | models.Q(is_public=True)
    ).select_related('author').order_by('title')

    context = {
        'form': form,
        'title': f'Editar Lección: {lesson.title}',
        'lesson': lesson,
        'has_structured_content': bool(lesson.structured_content),
        'structured_content_count': len(lesson.structured_content) if lesson.structured_content else 0,
        'lesson_types': LessonTypeChoices.choices,
        'available_content_blocks': available_content_blocks,
        'is_standalone': True,
    }

    return render(request, 'courses/standalone_lesson_form.html', context)

@login_required
def delete_standalone_lesson(request, slug):
    """Eliminar una lección independiente"""
    lesson = get_object_or_404(
        Lesson,
        slug=slug,
        author=request.user,
        module__isnull=True
    )

    if request.method == 'POST':
        title = lesson.title
        lesson.delete()
        messages.success(request, f'Lección independiente "{title}" eliminada exitosamente')
        return redirect('courses:my_standalone_lessons')

    return render(request, 'courses/delete_standalone_lesson.html', {
        'lesson': lesson,
    })

@login_required
def preview_lesson(request, course_slug, module_id, lesson_id):
    """Vista previa de una lección para tutores - modo solo lectura"""
    course = get_object_or_404(Course, slug=course_slug, tutor=request.user)
    module = get_object_or_404(Module, id=module_id, course=course)
    lesson = get_object_or_404(Lesson, id=lesson_id, module=module)

    context = {
        'course': course,
        'current_lesson': lesson,
        'preview_mode': True,  # Flag para indicar que estamos en modo vista previa
        'title': f'Vista Previa - {lesson.title}',
    }

    return render(request, 'courses/lesson_preview.html', context)

@require_POST
@login_required
def toggle_lesson_published(request, slug):
    """Alternar estado de publicación de una lección independiente"""
    lesson = get_object_or_404(
        Lesson,
        slug=slug,
        author=request.user,
        module__isnull=True
    )

    lesson.is_published = not lesson.is_published
    lesson.save()

    status = "publicada" if lesson.is_published else "ocultada"
    messages.success(request, f'Lección "{lesson.title}" {status} exitosamente')

    return JsonResponse({
        'success': True,
        'is_published': lesson.is_published
    })


@require_GET
def courses_docs(request):
    """Vista para mostrar la documentación de la app courses (README.md)"""
    try:
        # Leer el archivo README.md
        readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        context = {
            'title': 'Documentación - App Courses',
            'content': content,
            'page_title': 'Documentación de la App Courses',
            'categories': CourseCategory.objects.all(),
        }

        return render(request, 'courses/docs.html', context)

    except FileNotFoundError:
        messages.error(request, 'Archivo de documentación no encontrado')
        return redirect('courses:index')
    except Exception as e:
        messages.error(request, f'Error al cargar la documentación: {str(e)}')
        return redirect('courses:index')