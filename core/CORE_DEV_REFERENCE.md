# Referencia de Desarrollo — App `core`

> **Actualizado:** 2026-03-19  
> **Audiencia:** Desarrolladores y asistentes IA  
> **Archivos:** 45 | **Vistas:** 1 archivo (379 líneas) | **Utils:** 379 líneas | **Templates:** 36 | **Endpoints:** 16  
> **Migraciones:** `0001_initial`, `0002_alter_article_options_...`

---

## Índice

| Sección | Contenido |
|---------|-----------|
| 1. Resumen | Qué hace esta app y sus pilares |
| 2. Modelos | `Article` |
| 3. Vistas | Dashboard, páginas estáticas, AJAX, búsqueda, url-map |
| 4. Utils | Funciones de caché, estadísticas y URL parser |
| 5. URLs | Mapa completo de endpoints |
| 6. Templates | Estructura de layouts globales |
| 7. Convenciones críticas | Gotchas, dependencias, patrones |
| 8. Bugs conocidos | Issues activos |
| 9. Deuda técnica | Clasificada por prioridad |

---

## 1. Resumen

`core` es la **app de infraestructura global** de Management360. No gestiona ningún dominio de negocio específico — su función es proveer la capa que sostiene todo el proyecto:

- **Dashboard principal** — home con estadísticas agregadas de `events` (eventos, proyectos, tareas), con filtro temporal dinámico y caché Redis
- **Layouts y navegación global** — `base.html`, `sidebar.html`, `header.html` y todos los fragmentos de nav por app (`nav-content/`)
- **Búsqueda global** — cross-app sobre Articles, Events, Projects, Tasks
- **URL Map** — introspección dinámica del proyecto: lee y parsea todos los `urls.py` del filesystem para renderizar un mapa navegable en `/url-map/`
- **Páginas estáticas** — about, contact, FAQ, GTD guide, blank
- **Modelo `Article`** — contenido editorial simple (publicaciones del sitio)
- **AJAX del dashboard** — endpoints para paginación lazy de actividades, items recientes y categorías

Sus dos pilares técnicos son `views.py` (16 endpoints) y `utils.py` (7 funciones de lógica de negocio + 3 de URL parsing).

---

## 2. Modelos

### `Article`

Modelo simple para contenido editorial del sitio. No tiene autor (`created_by`) ni relación con `accounts.User`.

```python
class Article(models.Model):
    title            # CharField(200) — obligatorio
    content          # TextField — obligatorio
    excerpt          # CharField(300) — opcional, default=""
    publication_date # DateTimeField(auto_now_add=True) — no editable
    is_published     # BooleanField(default=True)

    class Meta:
        ordering = ['-publication_date']
```

**Métodos:**

| Método | Descripción |
|--------|-------------|
| `__str__()` | Retorna `self.title` |
| `get_absolute_url()` | Reverse de `'article_detail'` — ⚠️ ver bug B1 |
| `get_excerpt_display()` | Retorna `excerpt` si existe; si no, trunca `content[:150] + "..."` |

**⚠️ Violaciones de convención del proyecto:**
- Sin `id = UUIDField(primary_key=True)` — usa `BigAutoField` (int) del `default_auto_field` de `CoreConfig`
- Sin `created_by` (no tiene propietario)
- Sin `updated_at` — solo tiene `publication_date` (auto_now_add, equivalente a `created_at`)
- Sin `is_active` para soft delete

**Admin registrado** en `admin.py` con `ArticleAdmin`: list_display, list_filter, search, list_editable para `is_published`, date_hierarchy, fieldsets.

---

## 3. Vistas

### `home_view` — Dashboard principal

```python
@login_required
def home_view(request, days=None, days_ago=None):
```

| Aspecto | Detalle |
|---------|---------|
| URLs | `/` · `/<int:days>/` · `/<int:days>/<int:days_ago>/` |
| Auth | `@login_required` |
| Template | `home/home.html` |

**Parámetros de tiempo:**
- `days` (default 30, rango 1–365): ventana de tiempo hacia atrás desde hoy
- `days_ago`: si se provee, desplaza la ventana — el período va desde `(now - days_ago)` hasta `(now - days_ago + days)`

**Contexto completo:**

