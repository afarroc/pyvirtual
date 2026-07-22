# Digitalización y Microformatos — App M360

## Resumen

App Django integrada en **Management360** para la gestión de documentos escaneados, microformatos JSON y línea de producción de digitalización del proyecto **Administracion_UPN**.

## Alcance

- Registro de lotes de digitalización y documentos escaneados.
- Pipeline de 9 etapas: preparación → digitalización → QC1 → preprocesamiento → metadatos → QC2 → auditoría → fedatación → certificación.
- Generación y mantenimiento de microformatos JSON canonicales.
- Dashboard web y API REST para consumo por agentes/sistemas externos.
- Integración con escáner vía `scanlib`, OCR vía `pytesseract` + Tesseract local bundle, PDF/A vía Pillow.
- Migración desde microformatos JSON filesystem hacia el modelo Django.

## Estructura

| Componente | Archivos clave |
|---|---|
| Modelos | `models.py` — LoteDigitalizacion, DocumentoDigital, EtapaPipeline, Fedatacion |
| Vistas web | `views.py` — 9 vistas por etapa + dashboard + preparación |
| API REST | ViewSets integrados en `/api/v1/digitalizacion/` |
| Servicios | `services/` — pipeline, scanner, preprocessor, ocr, pdfa, metadata, fedatacion, checksum |
| Templates | `templates/digitalizacion/` — 12 HTML (dashboard, preparación, procesar, 7 etapas) |
| Estáticos | `static/m360/css/_index.css` (Design System M360, clases `m360-*`) |
| Forms | `forms.py` — LoteDigitalizacionForm, DocumentoDigitalForm |
| Tareas | `tasks.py` — Celery tasks para pipeline y checksums |
| Admin | `admin.py` — Registro de los 4 modelos |
| Management commands | `management/commands/run_pipeline.py`, `migrar_microformatos.py` |
| Migraciones | `migrations/0001_initial.py`, `0002_alter_etapapipeline_documento.py` |

## Documentación

| Documento | Ruta | Propósito |
|---|---|---|
| Manual de usuario | `docs/MANUAL_USUARIO.md` | Guía para operadores, catalogadores, auditores y fedatarios. |
| Arquitectura | `docs/ARQUITECTURA.md` | Modelos, servicios, pipeline, integración con M360. |
| API REST | `docs/API.md` | Endpoints, esquemas, ejemplos de consumo. |
| Pipeline | `docs/PIPELINE.md` | Etapas, controles, criterios de aceptación y cierre. |

## OCR / Tesseract

- Binario Tesseract empaquetado en `tools/tesseract/Tesseract.app`.
- Datos de idioma en `tools/tesseract/Tesseract.app/Contents/Resources/` (`eng`, `spa`, `osd`, `snum`).
- `OCRService` detecta automáticamente el binario y el `tessdata_prefix`.
- Idioma español: usar `lang='spa'` en el servicio.
- No requiere `brew` ni instalación global.

## Configuración rápida

```bash
cd /Volumes/Macintosh\ HD\ -\ Datos/projects/Management360
./venv/bin/python manage.py makemigrations digitalizacion
./venv/bin/python manage.py migrate
./venv/bin/python manage.py migrar_microformatos
./venv/bin/python manage.py runserver 127.0.0.1:8001
```

Luego abrir:
- Dashboard: `http://127.0.0.1:8001/digitalizacion/dashboard/`
- API: `http://127.0.0.1:8001/api/v1/digitalizacion/`

## Enlaces relevantes

- Proyecto cliente: `projects/Administracion_UPN/`
- Procedimiento de escaneo: `docs/guides/PROCEDIMIENTO_DIGITALIZACION_ESCANER_UPN.md`
- Línea de producción: `docs/guides/LINEA_PRODUCCION_DIGITALIZACION_UPN.md`
- Handoff: `projects/Administracion_UPN/handoffs/HANDOFF_2026-07-19_digitalizacion_documento_fisico_upn.md`
