# Sync Summary — App Digitalización M360

**Fecha:** 2026-07-20
**Estado:** Código completado, documentación sincronizada, pendiente de commit.

## Resumen de cambios

La app `digitalizacion` fue implementada completamente dentro del proyecto **Management360** en `/Volumes/Macintosh HD - Datos/projects/Management360/`. A continuación se documenta el estado actual y la sincronización realizada.

## Archivos agregados/modificados

### Nuevos archivos (app completa)

| Archivo | Líneas | Estado |
|---|---|---|
| `digitalizacion/__init__.py` | — | ✅ |
| `digitalizacion/apps.py` | — | ✅ |
| `digitalizacion/models.py` | 115 | ✅ |
| `digitalizacion/views.py` | 659 | ✅ |
| `digitalizacion/urls.py` | 26 | ✅ |
| `digitalizacion/forms.py` | 37 | ✅ |
| `digitalizacion/serializers.py` | 28 | ✅ |
| `digitalizacion/admin.py` | — | ✅ |
| `digitalizacion/tasks.py` | — | ✅ |
| `digitalizacion/services/__init__.py` | — | ✅ |
| `digitalizacion/services/pipeline.py` | — | ✅ |
| `digitalizacion/services/scanner.py` | — | ✅ |
| `digitalizacion/services/preprocessor.py` | — | ✅ |
| `digitalizacion/services/ocr_service.py` | — | ✅ |
| `digitalizacion/services/pdfa_service.py` | — | ✅ |
| `digitalizacion/services/metadata_service.py` | — | ✅ |
| `digitalizacion/services/fedatacion_service.py` | — | ✅ |
| `digitalizacion/services/checksum_service.py` | — | ✅ |
| `digitalizacion/templates/digitalizacion/base.html` | 80 | ✅ |
| `digitalizacion/templates/digitalizacion/home.html` | 109 | ✅ |
| `digitalizacion/templates/digitalizacion/components/_site_header.html` | 12 | ✅ |
| `digitalizacion/templates/digitalizacion/components/_navbar.html` | 18 | ✅ |
| `digitalizacion/templates/digitalizacion/components/_site_footer.html` | 5 | ✅ |
| `digitalizacion/templates/digitalizacion/preparacion.html` | 156 | ✅ |
| `digitalizacion/templates/digitalizacion/procesar.html` | 159 | ✅ |
| `digitalizacion/templates/digitalizacion/base.html` | 30 | ✅ |
| `digitalizacion/templates/digitalizacion/etapas/digitalizar.html` | 135 | ✅ |
| `digitalizacion/templates/digitalizacion/etapas/cc1.html` | 63 | ✅ |
| `digitalizacion/templates/digitalizacion/etapas/metadatos.html` | 73 | ✅ |
| `digitalizacion/templates/digitalizacion/etapas/qc2.html` | 47 | ✅ |
| `digitalizacion/templates/digitalizacion/etapas/auditoria.html` | 80 | ✅ |
| `digitalizacion/templates/digitalizacion/etapas/certificar.html` | 58 | ✅ |
| `digitalizacion/static/digitalizacion/css/main.css` | — | ❌ Eliminado (migrado a M360 Design System) |
| `digitalizacion/docs/ARQUITECTURA.md` | 180 | ✅ Sincronizado |
| `digitalizacion/docs/API.md` | 177 | ✅ |
| `digitalizacion/docs/MANUAL_USUARIO.md` | — | ✅ |
| `digitalizacion/docs/PIPELINE.md` | — | ✅ |
| `digitalizacion/docs/README.md` | 43 | ✅ Sincronizado |
| `digitalizacion/migrations/0001_initial.py` | — | ✅ |
| `digitalizacion/migrations/0002_alter_etapapipeline_documento.py` | — | ✅ |
| `digitalizacion/management/commands/migrar_microformatos.py` | — | ✅ |
| `digitalizacion/management/commands/run_pipeline.py` | — | ✅ |

### Archivos modificados (integración M360)

| Archivo | Cambio |
|---|---|
| `panel/settings.py` | Agregado `'digitalizacion.apps.DigitalizacionConfig'` a `INSTALLED_APPS` |
| `panel/urls.py` | Agregado `path('digitalizacion/', include('digitalizacion.urls', namespace='digitalizacion'))` |
| `api/v1/urls.py` | Agregados 4 routers: `digitalizacion/lotes`, `documentos`, `etapas`, `fedatacion` |
| `api/v1/views.py` | Agregados imports y ViewSets de digitalizacion |
| `api/v1/serializers.py` | Agregados serializers de digitalizacion |

## Modelos implementados

| Modelo | Campos clave | Estado |
|---|---|---|
| `LoteDigitalizacion` | nombre, estado, ruta_base, proyecto_m360, curso_m360, metadata_proyecto, created_by | ✅ |
| `DocumentoDigital` | document_id (unique), tipo, titulo, creator, subject, description, fecha_documento, language, rights, ruta_inbox, ruta_preprocessed, ruta_acceso, ruta_master, checksum_sha256, checksum_md5, ocr_engine, ocr_confidence, converted_to_pdf_a, microformato_json | ✅ |
| `EtapaPipeline` | lote, documento, etapa, estado, usuario, inicio, fin, observaciones, metadata | ✅ |
| `Fedatacion` | lote (OneToOne), fedatario, certificado_numero, firma_digital, sello_tiempo, acta_apertura, acta_cierre, hash_lote | ✅ |

## Servicios implementados