| Clave | Fuente | Contenido |
|-------|--------|-----------|
| `days`, `days_ago`, `start_date`, `end_date` | `validate_time_parameters()` | Período activo |
| `total_events`, `events_in_period` | `get_cached_basic_stats()` | Totales globales + en período |
| `total_projects`, `projects_in_period` | `get_cached_basic_stats()` | Ídem |
| `total_tasks`, `tasks_in_period` | `get_cached_basic_stats()` | Ídem |
| `completed_events`, `active_projects`, `pending_tasks`, etc. | `get_cached_status_counts()` | Por estado |
| `recent_activities` | `get_recent_activities()` | Lista de `LogEntry` (últimas 10) |
| `upcoming_events` | `get_recent_items()` | Queryset de próximos eventos |
| `recent_projects_list` | `get_recent_items()` | Últimos 5 proyectos por `updated_at` |
| `recent_tasks` | `get_recent_items()` | Últimas 5 tareas por `updated_at` |
| `event_categories` | `get_cached_categories()` | Lista de dicts `{event_category, count}` |
| `project_categories` | `get_cached_categories()` | Queryset de `Classification` |
| `alerts` | `generate_home_alerts()` | Lista de dicts de alertas inteligentes |
| `profile_completion` | Hardcoded | `50` — placeholder sin implementar |

⚠️ `upcoming_events` se calcula con `created_at__gte=timezone.now()` — filtra eventos cuya fecha de **creación** es futura, no su fecha de inicio. Bug semántico (ver B3).

⚠️ `log_info` con `validate_time_parameters(days, days_ago)` es llamado **dos veces** — una para logging y otra para obtener los valores. Llamada redundante.

---

### Páginas estáticas

Todas sin `@login_required`, sin estado, sin forms.

| Vista | URL | Template | Contexto notable |
|-------|-----|----------|-----------------|
| `about_view` | `/about/` | `about/about.html` | `page_title` |
| `contact_view` | `/contact/` | `contact/contact.html` | `page_title` |
| `faq_view` | `/faq/` | `faq/faq.html` | `page_title` |
| `gtd_guide_view` | `/gtd-guide/` | `docs/gtd_guide.html` | `page_title`, `title`, `subtitle` |
| `blank_view` | `/blank/` | `blank/blank.html` | `page_title`, `message` |

---

### AJAX endpoints

Los endpoints GET usan `@require_GET` + `@login_required`. `refresh_dashboard_data` usa `@require_POST` + `@login_required`.

#### `load_more_activities` — `/api/activities/more/`

Paginación de `django.contrib.admin.models.LogEntry` filtrado por ContentTypes de Event/Project/Task.

| Param GET | Default | Máx |
|-----------|---------|-----|
| `offset` | 10 | — |
| `limit` | 10 | 50 |

Respuesta: `{success, activities: [{content_type, action, user, timestamp, object_repr, badge_color}], has_more}`

---

#### `load_more_recent_items` — `/api/items/<str:item_type>/more/`

Tipos válidos: `'projects'`, `'tasks'`, `'events'`. Cualquier otro retorna 400.

| Param GET | Default | Máx |
|-----------|---------|-----|
| `offset` | 5 | — |
| `limit` | 5 | 20 |

⚠️ La rama `'events'` usa `created_at__gte=timezone.now()` — mismo bug semántico que en `home_view` (ver B3).

---

#### `load_more_categories` — `/api/categories/<str:category_type>/more/`

Tipos válidos: `'events'` (agrupa por `event_category`), `'projects'` (lista `Classification`).

La rama `'projects'` tiene un `except: pass` desnudo — traga cualquier excepción silenciosamente.

---

#### `refresh_dashboard_data` — `/api/dashboard/refresh/`

```python
@require_POST
@login_required
```

`data_type` acepta: `'all'`, `'stats'`, `'status_counts'`, `'activities'`.

---

#### `get_dashboard_stats` — `/api/dashboard/stats/`

`@require_GET` + `@login_required`. Devuelve stats básicas + por estado + derivadas (total_items, completion_rate).

Estructura de respuesta:
```json
{
  "success": true,
  "stats": {
    "basic": {...},
    "status": {...},
    "derived": {"total_items": 42, "completion_rate": 71.43}
  },
  "timestamp": "2026-03-19T..."
}
```

---

### `search_view` — `/search/`

Tiene `@login_required`. Busca simultáneamente en `Article`, `Event`, `Project`, `Task` con `Q(field__icontains=query)`.

Campos buscados por modelo:

| Modelo | Campos |
|--------|--------|
| `Article` | `title`, `content`, `excerpt` |
| `Event` | `title`, `description`, `venue`, `event_category` |
| `Project` | `title`, `description` |
| `Task` | `title`, `description` |

Sin paginación — devuelve todos los resultados. Potencial problema de performance con datasets grandes.

---

### `url_map_view` — `/url-map/`

Sin auth. Dos modos:
- Sin `?app_name=`: llama `get_all_apps_url_structure()` → renderiza `core/url_map.html`
- Con `?app_name=X`: llama `get_app_url_structure(X)` → renderiza `core/url_map_detail.html`

