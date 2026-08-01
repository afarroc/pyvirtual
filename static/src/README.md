# App Courses - Índice de URLs y Vistas

## Descripción General
La aplicación `courses` es un sistema completo de gestión de cursos en línea con funcionalidades para estudiantes, tutores y administradores.

## URLs Principales

### Páginas Públicas
- `/` - [`index`](views.py:21) - Página principal con estadísticas y cursos destacados
- `/category/<slug>/` - [`course_list`](views.py:72) - Lista de cursos por categoría
- `/courses/` - [`course_list`](views.py:72) - Catálogo completo de cursos

### URLs de Estudiantes
- `/dashboard/` - [`dashboard`](views.py:177) - Panel de control personal del estudiante
- `/<course_id>/enroll/` - [`enroll`](views.py:153) - Inscripción a un curso
- `/<slug>/` - [`course_detail`](views.py:117) - Detalle de un curso específico
- `/<slug>/learn/` - [`course_learning`](views.py:309) - Vista de aprendizaje del curso
- `/<slug>/learn/<lesson_id>/` - [`course_learning`](views.py:309) - Aprendizaje de lección específica
- `/lesson/<lesson_id>/complete/` - [`mark_lesson_complete`](views.py:414) - Marcar lección como completada
- `/<course_id>/review/` - [`add_review`](views.py:444) - Añadir reseña a un curso

### URLs de Tutores
- `/manage/` - [`manage_courses`](views.py:477) - Gestión de cursos del tutor
- `/manage/create/` - [`create_course`](views.py:509) - Crear nuevo curso
- `/manage/create/wizard/` - [`create_course_wizard`](views.py:528) - Asistente paso a paso para crear curso
- `/manage/<slug>/edit/` - [`edit_course`](views.py:586) - Editar curso existente
- `/manage/<slug>/delete/` - [`delete_course`](views.py:608) - Eliminar curso
- `/manage/<slug>/analytics/` - [`course_analytics`](views.py:667) - Analíticas del curso

#### Gestión de Contenido
- `/manage/<slug>/content/` - [`manage_content`](views.py:714) - Gestionar contenido del curso
- `/manage/<slug>/modules/create/` - [`create_module`](views.py:738) - Crear módulo
- `/manage/<slug>/modules/<module_id>/edit/` - [`edit_module`](views.py:761) - Editar módulo
- `/manage/<slug>/modules/<module_id>/delete/` - [`delete_module`](views.py:782) - Eliminar módulo
- `/manage/<slug>/modules/<module_id>/duplicate/` - [`duplicate_module`](views.py:800) - Duplicar módulo
- `/manage/<slug>/modules/<module_id>/statistics/` - [`module_statistics`](views.py:859) - Estadísticas del módulo
- `/manage/<slug>/modules/<module_id>/progress/` - [`module_progress`](views.py:929) - Progreso de estudiantes en módulo
- `/manage/<slug>/modules/bulk-actions/` - [`bulk_module_actions`](views.py:968) - Acciones masivas en módulos
- `/manage/<slug>/modules/reorder/` - [`reorder_modules`](views.py:839) - Reordenar módulos

#### Gestión de Lecciones
- `/manage/<slug>/modules/<module_id>/lessons/create/` - [`create_lesson`](views.py:1016) - Crear lección
- `/manage/<slug>/modules/<module_id>/lessons/<lesson_id>/edit/` - [`edit_lesson`](views.py:1074) - Editar lección
- `/manage/<course_slug>/modules/<module_id>/lessons/<lesson_id>/preview/` - [`preview_lesson`](views.py:2234) - Vista previa de lección
- `/manage/<slug>/modules/<module_id>/lessons/<lesson_id>/delete/` - [`delete_lesson`](views.py:1134) - Eliminar lección

### URLs de Administración
- `/manage/categories/` - [`manage_categories`](views.py:1154) - Gestionar categorías
- `/manage/categories/create/` - [`create_category`](views.py:1172) - Crear categoría
- `/manage/categories/quick-create/` - [`quick_create_category`](views.py:1217) - Crear categorías comunes rápidamente
- `/manage/categories/<category_id>/edit/` - [`edit_category`](views.py:1275) - Editar categoría
- `/manage/categories/<category_id>/delete/` - [`delete_category`](views.py:1299) - Eliminar categoría

