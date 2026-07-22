# Arquitectura — App Digitalización M360

## Visión general

La app `digitalizacion` extiende **Management360** para gestionar la línea de producción de documentos escaneados, microformatos JSON y metadatos Dublin Core/PREMIS del proyecto **Administracion_UPN**.

## Contexto

- **Proyecto cliente:** Administracion_UPN
- **Proyecto M360 asociado:** events.Project (ID 80)
- **URL dashboard:** `/digitalizacion/dashboard/`
- **API REST:** `/api/v1/digitalizacion/`
- **Directorio base de archivos:** `/Volumes/Macintosh HD - Datos/otros_proyectos/Administracion_UPN/Documentos_Escaneados/`
- **Estructura de carpetas normalizada:**
  - `inbox/<lote>/` — imágenes/pdf originales por lote
  - `preprocessed/<lote>/` — imágenes preprocesadas por lote
  - `acceso/` — PDFs finales certificados
  - `microformatos/` — JSONs por documento
  - `dashboard/` — datos de dashboard
  - `master/` — reservado para TIFF maestros
  - `ocr/` — reservado para resultados OCR
- **Lote activo:** ID 1 — `Migración inicial workspace → M360` (estado: `certificado`)
- **Documentos:** 9 documentos UPN con rutas validadas y etapas normalizadas (9 etapas únicas por documento)

## Estructura

```
digitalizacion/
├── __init__.py
├── apps.py
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── admin.py
├── tasks.py
├── forms.py
├── services/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── scanner.py
│   ├── preprocessor.py
│   ├── ocr_service.py
│   ├── pdfa_service.py
│   ├── metadata_service.py
│   └── fedatacion_service.py
├── templates/
│   └── digitalizacion/
│       ├── base.html
│       ├── home.html
│       ├── components/
│       │   ├── _site_header.html
│       │   ├── _navbar.html
│       │   └── _site_footer.html
│       ├── preparacion.html
│       ├── procesar.html
│       └── etapas/
│           ├── base.html
│           ├── digitalizar.html
│           ├── cc1.html
│           ├── metadatos.html
│           ├── qc2.html
│           ├── auditoria.html
│           └── certificar.html
├── static/
│   └── (usa static/m360/css/_index.css — Design System M360)
├── management/
│   └── commands/
│       ├── migrar_microformatos.py
│       └── run_pipeline.py
├── migrations/
│   ├── 0001_initial.py
│   └── 0002_alter_etapapipeline_documento.py
└── docs/
    ├── README.md
    ├── MANUAL_USUARIO.md
    ├── ARQUITECTURA.md
    ├── API.md
    └── PIPELINE.md
```

## Modelos

### LoteDigitalizacion

Agrupa documentos por campaña/proyecto/curso.

```python
class LoteDigitalizacion(models.Model):
    nombre = models.CharField(max_length=255)
    proyecto_m360 = models.ForeignKey('events.Project', null=True, blank=True, on_delete=models.SET_NULL)
    curso_m360 = models.ForeignKey('courses.Course', null=True, blank=True, on_delete=models.SET_NULL)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='preparacion')
    ruta_base = models.CharField(max_length=512)
    metadata_proyecto = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
```

### DocumentoDigital

Representa un documento escaneado individual.

```python
class DocumentoDigital(models.Model):
    lote = models.ForeignKey(LoteDigitalizacion, related_name='documentos', on_delete=models.CASCADE)
    document_id = models.CharField(max_length=64, unique=True)
    tipo = models.CharField(max_length=128)
    titulo = models.CharField(max_length=255)
    creator = models.CharField(max_length=255, blank=True)
    subject = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    fecha_documento = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=8, default='es')
    rights = models.CharField(max_length=255, blank=True)
    ruta_inbox = models.CharField(max_length=512)
    ruta_preprocessed = models.CharField(max_length=512)
    ruta_acceso = models.CharField(max_length=512, blank=True)
    ruta_master = models.CharField(max_length=512, blank=True)
    checksum_sha256 = models.CharField(max_length=128, blank=True)
    checksum_md5 = models.CharField(max_length=128, blank=True)
    ocr_engine = models.CharField(max_length=64, default='pending')
    ocr_confidence = models.FloatField(null=True, blank=True)
    converted_to_pdf_a = models.BooleanField(default=False)
    microformato_json = models.JSONField(default=dict, blank=True)
```

### EtapaPipeline

Registro histórico de cada etapa para trazabilidad.

