# Mapa de Contexto — App `core`

> Generado por `m360_map.sh`  |  2026-03-19 18:15:43
> Ruta: `/data/data/com.termux/files/home/projects/Management360/core`  |  Total archivos: **45**

---

## Índice

| # | Categoría | Archivos |
|---|-----------|----------|
| 1 | 👁 `views` | 1 |
| 2 | 🎨 `templates` | 36 |
| 3 | 🗃 `models` | 1 |
| 4 | 🔗 `urls` | 1 |
| 5 | 🛡 `admin` | 1 |
| 6 | 🧪 `tests` | 1 |
| 7 | 📄 `other` | 4 |

---

## Archivos por Categoría


### VIEWS (1 archivos)

| Archivo | Líneas | Ruta relativa |
|---------|--------|---------------|
| `views.py` | 379 | `views.py` |

### TEMPLATES (36 archivos)

| Archivo | Líneas | Ruta relativa |
|---------|--------|---------------|
| `about.html` | 111 | `templates/about/about.html` |
| `about_old_panda.html` | 112 | `templates/about/about_old_panda.html` |
| `blank.html` | 48 | `templates/blank/blank.html` |
| `contact.html` | 94 | `templates/contact/contact.html` |
| `url_map.html` | 331 | `templates/core/url_map.html` |
| `url_map_detail.html` | 438 | `templates/core/url_map_detail.html` |
| `gtd_guide.html` | 695 | `templates/docs/gtd_guide.html` |
| `faq.html` | 476 | `templates/faq/faq.html` |
| `home.html` | 1131 | `templates/home/home.html` |
| `base.html` | 174 | `templates/layouts/base.html` |
| `header.html` | 191 | `templates/layouts/header.html` |
| `alert.html` | 14 | `templates/layouts/includes/alert.html` |
| `disabled_link.html` | 24 | `templates/layouts/includes/disabled_link.html` |
| `credit.html` | 47 | `templates/layouts/includes/header/credit.html` |
| `info_acordeon.html` | 19 | `templates/layouts/includes/information/info_acordeon.html` |
| `info_links.html` | 18 | `templates/layouts/includes/information/info_links.html` |
| `info_links_card.html` | 14 | `templates/layouts/includes/information/info_links_card.html` |
| `account.html` | 39 | `templates/layouts/includes/nav-content/account.html` |
| `analyst.html` | 146 | `templates/layouts/includes/nav-content/analyst.html` |
| `chat.html` | 17 | `templates/layouts/includes/nav-content/chat.html` |
| `configuration.html` | 33 | `templates/layouts/includes/nav-content/configuration.html` |
| `courses.html` | 61 | `templates/layouts/includes/nav-content/courses.html` |
| `curriculum.html` | 41 | `templates/layouts/includes/nav-content/curriculum.html` |
| `dashboard.html` | 5 | `templates/layouts/includes/nav-content/dashboard.html` |
| `events.html` | 67 | `templates/layouts/includes/nav-content/events.html` |
| `help.html` | 21 | `templates/layouts/includes/nav-content/help.html` |
| `kpis.html` | 24 | `templates/layouts/includes/nav-content/kpis.html` |
| `management.html` | 143 | `templates/layouts/includes/nav-content/management.html` |
| `pages.html` | 35 | `templates/layouts/includes/nav-content/pages.html` |
| `projects.html` | 61 | `templates/layouts/includes/nav-content/projects.html` |
| `rooms.html` | 36 | `templates/layouts/includes/nav-content/rooms.html` |
| `tasks.html` | 74 | `templates/layouts/includes/nav-content/tasks.html` |
| `tools.html` | 6 | `templates/layouts/includes/nav-content/tools.html` |
| `mask.html` | 44 | `templates/layouts/mask.html` |
| `sidebar.html` | 92 | `templates/layouts/sidebar.html` |
| `search.html` | 137 | `templates/search/search.html` |

### MODELS (1 archivos)

| Archivo | Líneas | Ruta relativa |
|---------|--------|---------------|
| `models.py` | 54 | `models.py` |

### URLS (1 archivos)

| Archivo | Líneas | Ruta relativa |
|---------|--------|---------------|
| `urls.py` | 30 | `urls.py` |

