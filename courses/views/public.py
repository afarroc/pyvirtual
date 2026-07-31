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
    return render(request, 'courses/public/home.html', context)


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
    total_students = courses.aggregate(total=models.Sum('students_count'))['total'] or 0
    average_rating = courses.aggregate(avg=models.Avg('average_rating', filter=models.Q(average_rating__gt=0)))['avg'] or 0

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
    return render(request, 'courses/public/course_list.html', context)


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
    return render(request, 'courses/public/course_detail.html', context)

# ======================
# VISTAS DE ESTUDIANTES
# ======================


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

        return render(request, 'courses/public/docs.html', context)

    except FileNotFoundError:
        messages.error(request, 'Archivo de documentación no encontrado')
        return redirect('courses:index')
    except Exception as e:
        messages.error(request, f'Error al cargar la documentación: {str(e)}')
        return redirect('courses:index')
