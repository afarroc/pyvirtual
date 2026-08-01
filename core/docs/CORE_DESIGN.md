# Diseño y Roadmap — App `core`

> **Actualizado:** 2026-03-19  
> **Estado:** Funcional en producción — documentación generada esta sesión  
> **Sprint actual:** 7 completado | Próximo: Sprint 8

---

## Visión General

`core` es la **app de infraestructura** de Management360. No pertenece a ningún dominio de negocio — es la capa transversal que conecta todo el proyecto: layouts globales, dashboard principal, búsqueda, introspección de URLs y páginas estáticas.

A diferencia de todas las demás apps, `core` no tiene un dominio propio — su razón de ser es **servir a todas las demás apps**.

```
┌──────────────────────────────────────────────────────────┐
│                       APP CORE                           │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  LAYOUTS GLOBALES (base.html, sidebar, header, nav) │ │
│  │  → heredados por los ~150 templates del proyecto    │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Dashboard   │  │  Búsqueda    │  │   URL Map     │  │
│  │  /           │  │  global      │  │  introspección│  │
│  │  estadísticas│  │  cross-app   │  │  del proyecto │  │
│  │  + alertas   │  │              │  │               │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────────────────────────┐  │
│  │   Article    │  │   Páginas estáticas              │  │
│  │   (editorial)│  │   about / contact / faq / gtd    │  │
│  └──────────────┘  └──────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
         │
         │ importa directamente de:
         ▼
    events.{Event, Project, Task, Status, ProjectStatus, TaskStatus}
```

---

## Estado de Implementación

| Módulo | Estado | Observaciones |
|--------|--------|---------------|
| Layouts globales (`base.html`, `sidebar`, `header`) | ✅ Completo | 16 fragmentos de nav por app |
| Dashboard principal (`home_view`) | ✅ Funcional | Caché Redis, filtro temporal, alertas |
| AJAX paginación (activities, items, categories) | ✅ Funcional | 4 endpoints |
| Búsqueda global (`search_view`) | ⚠️ Funcional con bugs | Sin auth, sin paginación |
| URL Map (`url_map_view`) | ✅ Funcional | Parser regex estático, sin auth |
| Páginas estáticas (about, contact, faq, etc.) | ✅ Completo | Sin auth requerida |
| Modelo `Article` | ⚠️ Parcial | `get_absolute_url()` apunta a URL inexistente |
| Admin de `Article` | ✅ Completo | `ArticleAdmin` con fieldsets |
| `utils.py` — estadísticas y caché | ✅ Funcional | Dependencia frágil de status names |
| `utils.py` — URL parser | ✅ Funcional | Regex simple, suficiente para el caso de uso |
| Tests (`test_performance.py`) | ⚠️ Desconocido | 249 líneas — cobertura no verificada |
| Documentación | ✅ Esta sesión | Primera documentación formal |

---

## Arquitectura de Datos

### Dependencias de `core` con otras apps

```
core
  └── events (importación directa en utils.py y views.py)
        ├── Event
        ├── Project
        ├── Task
        ├── Status
        ├── ProjectStatus
        ├── TaskStatus
        └── Classification (import lazy en get_cached_categories)

core ←── TODAS las apps del proyecto
          (heredan layouts de core/templates/layouts/)
```

`core` es **dependiente de `events`** (importación directa) y **proveedor de layouts** para todas las apps. Este acoplamiento es intencional y estructural.

### Modelo `Article` — posición en el proyecto

`Article` es un modelo huérfano. No tiene autor, no se referencia desde ninguna otra app, y su única vista es `search_view` (que sí lo busca). `get_absolute_url()` apunta a una URL inexistente. Su función actual es servir como contenido editorial del sitio (FAQ, notas) pero está sin integración real.

### Sistema de caché del dashboard

```
Redis
  ├── home_stats_{days}_{days_ago or 0}     TTL  5 min
  ├── home_status_counts                    TTL 10 min
  ├── home_event_categories                 TTL 15 min
  └── home_project_categories               TTL 30 min
```

No hay invalidación activa de caché — los datos se actualizan solo por expiración natural o por `POST /api/dashboard/refresh/`.

---

## Roadmap

### Deuda inmediata (pre-Sprint 8)

