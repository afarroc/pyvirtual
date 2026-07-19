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
def admin_dashboard(request):
    """Panel de administración de cursos"""
    if not request.user.is_staff:
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('courses:courses_list')

    # Estadísticas generales
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    total_enrollments = Enrollment.objects.filter(status=EnrollmentStatusChoices.ACTIVE).count()
    total_categories = CourseCategory.objects.count()
    total_tutors = User.objects.filter(cv__isnull=False).count()

    stats = {
        'total_courses': total_courses,
        'published_courses': published_courses,
        'total_users': total_users,
        'total_enrollments': total_enrollments,
        'total_categories': total_categories,
        'total_students': total_enrollments,
        'total_tutors': total_tutors,
    }

    # Cursos recientes
    recent_courses = Course.objects.select_related('tutor', 'category').order_by('-created_at')[:5]

    # Usuarios recientes
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Categorías para navbar y estadísticas
    categories = CourseCategory.objects.all()
    categories_stats = CourseCategory.objects.annotate(
        courses_count=Count('courses'),
        students_count=Count('courses__enrollments', filter=Q(courses__enrollments__status=EnrollmentStatusChoices.ACTIVE))
    ).order_by('-courses_count')[:5]

    context = {
        'stats': stats,
        'recent_courses': recent_courses,
        'recent_users': recent_users,
        'categories': categories,
        'categories_stats': categories_stats,
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

    categories = CourseCategory.objects.all()

    context = {
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'categories': categories,
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

    user_stats = {
        'courses_as_student': Enrollment.objects.filter(student=user).count(),
        'courses_as_tutor': Course.objects.filter(tutor=user).count(),
        'completed_enrollments': Enrollment.objects.filter(student=user, status=EnrollmentStatusChoices.COMPLETED).count(),
        'reviews_count': Review.objects.filter(student=user).count(),
    }

    categories = CourseCategory.objects.all()

    context = {
        'user_detail': user,
        'user_profile': user,
        'user_courses': user_courses,
        'user_enrollments': user_enrollments,
        'user_stats': user_stats,
        'categories': categories,
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

    categories = CourseCategory.objects.all()

    return render(request, 'courses/admin/edit_user.html', {
        'user': user,
        'categories': categories,
    })

# ======================
# CONTENT MANAGEMENT SYSTEM VIEWS
# ======================