```python
class EtapaPipeline(models.Model):
    lote = models.ForeignKey(LoteDigitalizacion, related_name='etapas', on_delete=models.CASCADE)
    documento = models.ForeignKey(DocumentoDigital, null=True, blank=True, on_delete=models.CASCADE)
    etapa = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    estado = models.CharField(max_length=20, choices=[('ok','OK'),('error','Error'),('rechazado','Rechazado')])
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
```

### Fedatacion

Certificación por fedatario juramentado (valor legal).

```python
class Fedatacion(models.Model):
    lote = models.OneToOneField(LoteDigitalizacion, on_delete=models.CASCADE, related_name='fedatacion')
    fedatario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='fedataciones')
    certificado_numero = models.CharField(max_length=128)
    firma_digital = models.TextField()
    sello_tiempo = models.DateTimeField()
    acta_apertura = models.CharField(max_length=512)
    acta_cierre = models.CharField(max_length=512)
    hash_lote = models.CharField(max_length=128)
```

## OCR

- Motor: Tesseract 4.1.1 empaquetado como bundle local en `tools/tesseract/Tesseract.app`.
- Datos de idioma: `tools/tesseract/Tesseract.app/Contents/Resources/`.
- Paquete Python: `pytesseract` en `venv312`.
- `OCRService` detecta automáticamente binario y `TESSDATA_PREFIX`.
- Idioma por defecto: `spa` (mapeo automático desde `es`).
- Integración: etapa `metadatos` ejecuta OCR sobre imágenes en `ruta_preprocessed` y guarda texto + confianza en `microformato_json`.

## PDF/A

- `PDFAService` genera PDF/A-2b usando Pillow/convertidor local.
- Ruta de salida: `.../acceso/<document_id>.pdf`.
- Flag: `DocumentoDigital.converted_to_pdf_a`.

## Servicios

| Servicio | Responsabilidad |
|---|---|
| `pipeline.py` | Orquestador de etapas, validación de transiciones. |
| `scanner.py` | Wrapper de `scanlib` para captura desde escáner. |
| `preprocessor.py` | Deskew, denoise, normalización de imágenes. |
| `ocr_service.py` | Ejecución de OCR (Tesseract local / fallback). |
| `pdfa_service.py` | Generación de PDF/A-2b. |
| `metadata_service.py` | Aplicación de Dublin Core + PREMIS. |
| `fedatacion_service.py` | Firma digital, sello de tiempo, actas. |

## Tareas async

- `ejecutar_etapa_pipeline`: ejecuta una etapa del pipeline en background.
- `calcular_checksums_documento`: calcula SHA256/MD5 de archivos.

## Integración con M360

- **Settings:** `digitalizacion.apps.DigitalizacionConfig` registrado en `panel/settings.py`.
- **URLs:** `digitalizacion/` en `panel/urls.py` y `/api/v1/digitalizacion/` en `api/v1/urls.py`.
- **Estilos:** `static/m360/css/_index.css` (Design System M360). La app no tiene CSS propio; usa exclusivamente el diseño M360 con clases `m360-*`.
- **Templates:** Extienden `digitalizacion/base.html` (layout base M360). Componentes parciales: `_site_header.html`, `_navbar.html`, `_site_footer.html`. Vistas: home, preparación, procesar, y 7 vistas de etapa.
- **Forms:** `LoteDigitalizacionForm` y `DocumentoDigitalForm` con validación de unicidad de `document_id` por lote.

## Diagrama de secuencia simplificado

```
Usuario → Admin: Crear lote
Usuario → Admin: Cargar documento
Operador → ScannerService: escanear()
Inspector → QC1: revisar imagenes
Procesador → PreprocessorService: procesar()
Catalogador → MetadataService: aplicar metadatos
Inspector → QC2: validar metadatos
Auditor → EtapaPipeline: cerrar auditoria
Fedatario → FedatacionService: firmar()
Sistema → Microformato: generar JSON
Sistema → Dashboard: publicar
```

## Decisiones técnicas

- **App dentro de M360:** evita duplicar auth, base de datos y despliegue.
- **Design System M360:** la app usa exclusivamente `static/m360/css/_index.css` con clases `m360-*`. No hay CSS propio en `static/digitalizacion/`.
- **JSON canonical:** cada documento tiene un microformato JSON con contrato schema-first.
- **Trazabilidad:** `EtapaPipeline` registra cada transición con usuario y timestamps.
- **Placeholders:** servicios de pipeline tienen implementaciones mínimas; se completarán por etapas.