| ID | Tarea | Prioridad |
|----|-------|-----------|
| CORE-1 | Corregir `upcoming_events`: cambiar `created_at__gte` por campo de fecha real de `Event.start_date` | 🔴 |
| CORE-2 | ~~Agregar `@login_required` a `search_view`~~ → completada | ✅ |
| CORE-3 | ~~Eliminar `@csrf_exempt` de `refresh_dashboard_data`~~ → completada | ✅ |
| CORE-4 | Corregir `Article.get_absolute_url()` — reverse `'article_detail'` no existe | 🟠 |
| CORE-5 | Agregar `@login_required` a `url_map_view` — expone arquitectura del proyecto | 🟠 |
| CORE-10 | Duplicidad `'home'`/`'index'` en `core/urls.py` — se mantiene por compatibilidad hasta migración completa | 🟡 |

### Sprint 8

| ID | Tarea | Prioridad |
|----|-------|-----------|
| CORE-6 | Declarar `app_name = 'core'` en `urls.py` | 🟠 |
| CORE-7 | Reemplazar strings hardcodeados de status en `get_cached_status_counts()` por constantes | 🟠 |
| CORE-8 | `generate_home_alerts()` — usar `reverse()` para `action_url`, eliminar parámetro `user` muerto | 🟠 |
| CORE-9 | Paginación en `search_view` | 🟡 |
| CORE-10 | Resolver duplicidad `'home'`/`'index'` en urls.py | 🟡 |

### Sprint 9

| ID | Tarea | Prioridad |
|----|-------|-----------|
| CORE-11 | Implementar `profile_completion` real basado en campos de `accounts.User` | 🟡 |
| CORE-12 | Alinear `Article` a convenciones del proyecto (UUID pk, `created_by`, `updated_at`) o eliminarlo | 🟡 |
| CORE-13 | Invalidación activa de caché cuando se crean/modifican Events/Projects/Tasks (signals) | 🟡 |
| CORE-14 | Eliminar `except: pass` en `load_more_categories` — agregar logging | 🟡 |

---

## Notas para Claude
- **Bootstrap removido desde `core`** — se eliminó la carga global de `vendor/bootstrap`, icon packs y `main.js` desde `base.html`. Quedan muchas clases Bootstrap en templates, CSS inline y JS como deuda controlada; resolverla por app, no en bloque.
- **Base ITCSS M360 activa** — `core/templates/layouts/base.html` ahora carga `static/m360/css/...` (tokens/base/utilities/components/layout/sections/index) como sistema de diseño principal. Seguir este orden al introducir nuevos estilos de `core`.
- **Header M360 migrado** — `core/templates/layouts/header.html` se migró a clases ITCSS `.m360-site-header`, `.m360-dropdown`, `.m360-btn`, `.m360-badge`; los icons legacy quedaron como placeholders Unicode pendientes de migrar.
- **Iconos pendientes** — `core/header.html` usa placeholders Unicode porque se removieron Bootstrap Icons. Documentado como deuda separada: migrar a icon set propio o SVG inline antes de extender a más apps.
- **Deuda Bootstrap/NiceAdmin remanente en `core`** — Quedan referencias en `core/templates/home/home.html`, `core/templates/search/search.html`, `core/templates/layouts/includes/alert.html` y `core/templates/base.html` (alerts/inline close). No se están tocando en este paso para no bloquear el avance; resolver en pasos siguientes por template.
- **`'index'` y `'home'` son el mismo endpoint** — en redirects y templates del proyecto se usa `'index'`. `'home'` también está ampliamente referenciado; no eliminar ningún name sin migrar también `redirect('home')`, `LOGIN_REDIRECT_URL='home'` y los templates que usan `{% url 'home' %}`.
- **`core` depende de `events`** — import directo en `utils.py` y `views.py`. Si `events` no existe o falla migración, `core` no arranca
- **`upcoming_events` es un bug semántico** — filtra por `created_at__gte=now()`, no por fecha de inicio del evento. Cualquier query con ese nombre en templates o JS devuelve datos incorrectos
- **`@csrf_exempt` en `refresh_dashboard_data`** — existe pero está prohibido; no replicar en nuevos endpoints
- **Status names hardcodeados** — `'Completed'`, `'In Progress'`, `'To Do'`, `'Created'` deben existir exactamente con esos nombres en la BD para que el dashboard muestre conteos correctos
- **URL Map es análisis estático** — `get_app_url_structure()` lee archivos del disco con regex, no importa Python. No puede resolver `include()` ni patterns dinámicos
- **Layouts en `core/templates/layouts/`** — son los templates base de todo el proyecto. Modificar `base.html` o `sidebar.html` afecta todas las apps. Cualquier nueva app necesita su fragmento en `nav-content/`
- **`Article.get_absolute_url()`** lanza `NoReverseMatch` si se llama — no llamarla hasta que exista la URL `'article_detail'`
- **`home.html` tiene 1131 líneas** — el template más grande del proyecto. Editar con precaución
