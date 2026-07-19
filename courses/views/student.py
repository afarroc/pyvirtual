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
    return render(request, 'courses/student/dashboard.html', context)


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
    return render(request, 'courses/public/course_learning.html', context)


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
    
    return render(request, 'courses/student/add_review.html', {
        'form': form,
        'course': course,
    })


# ======================
# VISTAS PARA TUTORES
# ======================