### ADMIN (1 archivos)

| Archivo | Líneas | Ruta relativa |
|---------|--------|---------------|
| `admin.py` | 22 | `admin.py` |

### TESTS (1 archivos)

| Archivo | Líneas | Ruta relativa |
|---------|--------|---------------|
| `test_performance.py` | 249 | `tests/test_performance.py` |

### OTHER (4 archivos)

| Archivo | Líneas | Ruta relativa |
|---------|--------|---------------|
| `CORE_CONTEXT.md` | 225 | `CORE_CONTEXT.md` |
| `__init__.py` | 16 | `__init__.py` |
| `apps.py` | 13 | `apps.py` |
| `utils.py` | 379 | `utils.py` |

---

## Árbol de Directorios

```
core/
├── templates
│   ├── about
│   │   ├── about.html
│   │   └── about_old_panda.html
│   ├── blank
│   │   └── blank.html
│   ├── contact
│   │   └── contact.html
│   ├── core
│   │   ├── url_map.html
│   │   └── url_map_detail.html
│   ├── docs
│   │   └── gtd_guide.html
│   ├── faq
│   │   └── faq.html
│   ├── home
│   │   └── home.html
│   ├── layouts
│   │   ├── includes
│   │   │   ├── header
│   │   │   │   └── credit.html
│   │   │   ├── information
│   │   │   │   ├── info_acordeon.html
│   │   │   │   ├── info_links.html
│   │   │   │   └── info_links_card.html
│   │   │   ├── nav-content
│   │   │   │   ├── account.html
│   │   │   │   ├── analyst.html
│   │   │   │   ├── chat.html
│   │   │   │   ├── configuration.html
│   │   │   │   ├── courses.html
│   │   │   │   ├── curriculum.html
│   │   │   │   ├── dashboard.html
│   │   │   │   ├── events.html
│   │   │   │   ├── help.html
│   │   │   │   ├── kpis.html
│   │   │   │   ├── management.html
│   │   │   │   ├── pages.html
│   │   │   │   ├── projects.html
│   │   │   │   ├── rooms.html
│   │   │   │   ├── tasks.html
│   │   │   │   └── tools.html
│   │   │   ├── alert.html
│   │   │   └── disabled_link.html
│   │   ├── base.html
│   │   ├── header.html
│   │   ├── mask.html
│   │   └── sidebar.html
│   └── search
│       └── search.html
├── tests
│   └── test_performance.py
├── CORE_CONTEXT.md
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── urls.py
├── utils.py
└── views.py
```

---

## Endpoints registrados

Fuente: `urls.py`

```python
  path('', views.home_view, name='home'),
  path('', views.home_view, name='index'),
  path('about/', views.about_view, name='about'),
  path('contact/', views.contact_view, name='contact'),
  path('faq/', views.faq_view, name='faq'),
  path('gtd-guide/', views.gtd_guide_view, name='gtd_guide'),
  path('blank/', views.blank_view, name='blank'),
  path('<int:days>/', views.home_view, name='home_by_days'),
  path('<int:days>/<int:days_ago>/', views.home_view, name='home_by_days_range'),
  path('search/', views.search_view, name='search'),
  path('url-map/', views.url_map_view, name='url_map'),
  path('api/activities/more/', views.load_more_activities, name='load_more_activities'),
  path('api/items/<str:item_type>/more/', views.load_more_recent_items, name='load_more_recent_items'),
  path('api/categories/<str:category_type>/more/', views.load_more_categories, name='load_more_categories'),
  path('api/dashboard/refresh/', views.refresh_dashboard_data, name='refresh_dashboard_data'),
  path('api/dashboard/stats/', views.get_dashboard_stats, name='dashboard_stats'),
```

---

## Modelos detectados

**`models.py`**

- línea 5: `class Article(models.Model):`


---

## Migraciones

| Archivo | Estado |
|---------|--------|
| `0001_initial` | aplicada |
| `0002_alter_article_options_article_is_published_and_more` | aplicada |

---

## Funciones clave (views/ y services/)


---

## Compartir con Claude

```bash
cat /data/data/com.termux/files/home/projects/Management360/core/views/mi_vista.py | termux-clipboard-set
```
