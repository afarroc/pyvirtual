# Manual de usuario — Digitalización UPN

App: `digitalizacion` dentro de Management360  
Proyecto: Administracion_UPN  
URL: `http://127.0.0.1:8001/digitalizacion/dashboard/`

---

## 1. Roles y responsables

| Rol | Acciones permitidas | Responsabilidad |
|---|---|---|
| Archivista / Asistente | Recepción, preparación, cierre de recepción/preparación | Registrar entrada de lotes, generar acta de recepción, acondicionar folios, declarar estado de conservación y folios, cerrar preparación. |
| Operador de escáner | Captura, carga de imágenes | Digitalizar según parámetros técnicos: DPI ≥ 300, formato TIFF/JPEG, perfil de color. |
| Inspector QC1 | Revisión y aprobación/rechazo | Verificar calidad de imagen y completitud contra folios declarados. |
| Catalogador | Edición de metadatos | Completar Dublin Core, controlled vocabularies, OCR, generar microformato JSON canonical. |
| Inspector QC2 | Validación final de metadatos | Verificar checksums, nomenclatura, PDF/A-2b, confianza OCR. |
| Auditor | Aprobación formal | Trazabilidad completa, cumplimiento de estándares, aprobación de lote. |
| Fedatario | Firma digital | Certificar lotes con valor legal. |
| Administrador | Configuración y asignación | Crear lotes, asignar roles, supervisar pipeline. |

---

## 2. Flujo de trabajo

### 2.1 Recepción de lote desde Archivo Central

**Ruta:** `http://127.0.0.1:8001/digitalizacion/recepcion/`

1. Abrir la sección **Recepción** en el dashboard de digitalización.
2. Completar el formulario **Registrar nuevo lote**:
   - **Nombre del lote:** `LOTE_YYYYMMDD_NNN - Archivo Central - Descripción`
   - **Proyecto M360 / Curso M360:** asociar si aplica
   - **Ruta base de archivos:** `/ruta/a/documentos`
   - **Metadata de proyecto (JSON):** incluir origen, fecha recepción, responsable archivo central
3. Click en **Registrar lote en recepción**.

**Resultado:** el lote queda en estado `preparacion` visible en la lista inferior, pendiente de preparación física.

4. Verificar checklist de recepción por lote:
   - Inventario físico verificado contra registros declarados
   - Archivo de origen documentado
   - Responsable de entrega registrado
   - Fecha y hora de recepción registrada
   - Condición general del lote evaluada
5. Click en **Cerrar recepción**.
6. Confirmar la acción en el diálogo.
7. El sistema registra automáticamente:
   - Etapa `recepcion` con estado `ok`
   - Etapa `preparacion` con estado `en_progreso`
   - Acta de recepción con responsable, fecha y cantidad de documentos
   - Timestamp de cierre
8. El lote queda listo para **preparación física**.

### 2.2 Preparación física de documentos

**Ruta:** `http://127.0.0.1:8001/digitalizacion/preparacion/`

1. Abrir la sección **Preparación** en el dashboard de digitalización.
2. Completar el formulario **Agregar documento a lote**:
   - **Lote:** seleccionar el lote con recepción cerrada
   - **Document ID:** `upn_YYYY-MM-DD_NNN`
   - **Título:** descripción del documento
   - **Tipo:** `Plan de estudios`, `Examen`, `Acta`, etc.
   - **Creador:** entidad responsable
   - **Fecha del documento:** fecha real del documento
   - **Folios:** cantidad de páginas/folios físicos a digitalizar
   - **Estado de conservación:** Bueno / Regular / Crítico
   - **Grapas detectadas:** sí/no
   - **Objetos ajenos:** post-its, clips, notas
   - **Foliado aplicado:** sí/no
   - **Observaciones:** reparaciones mínimas, retiros, observaciones del archivero
3. Click en **Agregar documento**.
4. Repetir por cada folio o grupo de folios que conforman un documento.

**Resultado:** el lote queda en estado `preparacion` con N documentos registrados, cada uno con su ID único pero sin rutas de archivo todavía. La tabla inferior muestra todos los documentos registrados.

### 2.3 Cierre de preparación y paso a digitalización

Cuando el archivista/asesor confirma que los folios están listos (reparados, foliados, limpios):

1. Ir al detalle del lote: `/digitalizacion/preparacion/lote/<lote_id>/`
2. Verificar checklist por documento:
   - Sin grapas ni clips
   - Sin objetos ajenos
   - Orden verificado
   - Foliado aplicado si corresponde
   - Estado de conservación documentado
   - Total de folios declarado coincide con físico
3. Click en **Cerrar preparación**.
4. Confirmar la acción en el diálogo.
5. El sistema registra automáticamente:
   - Etapa `preparacion` con estado `ok`
   - Etapa `digitalizacion` con estado `en_progreso`
   - Acta de recepción con responsable, fecha y cantidad de documentos
   - Timestamp de cierre