---

## 4. Utils (`utils.py`)

### `validate_time_parameters(days, days_ago)`

Sanitiza y convierte parámetros temporales. `days` fuera de rango `(0, 365]` → default 30. Retorna `(days, days_ago, start_date, end_date)` como `datetime` con timezone.

---

### `get_cached_basic_stats(start_date, end_date, days, days_ago)` → dict

**Cache key:** `home_stats_{days}_{days_ago or 0}` | **TTL:** 300s (5 min)

Ejecuta 3 queries `aggregate(Count)` sobre Event, Project, Task. Retorna totales globales + conteos en el período.

---

### `get_cached_status_counts()` → dict

**Cache key:** `home_status_counts` | **TTL:** 600s (10 min)

Busca status por `status_name` exacto: `'Completed'`, `'In Progress'`, `'Created'`, `'To Do'`. Si alguno no existe en BD retorna 0 silenciosamente. Envuelto en `try/except` — fallo total retorna dict de ceros.

⚠️ **Dependencia frágil de strings hardcodeados** — si alguien renombra un `Status` en la BD, los conteos caen a 0 sin error visible.

---

### `get_recent_activities()` → list

Lee `LogEntry` (Django Admin log) de Event/Project/Task. Retorna lista de dicts con `content_type`, `action`, `user` (objeto), `timestamp`, `object_repr`, `get_badge_color`.

⚠️ Solo registra actividades del **Admin de Django**, no acciones desde la UI de M360.

---

### `get_recent_items()` → dict

Retorna querysets (no evaluados): `upcoming_events` (5), `recent_projects_list` (5), `recent_tasks` (5). Usa `select_related` correctamente.

⚠️ `upcoming_events` filtra `created_at__gte=timezone.now()` — bug semántico (ver B3).

---

### `get_cached_categories()` → dict

**Cache keys:** `home_event_categories` (TTL 900s) · `home_project_categories` (TTL 1800s)

Event categories: lista de dicts `{event_category, count}` — top 10 por frecuencia.  
Project categories: lista de objetos `Classification` — top 10.

Import de `Classification` es lazy (dentro de la función) — patrón inconsistente con el resto.

---

### `generate_home_alerts(user, stats)` → list[dict]

Genera alertas inteligentes basadas en umbrales. Cada alerta: `{type, icon, title, message, action_url, action_text}`.

| Condición | Tipo | Umbral |
|-----------|------|--------|
| Sin eventos ni proyectos | `info` | `total_events == 0 and total_projects == 0` |
| Alta actividad reciente | `success` | `recent_activities > 5` |
| Eventos próximos | `warning` | `upcoming_events > 0` |
| Backlog de tareas | `danger` | `pending_tasks > 10` |
| Baja actividad | `warning` | `recent_activities == 0` con datos existentes |

⚠️ `action_url` está **hardcodeado** con rutas absolutas (`'/events/events/create/'`, etc.) — no usa `reverse()` ni `{% url %}`. Frágil ante cambios de URL.

⚠️ El parámetro `user` se recibe pero **nunca se usa** dentro de la función.

---

### `get_all_apps_url_structure()` → list

Itera sobre `_get_local_apps()` y llama `get_app_url_structure()` para cada una. Devuelve lista de dicts con `name`, `type`, `url_count`, `urls`.

---

### `get_app_url_structure(app_name)` → dict | None

Lee el archivo `{BASE_DIR}/{app_name}/urls.py` del filesystem y lo parsea con regex. No importa ni ejecuta código Python — análisis estático puro.

Retorna `{app_name, urls_file, urls: [...]}` o `{app_name, error, urls: []}`.

---

### `parse_urlpatterns(content, app_name)` → list

Parsea `path()` y `re_path()` con regex. Por cada match retorna `{pattern, view, type, full_pattern}`.

⚠️ El regex de `path()` es simple — no maneja correctamente llamadas multilínea complejas ni `include()`. Suficiente para el URL Map pero no apto para análisis profundo.

---

### `_build_full_pattern(url_pattern, app_name)` → str

Construye el path completo con prefijo de app. Helper interno.

---

### `_get_local_apps()` → set[str]

Combina apps de `INSTALLED_APPS` (excluye `django.*`) con directorios del filesystem (excluye `static`, `media`, `templates`, `__pycache__`). Retorna set ordenado.

---

## 5. URLs

> **⚠️ Violación de convención:** `core` **NO declara `app_name`** en `urls.py`. Sin namespace declarado.

