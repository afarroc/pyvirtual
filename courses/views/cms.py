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

    return render(request, 'courses/cms/content_manager.html', context)


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

    return render(request, 'courses/cms/content_block_form.html', context)


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

    return render(request, 'courses/cms/content_block_form.html', context)


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

    return render(request, 'courses/cms/delete_content_block.html', {
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

    return render(request, 'courses/cms/content_blocks_list.html', context)


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

    return render(request, 'courses/public/public_content_blocks.html', context)


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

    response = render(request, 'courses/public/public_content_detail.html', context)
    return response


@login_required
def featured_content_blocks(request):
    """Ver bloques de contenido destacados"""
    blocks = ContentBlock.objects.filter(is_featured=True).select_related('author').order_by('-updated_at')

    context = {
        'blocks': blocks,
        'title': 'Bloques Destacados',
    }

    return render(request, 'courses/cms/content_blocks_list.html', context)


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

    return render(request, 'courses/cms/duplicate_content_block.html', {
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

    return render(request, 'courses/cms/content_block_preview.html', context)

# ======================
# STANDALONE LESSONS VIEWS
# ======================