| Servicio | Función | Estado |
|---|---|---|
| `PipelineDigitalizacion` | Orquestador de 9 etapas, validación de transiciones | ✅ |
| `ScannerService` | Wrapper `scanlib` para captura desde escáner | ✅ |
| `PreprocessorService` | Deskew, denoise, normalización (Pillow) | ✅ |
| `OCRService` | Ejecución OCR vía pytesseract | ✅ |
| `PDFAService` | Generación PDF/A (workaround Pillow) | ✅ |
| `MetadataService` | Dublin Core + PREMIS (placeholder) | ⚠️ Placeholder |
| `FedatacionService` | Firma digital, sello de tiempo (placeholder) | ⚠️ Placeholder |
| `ChecksumService` | Cálculo MD5/SHA-256 | ✅ |

## Vistas web implementadas

| Vista | URL | Descripción | Estado |
|---|---|---|---|
| `dashboard` | `/digitalizacion/dashboard/` | Panel principal con estadísticas | ✅ |
| `preparacion` | `/digitalizacion/preparacion/` | Crear lotes y registrar documentos | ✅ |
| `digitalizar_documento` | `/digitalizacion/digitalizar/<id>/` | Escaneo y subida de imágenes | ✅ |
| `cc1_documento` | `/digitalizacion/cc1/<id>/` | Control de calidad 1 | ✅ |
| `metadatos_documento` | `/digitalizacion/metadatos/<id>/` | Dublin Core + OCR | ✅ |
| `qc2_documento` | `/digitalizacion/qc2/<id>/` | Control de calidad 2 | ✅ |
| `auditoria_documento` | `/digitalizacion/auditoria/<id>/` | Bitácora y reporte | ✅ |
| `certificar_documento` | `/digitalizacion/certificar/<id>/` | Certificación y fedatación | ✅ |
| `acceso_pdf` | `/digitalizacion/acceso/<id>/` | Servir PDF/A | ✅ |
| `procesar_documento` | `/digitalizacion/procesar/<id>/` | Ejecución genérica de pipeline | ✅ |

## API REST expuesta

| Recurso | Ruta base | Métodos |
|---|---|---|
| Lotes | `/api/v1/digitalizacion/lotes/` | CRUD + etapas, fedatacion |
| Documentos | `/api/v1/digitalizacion/documentos/` | CRUD + catalog |
| Etapas | `/api/v1/digitalizacion/etapas/` | Read-only |
| Fedatación | `/api/v1/digitalizacion/fedatacion/` | Read-only |

## Templates implementados

| Template | Líneas | Descripción |
|---|---|---|
| `base.html` | 31 | Layout base M360 |
| `home.html` | 109 | Panel principal |
| `components/_site_header.html` | 12 | Header parcial |
| `components/_navbar.html` | 18 | Navegación parcial |
| `components/_site_footer.html` | 5 | Footer parcial |
| `preparacion.html` | 156 | Gestión de lotes y documentos |
| `procesar.html` | 159 | Ejecución genérica de pipeline |
| `base.html` | 30 | Base layout M360 |
| `etapas/digitalizar.html` | 135 | Escaneo y subida |
| `etapas/cc1.html` | 63 | Control de calidad 1 |
| `etapas/metadatos.html` | 73 | Metadatos + OCR |
| `etapas/qc2.html` | 47 | Control de calidad 2 |
| `etapas/auditoria.html` | 80 | Auditoría |
| `etapas/certificar.html` | 58 | Certificación |

## Sincronización de documentación realizada

### Migración a Design System M360 (2026-07-20)
- ✅ Eliminado `static/digitalizacion/css/` completo (9 archivos)
- ✅ Templates migrados a clases `m360-*` exclusivamente
- ✅ `base.html` ahora carga solo `{% static 'm360/css/_index.css' %}`
- ✅ Componentes (`_site_header.html`, `_navbar.html`, `_site_footer.html`) migrados a clases M360
- ✅ Vistas: home, preparacion, procesar, y 7 etapas migradas
- ✅ Documentación actualizada (ARQUITECTURA.md, README.md, SYNC.md)

### ARQUITECTURA.md
- ✅ Corregido árbol de directorios: agregados templates de etapas, forms.py, management commands, migraciones
- ✅ Eliminada referencia a `static/digitalizacion/css/main.css`; ahora usa `static/m360/css/_index.css` (Design System M360)
- ✅ Actualizada sección "Integración con M360" para reflejar diseño M360 exclusivo

### README.md
- ✅ Actualizada tabla de componentes: estáticos ahora referencian `static/m360/css/_index.css`

## Estado de git

```
M api/v1/serializers.py
M api/v1/urls.py
M api/v1/views.py
M courses/admin.py
M courses/models.py
M panel/settings.py
M panel/urls.py
?? courses/migrations/0002_upn_metodologia.py
?? digitalizacion/
?? static/digitalizacion/
```

## Próximos pasos sugeridos

1. **Commit** de la app digitalizacion y cambios de integración.
2. Ejecutar `makemigrations` y `migrate` para aplicar el esquema.
3. Ejecutar `migrar_microformatos` para cargar datos existentes.
4. Completar placeholders en `MetadataService` y `FedatacionService`.
5. Implementar edición multi-página en CC1 (rotar, renombrar, reordenar, eliminar, merge PDF).
6. Agregar tests unitarios para servicios y vistas.

## Notas

- El superuser `su` fue reseteado a password `admin123` previamente.
- Redis configurado según variables de entorno.
- La app corre en puerto 8001.
- Dependencias clave: Django 5.1.7, DRF, Pillow, PyMuPDF, pytesseract, scanlib.
