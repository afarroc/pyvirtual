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
        'categories': CourseCategory.objects.all(),
    }

    return render(request, 'courses/public/standalone_lessons_list.html', context)


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

    return render(request, 'courses/public/standalone_lesson_detail.html', context)


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

    return render(request, 'courses/student/my_standalone_lessons.html', context)


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

    return render(request, 'courses/public/standalone_lesson_form.html', context)


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

    return render(request, 'courses/public/standalone_lesson_form.html', context)


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

    return render(request, 'courses/public/delete_standalone_lesson.html', {
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

    return render(request, 'courses/public/lesson_preview.html', context)


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
