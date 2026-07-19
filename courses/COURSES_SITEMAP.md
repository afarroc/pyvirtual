# Mapa del Sitio — App `courses` (Management360)

Estructura de URLs y plantillas tras el reordenamiento (2026-07-18).
Base: `/courses/`. Namespace: `courses`.

## 1. Público (anónimo + auth, filtra `is_published=True`)

| Método | Ruta | Vista | name | Plantilla |
|--------|------|------|------|-----------|
| GET | `/` | `index` | `index` | `public/home.html` |
| GET | `/courses/` | `course_list` | `courses_list` | `public/course_list.html` |
| GET | `/category/<slug>/` | `course_list` | `course_list_by_category` | `public/course_list.html` |
| GET | `/<slug>/` | `course_detail` | `course_detail` | `public/course_detail.html` |
| GET | `/<slug>/learn/` | `course_learning` | `course_learning` | `public/course_learning.html` |
| GET | `/<slug>/learn/<id>/` | `course_learning` | `course_learning_lesson` | `public/course_learning.html` |
| GET | `/docs/` | `courses_docs` | `docs` | `public/docs.html` |
| GET | `/content/public/` | `public_content_blocks` | `public_content_blocks` | `public/public_content_blocks.html` |
| GET | `/content/public/<slug>/` | `public_content_detail` | `public_content_detail` | `public/public_content_detail.html` |
| GET | `/lessons/` | `standalone_lessons_list` | `standalone_lessons_list` | `public/standalone_lessons_list.html` |
| GET | `/lessons/<slug>/` | `standalone_lesson_detail` | `standalone_lesson_detail` | `public/standalone_lesson_detail.html` |

## 2. Estudiante (login requerido)

| Método | Ruta | Vista | name | Plantilla |
|--------|------|------|------|-----------|
| GET/POST | `/dashboard/` | `dashboard` | `dashboard` | `student/dashboard.html` |
| POST | `/<id>/enroll/` | `enroll` | `enroll` | (redirect) |
| POST | `/lesson/<id>/complete/` | `mark_lesson_complete` | `mark_lesson_complete` | (ajax/json) |
| GET/POST | `/<id>/review/` | `add_review` | `add_review` | `student/add_review.html` |
| GET | `/lessons/my-lessons/` | `my_standalone_lessons` | `my_standalone_lessons` | `student/my_standalone_lessons.html` |

## 3. Tutor (login + perfil CV)

| Método | Ruta | Vista | name | Plantilla |
|--------|------|------|------|-----------|
| GET | `/manage/` | `manage_courses` | `manage_courses` | `tutor/manage_courses.html` |
| GET/POST | `/manage/create/` | `create_course` | `create_course` | `tutor/course_form.html` |
| GET/POST | `/manage/create/wizard/` | `create_course_wizard` | `create_course_wizard` | `tutor/course_wizard_step1/2.html` |
| GET/POST | `/manage/<slug>/edit/` | `edit_course` | `edit_course` | `tutor/course_form.html` |
| GET/POST | `/manage/<slug>/delete/` | `delete_course` | `delete_course` | `tutor/delete_course.html` |
| GET | `/manage/<slug>/analytics/` | `course_analytics` | `course_analytics` | `tutor/course_analytics.html` |
| GET | `/manage/<slug>/content/` | `manage_content` | `manage_content` | `tutor/manage_content.html` |
| Módulos | `/manage/<slug>/modules/...` | create/edit/delete/duplicate/statistics/progress/reorder/bulk-actions | varios | `tutor/*.html` |
| Lecciones módulo | `/manage/<slug>/modules/<id>/lessons/...` | create/edit/delete/preview | varios | `tutor/lesson_form.html` |
| GET | `/modules/overview/` | `modules_overview` | `modules_overview` | `tutor/modules_overview.html` |
| Categorías | `/manage/categories/...` | manage/create/quick-create/edit/delete | varios | `tutor/*.html` |

## 4. CMS (login)

| Método | Ruta | Vista | name | Plantilla |
|--------|------|------|------|-----------|
| GET | `/content/` | `content_manager` | `content_manager` | `cms/content_manager.html` |
| GET/POST | `/content/create/<type>/` | `create_content_block` | `create_content_block` | `cms/content_block_form.html` |
| GET/POST | `/content/create/` | `create_content_block` | `create_content_block_default` | `cms/content_block_form.html` |
| GET/POST | `/content/<slug>/edit/` | `edit_content_block` | `edit_content_block` | `cms/content_block_form.html` |
| POST | `/content/<slug>/delete/` | `delete_content_block` | `delete_content_block` | `cms/delete_content_block.html` |
| POST | `/content/<slug>/duplicate/` | `duplicate_content_block` | `duplicate_content_block` | `cms/duplicate_content_block.html` |
| GET | `/content/<slug>/preview/` | `preview_content_block` | `preview_content_block` | `cms/content_block_preview.html` |
| GET | `/content/my-blocks/` | `my_content_blocks` | `my_content_blocks` | `cms/content_blocks_list.html` |
| GET | `/content/featured/` | `featured_content_blocks` | `featured_content_blocks` | `cms/content_blocks_list.html` |
| POST | `/content/<slug>/toggle-featured/` | `toggle_block_featured` | `toggle_block_featured` | (json) |
| POST | `/content/<slug>/toggle-public/` | `toggle_block_public` | `toggle_block_public` | (json) |

## 5. Lecciones independientes (gestión del autor, login)

