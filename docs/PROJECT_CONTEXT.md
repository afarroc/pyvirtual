# Mapa del Proyecto — Management360

> Generado por mementobloom  |  2026-06-29 02:05 -05:00
> Raíz: `/Volumes/Macintosh HD - Datos/projects/Management360`
> Apps: **20**  |  Metodología: GTD nativa  |  Estado servidor: activo (Daphne PID 66624, puerto 8000)

---

## Resumen por app (estado operativo)

| App | Namespace | Archivos | Modelos | Endpoints | Notas |
|-----|-----------|----------|---------|-----------|-------|
| `accounts` | `—` | 19 | 1 | 11 | Auth y perfiles custom (`User extends AbstractUser`) |
| `analyst` | `analyst` | 59 | 10 | 99 | Plataforma de datos, reportes, ETL, dashboards, pipelines |
| `api` | `—` | 6 | 0 | 4 | API REST publica (`/api/csrf/`, `/api/login/`, `/api/logout/`, `/api/signup/`) |
| `bitacora` | `bitacora` | 17 | 4 | 9 | Bitácora personal GTD |
| `board` | `board` | 15 | 3 | 8 | Kanban board |
| `bots` | `bots` | 16 | 10 | 13 | Bots, campañas, leads, distribución automática |
| `campaigns` | `campaigns` | 6 | 3 | 6 | Campañas, discador, contactos |
| `chat` | `chat` | 27 | 6 | 40 | Chat en tiempo real, rooms, mensajes, notificaciones, presencia |
| `core` | `—` | 44 | 1 | 16 | Home, about, contact, FAQ, GTD guide, dashboard, search, url-map |
| `courses` | `courses` | 88 | 12 | 59 | LMS: cursos, módulos, lecciones, categorías, analytics, contenido |
| `cv` | `cv` | 32 | 10 | 14 | Curriculum Vitae dinámico |
| `events` | `events` | 233 | 31 | 147 | **App principal**: Proyectos, Tareas, Eventos, Inbox, Tags, Reminders, GTD |
| `help` | `help` | 15 | 7 | 10 | Centro de ayuda, FAQ, artículos, videos, feedback |
| `kpis` | `kpis` | 11 | 2 | 5 | KPIs, AHT Dashboard, CallRecord, ExchangeRate |
| `memento` | `—` | 16 | 1 | 6 | Memento personal (daily/weekly/monthly/mori) |
| `panel` | `—` | 9 | 0 | 28 | Panel de configuración, routers centrales |
| `passgen` | `—` | 12 | 0 | 2 | Generador de contraseñas |
| `rooms` | `rooms` | 46 | 16 | 53 | Salas virtuales, portals, entradas/salidas, 3D, navegación |
| `sim` | `sim` | 33 | 11 | 48 | Simulador WFM (ACD multi-agente, training, GTR, pipelines) |
| `simcity` | `simcity` | 9 | 1 | 14 | Juego/Simulación ciudad |

---

## Estado API v1 (bridge mementobloom)

**Endpoints operativos:**
- `GET /api/v1/health/`
- `GET /api/v1/projects/` y `/api/v1/projects/{id}/`
- `GET /api/v1/projects/{project_id}/tasks/`
- `GET /api/v1/tasks/{task_id}/`
- `POST /api/v1/tasks/{task_id}/status/`
- `GET/POST /api/v1/events/` — ** reparado 2026-06-29 **
- `GET /api/v1/projects/{project_id}/reminders/`
- `GET /api/v1/inbox/`
- `POST /api/v1/inbox/{id}/`
- `GET /api/v1/courses/` y `/api/v1/course-categories/`

**Fix aplicados en esta sesión:**
- `EventViewSet.perform_create`: inyecta defaults para `event_status`, `host`, `assigned_to` cuando el cliente no los envía. Elimina `IntegrityError 500`.
- `TaskViewSet.perform_create`: valida `project` obligatorio, inyecta `TaskStatus` default, `host` y `assigned_to`.
- `TaskSerializer`: cambio de `IntegerField` a `PrimaryKeyRelatedField` en `task_status_id`, `project_id`, `assigned_to_id`, `host_id` para correcta resolución de instancias Django.
- Import corregido: `from events.models import ..., Status, TaskStatus` en `api/v1/views.py`.

**Tareas pendientes de fix en M360:**
- `TaskViewSet.retrieve/update`: endpoint `GET/PUT /api/v1/tasks/{id}/` presenta `TypeError 500` no resuelto aún.

---

## Clientes registrados (proyectos activos en M360)

| Cliente | Proyecto ID | Estado | Notas |
|---------|-------------|--------|-------|
| Administracion_UPN | 80 | Draft | Ciclo 01 en gestión GTD. 5 cursos publicados (IDs 55-59). Fase 1 cerrada, Fase 2 iniciada. |
| Bridge M360 - API Courses | 81 | Draft | API Courses operativa. Fix endpoint events aplicado. |

---

## Modelos por app (resumen)

### events (app principal)
- `Status`, `TaskStatus`, `ProjectStatus`
- `Project`, `Task`, `Event`, `Reminder`
- `InboxItem`, `Tag`, `TagCategory`
- `TaskSchedule`, `TaskProgram`, `TaskDependency`
- `ProjectState`, `ProjectHistory`, `TaskState`, `TaskHistory`, `EventState`, `EventHistory`
- `ProjectTemplate`, `TemplateTask`
- `InboxItemAuthorization`, `InboxItemClassification`, `InboxItemHistory`
- `GTDClassificationPattern`, `GTDLearningEntry`, `GTDProcessingSettings`

### courses
- `CourseCategory`, `Course`, `Module`, `Lesson`, `LessonAttachment`
- `Enrollment`, `Progress`, `Review`, `ContentBlock`

### analyst, bots, chat, rooms, sim, simcity, cv, bitacora, board, help, kpis, memento, passgen
- Ver detalle en archivos `_CONTEXT.md` de cada app.

---

## Integraciones clave
- **mementobloom → M360**: bridge `tools/m360_bridge/client.py` consume API v1 para proyectos, tareas, eventos, cursos.
- **M360 → mementobloom**: no existe pull automático; sincronización manual por API.
- **Cursos LMS ↔ Proyectos GTD**: entidades separadas sin FK directa (IDs coincidentes por auto-incremento compartido en BD, no por diseño).