> **Nota de deuda:** `'home'` e `'index'` apuntan al mismo `path('')`. Se mantienen ambos names porque el proyecto usa `{% url 'index' %}` masivamente y además existen `redirect('home')`, `LOGIN_REDIRECT_URL='home'` y templates con `{% url 'home' %}`. Eliminar cualquiera sin migración completa rompe navegación y login.

| URL | Name | Vista | Auth | Método |
|-----|------|-------|------|--------|
| `/` | `home` / `index` | `home_view` | ✅ | GET |
| `/about/` | `about` | `about_view` | ❌ | GET |
| `/contact/` | `contact` | `contact_view` | ❌ | GET |
| `/faq/` | `faq` | `faq_view` | ❌ | GET |
| `/gtd-guide/` | `gtd_guide` | `gtd_guide_view` | ❌ | GET |
| `/blank/` | `blank` | `blank_view` | ❌ | GET |
| `/<int:days>/` | `home_by_days` | `home_view` | ✅ | GET |
| `/<int:days>/<int:days_ago>/` | `home_by_days_range` | `home_view` | ✅ | GET |
| `/search/` | `search` | `search_view` | ✅ | GET |
| `/url-map/` | `url_map` | `url_map_view` | ❌ | GET |
| `/api/activities/more/` | `load_more_activities` | `load_more_activities` | ✅ | GET |
| `/api/items/<str:item_type>/more/` | `load_more_recent_items` | `load_more_recent_items` | ✅ | GET |
| `/api/categories/<str:category_type>/more/` | `load_more_categories` | `load_more_categories` | ✅ | GET |
| `/api/dashboard/refresh/` | `refresh_dashboard_data` | `refresh_dashboard_data` | ✅ | POST |
| `/api/dashboard/stats/` | `dashboard_stats` | `get_dashboard_stats` | ✅ | GET |

---

## 6. Templates — Estructura de Layouts

`core` es propietario de los **layouts globales** que heredan todos los templates del proyecto.

```
templates/layouts/
├── base.html              ← template padre de todo el proyecto (174 líneas)
├── header.html            ← barra superior (191 líneas)
├── sidebar.html           ← navegación lateral (92 líneas)
├── mask.html              ← overlay/loading (44 líneas)
└── includes/
    Bootstrap removido del stack cargado por `core`.`core/templates/layouts/base.html` ya no incluye `bootstrap.min.css`, `bootstrap.bundle.min.js`, icon packs ni `main.js`. Quedan clases y helpers Bootstrap en templates y JS como deuda técnica para migrar por app sin romper layouts.
    ├── disabled_link.html ← link deshabilitado con tooltip
    ├── header/
    │   └── credit.html    ← widget de créditos del usuario
    └── nav-content/       ← fragmentos de nav por app (16 archivos)
        ├── account.html
        ├── analyst.html   ← 146 líneas — el más complejo
        ├── chat.html
        ├── configuration.html
        ├── courses.html
        ├── curriculum.html
        ├── dashboard.html
        ├── events.html
        ├── help.html
        ├── kpis.html
        ├── management.html ← 143 líneas
        ├── pages.html
        ├── projects.html
        ├── rooms.html
        ├── tasks.html
        └── tools.html
```

**Regla clave:** cualquier nueva app que necesite entrada en la navegación debe agregar su fragmento en `templates/layouts/includes/nav-content/` e incluirlo en `sidebar.html` o `header.html`.

**`home.html` es el template más grande del proyecto** — 1131 líneas. Incluye el dashboard completo con gráficos, tablas y widgets.

---

## 7. Convenciones Críticas

### `'index'` y `'home'` son el mismo endpoint

```python
# urls.py — ambos resuelven al mismo path '/'
path('', views.home_view, name='home'),
path('', views.home_view, name='index'),

# En templates y redirects del proyecto se usa 'index':
return redirect('index')          # accounts/views.py
{% url 'index' %}                  # múltiples templates
```

Nunca cambiar ni eliminar el name `'index'` sin buscar todos sus usos en el proyecto.

### Caché del dashboard — prefijos y TTLs

| Cache key | TTL | Función |
|-----------|-----|---------|
| `home_stats_{days}_{days_ago}` | 5 min | `get_cached_basic_stats()` |
| `home_status_counts` | 10 min | `get_cached_status_counts()` |
| `home_event_categories` | 15 min | `get_cached_categories()` |
| `home_project_categories` | 30 min | `get_cached_categories()` |

Para forzar refresco de stats en desarrollo: `cache.clear()` en shell o usar `/api/dashboard/refresh/`.

### Dependencia directa con `events`

`core` importa directamente desde `events`:
```python
# utils.py
from events.models import Event, Project, Task, Status, ProjectStatus, TaskStatus

# views.py
from events.models import Event, Project, Task
```