| Método | Ruta | Vista | name | Plantilla |
|--------|------|------|------|-----------|
| GET/POST | `/lessons/create/` | `create_standalone_lesson` | `create_standalone_lesson` | `public/standalone_lesson_form.html` |
| GET/POST | `/lessons/<slug>/edit/` | `edit_standalone_lesson` | `edit_standalone_lesson` | `public/standalone_lesson_form.html` |
| POST | `/lessons/<slug>/delete/` | `delete_standalone_lesson` | `delete_standalone_lesson` | `public/delete_standalone_lesson.html` |
| POST | `/lessons/<slug>/toggle-published/` | `toggle_lesson_published` | `toggle_lesson_published` | (json) |
| GET | `/lessons/<slug>/preview/` | `preview_lesson` | `preview_standalone_lesson` | `public/lesson_preview.html` |

## 6. Admin (is_staff)

| Método | Ruta | Vista | name | Plantilla |
|--------|------|------|------|-----------|
| GET | `/admin/` | `admin_dashboard` | `admin_dashboard` | `admin/dashboard.html` |
| GET | `/admin/users/` | `admin_users` | `admin_users` | `admin/users.html` |
| GET | `/admin/users/<id>/` | `admin_user_detail` | `admin_user_detail` | `admin/user_detail.html` |
| GET/POST | `/admin/users/<id>/edit/` | `edit_user` | `edit_user` | `admin/edit_user.html` |

## Estructura de plantillas

```
courses/templates/courses/
├── base.html                  (base compartida)
├── public/      home, course_list, course_detail, course_learning, docs,
│                public_content_blocks, public_content_detail, standalone_lessons_list,
│                standalone_lesson_detail, standalone_lesson_form, lesson_preview, delete_standalone_lesson
├── student/     dashboard, add_review, my_standalone_lessons
├── tutor/       manage_courses, course_form, course_wizard_step1/2, course_analytics,
│                delete_course, manage_content, module_form, module_statistics, module_progress,
│                modules_overview, bulk_module_actions, duplicate_module, delete_module, lesson_form,
│                delete_lesson, manage_categories, category_form, quick_create_category, delete_category
├── cms/         content_manager, content_block_form, content_block_preview(_public),
│                content_blocks_list, duplicate_content_block, delete_content_block
├── admin/       dashboard, users, user_detail, edit_user
└── components/  _course_card, _course_card_modern, _dashboard_stats, _empty_state,
                 _lesson_item, _management_indicator, _quick_actions, _review_item, _star_rating,
                 cms_base, conditional_sidebar, content_manager_*
```

## Estructura de vistas (paquete `courses/views/`)

- `public.py` — index, course_list, course_detail, courses_docs
- `student.py` — enroll, dashboard, course_learning, mark_lesson_complete, add_review, _handle_*
- `tutor.py` — gestión de cursos/módulos/lecciones/categorías
- `cms.py` — content_manager y bloques de contenido
- `standalone.py` — lecciones independientes
- `admin.py` — admin_dashboard, admin_users, admin_user_detail, edit_user
- `__init__.py` re-exporta todo (`from .X import *`)

## Migración ITCSS — progreso

### Completados
- `public/home.html` — base propia, sin Bootstrap
- `public/course_list.html`
- `public/course_detail.html`
- `student/dashboard.html`
- `public/course_learning.html`
- `public/public_content_blocks.html`
- `public/public_content_detail.html`
- `public/docs.html`
- `tutor/manage_courses.html`
- `tutor/course_form.html`
- `tutor/module_form.html`
- `tutor/category_form.html`
- `student/add_review.html` ← migrado 2026-07-18
- `public/delete_standalone_lesson.html` ← migrado 2026-07-18

### Pendientes (aún extienden `courses/base.html` / usan Bootstrap)
- `public/standalone_lesson_detail.html` (381 líneas, CSS inline + MathJax)
- `public/standalone_lessons_list.html` (882 líneas)
- `public/standalone_lesson_form.html` (2311 líneas)
- `public/lesson_preview.html` (496 líneas)
- `student/my_standalone_lessons.html` (464 líneas)
- `tutor/manage_content.html`
- `tutor/module_progress.html`
- `tutor/module_statistics.html`
- `tutor/modules_overview.html`
- `tutor/bulk_module_actions.html`
- `tutor/lesson_form.html`
- `tutor/course_wizard_step1.html`
- `tutor/course_wizard_step2.html`
- `tutor/course_analytics.html`
- `tutor/delete_course.html`
- `tutor/delete_module.html`
- `tutor/delete_lesson.html`
- `tutor/delete_category.html`
- `tutor/duplicate_module.html`
- `tutor/manage_categories.html`
- `tutor/quick_create_category.html`
- `admin/dashboard.html`
- `admin/users.html`
- `admin/user_detail.html`
- `admin/edit_user.html`
- `admin/notifications.html`
- `admin/courses_overview.html`

### Estrategia pendiente
1. Crear `base_itcss.html` (genérica para gestión/admin) — se usará como base de migración
2. Migrar templates por tamaño: primero públicos pequeños, luego tutor, luego admin
3. Mover estilos inline a `static/courses/css/components/` según corresponda
4. Validar HTTP 200 y anti-bootstrap en cada migración

Django resuelve de arriba abajo; la PRIMERA coincidencia gana. Por eso:
- Todas las rutas específicas (con palabra clave o `<int>`/`<str>`) van ANTES del patrón catch-all.
- `courses/docs/`, `courses/content/`, `courses/lessons/`, `courses/dashboard/`, `courses/manage/`, `courses/admin/` van ANTES de `courses/<slug:slug>/` (si no, el slug devoraría esas rutas).
- `lessons/my-lessons/`, `lessons/create/` y demás van ANTES de `lessons/<slug:slug>/`.
- El detalle de curso `<slug:slug>/` y sus sub-rutas (`learn/`) van al FINAL.
