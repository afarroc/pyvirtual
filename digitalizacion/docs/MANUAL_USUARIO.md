# Manual de usuario — Digitalización UPN

App: `digitalizacion` dentro de Management360  
Proyecto: Administracion_UPN  
URL: `http://127.0.0.1:8001/digitalizacion/dashboard/`

---

## 1. Roles y responsables

| Rol | Acciones permitidas | Responsabilidad |
|---|---|---|
| Operador de escáner | Captura, carga de imágenes | Digitalizar según parámetros técnicos. |
| Inspector QC | Revisión y aprobación/rechazo | Verificar calidad de imagen y metadatos. |
| Catalogador | Edición de metadatos | Completar Dublin Core, controlled vocabularies. |
| Auditor | Validación final | Verificar cumplimiento de estándares y cierre de lote. |
| Fedatario | Firma digital | Certificar lotes con valor legal. |
| Administrador | Configuración y asignación | Crear lotes, asignar roles, supervisar pipeline. |

---

## 2. Flujo de trabajo

### 2.1 Crear un lote desde Archivo Central

Este flujo aplica cuando **Archivo Central entrega un grupo de folios físicos** para digitalizar.

**Ruta:** `http://127.0.0.1:8001/digitalizacion/preparacion/`

1. Abrir la sección **Preparación** en el dashboard de digitalización.
2. Completar el formulario **Crear nuevo lote**:
   - **Nombre del lote:** `LOTE_20260719_001 - Archivo Central - Planes de Estudio 2016`
   - **Proyecto M360 / Curso M360:** asociar si aplica
   - **Ruta base de archivos:** `/Volumes/Macintosh HD - Datos/otros_proyectos/Administracion_UPN/Documentos_Escaneados/`
   - **Metadata de proyecto (JSON):** incluir origen, fecha recepción, responsable archivo central
3. Click en **Crear lote**.

**Resultado:** el lote queda en estado `preparacion` visible en la lista inferior.

### 2.2 Registrar folios/documents en preparación

1. En la misma página **Preparación**, completar el formulario **Agregar documento a lote**:
   - **Lote:** seleccionar el lote creado
   - **Document ID:** `upn_YYYY-MM-DD_NNN`
   - **Título:** descripción del documento
   - **Tipo:** `Plan de estudios`, `Examen`, `Acta`, etc.
   - **Creador:** entidad responsable
   - **Fecha del documento:** fecha real del documento
   - **Idioma:** `es` (por defecto)
   - **Derechos:** `Derechos reservados UPN` (por defecto)
2. Click en **Agregar documento**.
3. Repetir por cada folio o grupo de folios que conforman un documento.

**Resultado:** el lote queda en estado `preparacion` con N documentos registrados, cada uno con su ID único pero sin rutas de archivo todavía. La tabla inferior muestra todos los documentos registrados.

### 2.3 Cerrar preparación y pasar a digitalización

Cuando Archivo Central confirma que los folios están listos (reparados, foliados, limpios):

1. En la sección **Preparación**, ubicar el lote en la tarjeta inferior.
2. Click en **Cerrar preparación**.
3. Confirmar la acción en el diálogo.
4. El sistema registra automáticamente:
   - Etapa `preparacion` con estado `ok`
   - Observaciones: `Preparación cerrada. N documentos registrados.`
   - Timestamp de cierre
5. El lote cambia de estado a `digitalizacion` y desaparece de la lista de preparación.

**El lote ya está listo para digitalización.** El operador de escáner procede a escanear cada documento y actualiza las rutas `ruta_inbox` y `ruta_preprocessed` en cada `DocumentoDigital`.

### 2.4 Ejecutar pipeline

El pipeline se ejecuta etapa por etapa. Para avanzar:

1. Abrir el documento en **Admin**.
2. Actualizar estado en **Etapas de pipeline** o usar la API.
3. Cada etapa registra:
   - Responsable
   - Fecha/hora inicio y fin
   - Observaciones
   - Metadata adicional

Estados disponibles:
- `preparacion`
- `digitalizacion`
- `qc1`
- `preprocesamiento`
- `metadatos`
- `qc2`
- `auditoria`
- `fedatacion`
- `certificado`
- `rechazado`

### 2.5 Control de calidad

**QC1** (sobre imágenes crudas):
- Imagen completa, no cortada.
- Sin distorsión, skew < 1°.
- Contraste y brillo legibles.
- Resolución >= 300 DPI.

**QC2** (sobre metadatos + preprocessed):
- Metadatos Dublin Core completos.
- Nomenclatura de archivos correcta.
- Checksums calculados.
- OCR ejecutado (si aplica).
- PDF/A generado (si aplica).

Si se detectan errores:
- Registrar observación en la etapa.
- Cambiar estado a `rechazado` y volver a la etapa anterior.

### 2.6 Fedatación (opcional, valor legal)

Para documentos que requieren valor legal (planes de estudios, certificados, actas):

1. Ir a **Fedataciones**.
2. Crear nueva fedatación:
   - Fedatario responsable
   - Certificado número
   - Firma digital (base64 o referencia)
   - Sello de tiempo
   - Acta de apertura / cierre
3. Al guardar, el lote pasa automáticamente a estado `certificado`.

### 2.7 Dashboard

El dashboard muestra:
- Total de documentos, tipos, OCR pendiente, PDF/A generados.
- Tarjetas por documento con:
  - Título y tipo
  - Estado OCR y PDF/A
  - Checksum
  - Enlace a vista de acceso
  - Enlace a admin

Filtros:
- Por tipo de documento
- Por estado OCR
- Por PDF/A generado
- Búsqueda por título o ID

---

## 3. Comandos útiles

```bash
# Migrar microformatos JSON existentes al modelo
./venv/bin/python manage.py migrar_microformatos

# Actualizar dashboard standalone (si se usa)
python3 tools/update_upn_dashboard.py

# Escanear documento (requiere scanlib)
python3 -m scanlib scan -s 0 -d "/ruta/inbox" -p "upn_20260719_010" --dpi 300 --color-mode color --format jpeg --jpeg-quality 95
```

---

## 4. Troubleshooting

| Problema | Solución |
|---|---|
| `scanlib list` vacío | Cerrar HP Easy Scan, reconectar USB, reintentar. |
| OCR < 90% | Revisar deskew/denoise; para manuscritos usar VLM multimodal. |
| PDF/A rechazado | Validar con veraPDF; usar PDF/A-2b con transparencias complejas. |
| Checksum no cuadra | Recalcular sobre `preprocessed/` (no sobre `inbox/` si se editó). |
| JSON inválido | Validar contra esquema antes de archivar. |

---

## 5. Referencias

- ISO 19005-2 (PDF/A-2)
- Dublin Core Metadata Element Set v1.1
- METS / PREMIS (Library of Congress)
- NTP 392.030-2:2015 (Perú)
- Decreto Legislativo N° 681 (Perú)