`core` no puede funcionar sin `events`. En el orden de migraciones, `events` debe estar aplicada antes que cualquier operación que ejecute código de `core`.

### Status names son strings hardcodeados

```python
# utils.py — get_cached_status_counts()
Status.objects.filter(status_name__in=['Completed', 'In Progress', 'Created'])
ProjectStatus.objects.filter(status_name__in=['Completed', 'In Progress'])
TaskStatus.objects.filter(status_name__in=['Completed', 'In Progress', 'To Do'])
```

Si estos nombres cambian en la BD (desde el admin), los conteos del dashboard caen a 0 silenciosamente. No rompe — simplemente muestra ceros.

### URL Map — análisis estático, no dinámico

`get_app_url_structure()` lee archivos del filesystem con regex. No carga ni importa los módulos Python. Ventaja: no hay riesgo de side effects. Desventaja: no maneja `include()` ni patterns complejos.

### `@csrf_exempt` en `refresh_dashboard_data` — no replicar

Este patrón está **prohibido** por convención del proyecto. El endpoint funciona, pero es una excepción no documentada que debe corregirse.

---

## 8. Bugs Conocidos

| # | Estado | Descripción |
|---|--------|-------------|
| B1 | ⬜ activo | `Article.get_absolute_url()` hace reverse de `'article_detail'` — URL que **no existe** en `urls.py`; llamarla lanza `NoReverseMatch` |
| B2 | ⬜ activo | `app_name` no declarado en `urls.py` — sin namespace propio |
| B3 | ⬜ activo | `upcoming_events` filtrado por `created_at__gte=now()` en lugar de campo de fecha de inicio del evento — semánticamente incorrecto |
| B4 | ✅ cerrado | `refresh_dashboard_data` tenía `@csrf_exempt` en endpoint POST autenticado — corregido |
| B5 | ⬜ activo | `home_view` llama `validate_time_parameters(days, days_ago)` dos veces (una para log, otra para uso) — query redundante |
| B6 | ⬜ activo | `generate_home_alerts(user, stats)` recibe `user` pero nunca lo usa — parámetro muerto |
| B7 | ⬜ activo | `action_url` en `generate_home_alerts()` hardcodeado con strings de URL — no usa `reverse()` |
| B8 | ⬜ activo | `load_more_categories` rama `'projects'` tiene `except: pass` desnudo — traga excepciones silenciosamente |
| B9 | ✅ cerrado | `search_view` sin `@login_required` — corregido |
| B10 | ⬜ activo | `url_map_view` sin `@login_required` — expone arquitectura interna del proyecto públicamente |
| B11 | ⬜ activo | `profile_completion: 50` hardcodeado en contexto de `home_view` — placeholder nunca implementado |
| B12 | ⬜ activo | `Article` no tiene `created_by`, `updated_at`, ni UUID pk — fuera de convenciones del proyecto |
| B13 | ⬜ activo | Dos names (`'home'` e `'index'`) para el mismo path `''` — ambigüedad en routing |

---

## 9. Deuda Técnica

**Alta prioridad:**
- **Corregir `upcoming_events`** — cambiar `created_at__gte` por el campo de fecha de inicio real de `Event` (verificar migración de `events`)
- **Proteger `url_map_view`** con `@login_required` — actualmente expone arquitectura a usuarios anónimos
- **Corregir `Article.get_absolute_url()`** — registrar URL `'article_detail'` o cambiar el reverse

**Media prioridad:**
- **Declarar `app_name = 'core'`** en `urls.py`
- **Resolución controlada de `'home'`/`index`** — requiere migrar `redirect('home')`, `LOGIN_REDIRECT_URL`, templates y rutas hermanas; no es seguro quitar uno sin migración completa
- **Reemplazar strings hardcodeados de status** en `get_cached_status_counts()` por constantes o referencias a PKs para evitar dependencia frágil de nombres
- **`generate_home_alerts`** — usar `reverse()` para `action_url` y eliminar parámetro `user` si no se usa
- **Paginación en `search_view`** — sin límite puede devolver cientos de resultados

**Baja prioridad:**
- **Eliminar llamada doble** a `validate_time_parameters()` en `home_view`
- **`profile_completion`** — implementar cálculo real basado en campos de `accounts.User` (avatar, phone, etc.)
- **`except: pass`** en `load_more_categories` → al menos loguear el error
- **`Article`** — decidir si es un modelo de contenido editorial real (y documentarlo) o un placeholder (y eliminarlo)
- **Tests** — `test_performance.py` (249 líneas) existe pero no se subió; verificar cobertura actual