6. El lote cambia de estado a `digitalizacion`.

**El lote ya está listo para digitalización.** El operador de escáner procede a escanear cada documento desde `/digitalizacion/digitalizar/<documento_id>/`.

### 2.4 Captura de imágenes

**Ruta:** `/digitalizacion/digitalizar/<documento_id>/`

1. Subir imágenes escaneadas o escanear directamente desde el dispositivo conectado.
2. Verificar que la cantidad de archivos en `inbox` coincida con `folios` declarados.
3. Completar captura.
4. Click en **Completar digitalización y avanzar a CC1 →**.
5. El sistema registra etapa `digitalizacion` con estado `ok` y redirige a CC1.

### 2.5 Control de calidad 1

**Ruta:** `/digitalizacion/cc1/<documento_id>/`

Criterios:
- Imagen completa, no cortada.
- Sin distorsión, skew < 1°.
- Contraste y brillo legibles.
- Resolución >= 300 DPI.
- Sin páginas faltantes.

Acciones:
- **Aprobar:** avanza a preprocesamiento.
- **Rechazar:** registra motivo y detiene el avance.

### 2.6 Preprocesamiento

**Ruta:** `/digitalizacion/preprocesamiento/<documento_id>/`

Criterios:
- Deskew automático (±1° tolerancia).
- Reducción de ruido (denoise) sin perder trazo.
- Resolución mínima mantenida ≥ 300 DPI.
- Binarización adaptativa si el documento es B/N.
- Sin recortes ni pérdida de bordes.
- Salida en ruta preprocessed lista para OCR.

Acciones:
- **Aprobar:** avanza a metadatos.
- **Rechazar:** registra motivo y detiene el avance.

### 2.7 Metadatos + OCR

**Ruta:** `/digitalizacion/metadatos/<documento_id>/`

1. Completar formulario Dublin Core:
   - Título, creador, fecha, idioma, derechos, tema, descripción.
2. Click en **Guardar y ejecutar OCR**.
3. El sistema ejecuta OCR (Tesseract por defecto) y genera el microformato JSON canonical.
4. El documento pasa a QC2.

### 2.8 Control de calidad 2

**Ruta:** `/digitalizacion/qc2/<documento_id>/`

Criterios:
- Metadatos Dublin Core completos.
- Nomenclatura de archivos correcta.
- Checksums calculados.
- OCR ejecutado (si aplica) con confianza ≥ umbral.
- PDF/A generado (si aplica).

Acciones:
- **Aprobar:** avanza a auditoría.
- **Rechazar:** registra motivo y detiene el avance.

### 2.9 Auditoría

**Ruta:** `/digitalizacion/auditoria/<documento_id>/`

- Verificar trazabilidad completa.
- Verificar cumplimiento de estándares.
- Aprobación formal del lote.

Acciones:
- **Aprobar:** avanza a certificación/fedatación.
- **Rechazar:** registra motivo y detiene el avance.

### 2.10 Certificación / Fedatación

**Ruta:** `/digitalizacion/certificar/<documento_id>/`

- Ejecutar checksums finales.
- Generar PDF/A-2b.
- Crear fedatación si aplica.
- Firmar digitalmente.
- Indexar microformato JSON en dashboard y memory_index.

**Resultado:** Documento certificado y listo para archivado.

---

## 3. Dashboard

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

## 4. Comandos útiles

```bash
# Migrar microformatos JSON existentes
./venv/bin/python manage.py migrar_microformatos

# Actualizar dashboard standalone (si se usa)
python3 tools/update_upn_dashboard.py

# Escanear documento (requiere scanlib)
python3 -m scanlib scan -s 0 -d "/ruta/inbox" -p "upn_20260719_010" --dpi 300 --color-mode color --format jpeg --jpeg-quality 95
```

---

## 5. Troubleshooting

| Problema | Solución |
|---|---|
| `scanlib list` vacío | Cerrar HP Easy Scan, reconectar USB, reintentar. |
| OCR < 90% | Revisar deskew/denoise; para manuscritos usar VLM multimodal. |
| PDF/A rechazado | Validar con veraPDF; usar PDF/A-2b con transparencias complejas. |
| Checksum no cuadra | Recalcular sobre `preprocessed/` (no sobre `inbox/` si se editó). |
| JSON inválido | Validar contra esquema antes de archivar. |

---

## 6. Referencias

- ISO 19005-2 (PDF/A-2)
- Dublin Core Metadata Element Set v1.1
- METS / PREMIS (Library of Congress)
- NTP 392.030-2:2015 (Perú)
- Decreto Legislativo N° 681 (Perú)
- 36 CFR 1236 Subpart E — Digitizing Permanent Federal Records
- NARA Digitization Quality Management Guide 2023
- RFC 8785 — JSON Canonicalization Scheme (JCS)