- `/admin/` - [`admin_dashboard`](views.py:1327) - Panel de administración
- `/admin/users/` - [`admin_users`](views.py:1356) - Gestión de usuarios
- `/admin/users/<user_id>/` - [`admin_user_detail`](views.py:1395) - Detalle de usuario
- `/admin/users/<user_id>/edit/` - [`edit_user`](views.py:1415) - Editar usuario

### URLs del CMS (Content Management System)
- `/content/` - [`content_manager`](views.py:1440) - Panel principal del CMS
- `/content/create/<block_type>/` - [`create_content_block`](views.py:1527) - Crear bloque de contenido
- `/content/<slug>/edit/` - [`edit_content_block`](views.py:1679) - Editar bloque de contenido
- `/content/<slug>/delete/` - [`delete_content_block`](views.py:1825) - Eliminar bloque de contenido
- `/content/<slug>/duplicate/` - [`duplicate_content_block`](views.py:1938) - Duplicar bloque de contenido
- `/content/<slug>/preview/` - [`preview_content_block`](views.py:2005) - Vista previa de bloque
- `/content/my-blocks/` - [`my_content_blocks`](views.py:1845) - Mis bloques de contenido
- `/content/public/` - [`public_content_blocks`](views.py:1884) - Biblioteca pública
- `/content/featured/` - [`featured_content_blocks`](views.py:1927) - Bloques destacados
- `/content/<slug>/toggle-featured/` - [`toggle_block_featured`](views.py:1970) - Alternar destacado
- `/content/<slug>/toggle-public/` - [`toggle_block_public`](views.py:1987) - Alternar público

### URLs de Lecciones Independientes
- `/lessons/` - [`standalone_lessons_list`](views.py:2025) - Lista de lecciones independientes
- `/lessons/my-lessons/` - [`my_standalone_lessons`](views.py:2123) - Mis lecciones independientes
- `/lessons/create/` - [`create_standalone_lesson`](views.py:2140) - Crear lección independiente
- `/lessons/<slug>/` - [`standalone_lesson_detail`](views.py:2106) - Detalle de lección independiente
- `/lessons/<slug>/edit/` - [`edit_standalone_lesson`](views.py:2175) - Editar lección independiente
- `/lessons/<slug>/delete/` - [`delete_standalone_lesson`](views.py:2212) - Eliminar lección independiente
- `/lessons/<slug>/toggle-published/` - [`toggle_lesson_published`](views.py:2249) - Alternar publicación

## Índice de Herramientas y Funciones (Dashboard)

El dashboard principal ([`dashboard`](views.py:177)) incluye las siguientes herramientas organizadas por rol:

### Para Todos los Usuarios
1. **Explorar Cursos** - Ver catálogo completo de cursos disponibles
2. **Contenido Educativo** - Lecciones independientes, bloques y contenido gratuito
3. **Mis Cursos** - Cursos en los que estoy inscrito como estudiante

### Para Tutores
4. **Crear Curso** - Crear un nuevo curso desde cero
5. **Asistente de Cursos** - Crear curso paso a paso con wizard
6. **Gestionar Cursos** - Administrar mis cursos como tutor
7. **Categorías** - Gestionar categorías de cursos (solo admin)
8. **Módulos** - Vista general de módulos de mis cursos
9. **Gestor de Contenido** - CMS para crear bloques de contenido reutilizable

### Para Administradores
10. **Panel de Administración** - Panel administrativo completo
11. **Gestión de Usuarios** - Administrar usuarios del sistema

## Modelos Principales

- `CourseCategory` - Categorías de cursos
- `Course` - Cursos principales
- `Module` - Módulos dentro de cursos
- `Lesson` - Lecciones individuales
- `LessonAttachment` - Archivos adjuntos a lecciones
- `Enrollment` - Inscripciones de estudiantes
- `Progress` - Progreso de estudiantes en lecciones
- `Review` - Reseñas de cursos
- `ContentBlock` - Bloques de contenido reutilizable (CMS)

## Permisos y Roles

- **Estudiantes**: Pueden inscribirse, aprender y dejar reseñas
- **Tutores**: Pueden crear y gestionar cursos, lecciones y contenido
- **Administradores**: Acceso completo a gestión de usuarios y categorías

## Notas Técnicas

- Todas las vistas requieren autenticación donde corresponda
- Se utilizan decoradores `@login_required` y `@require_POST`
- Optimización de consultas con `select_related` y `prefetch_related`
- Soporte para AJAX en operaciones críticas
- Sistema de permisos basado en perfiles de usuario (CV requerido para tutores)