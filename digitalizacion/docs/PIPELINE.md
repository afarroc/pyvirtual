# Pipeline de digitalización — Digitalización UPN

## 1. Propósito

Definir la línea de producción end-to-end desde la recepción del documento físico hasta la publicación del microformato JSON canonical, alineada a 36 CFR 1236 Subpart E, Dublin Core, PREMIS y PDF/A-2b.

## 2. Roles y responsabilidades

| Rol | Responsabilidades en el pipeline |
|---|---|
| Archivista / Asistente | Recepción, preparación física, checklist, cierre de `preparacion`, generación de acta de recepción. |
| Operador de escáner | Captura de imágenes, configuración de DPI/modo color/formato, entrega en `inbox`. |
| Inspector QC1 | Aprobación/rechazo de imágenes crudas según criterios NARA/FADGI. |
| Motor de preprocesamiento | Deskew, denoise, crop, binarización; salida en `preprocessed`. |
| Catalogador | Dublin Core + PREMIS, controlled vocabularies, OCR, generación de microformato JSON. |
| Inspector QC2 | Validación de metadatos, checksums, naming convention, PDF/A, confianza OCR. |
| Auditor | Trazabilidad completa, cumplimiento de estándares, aprobación formal. |
| Fedatario | Certificación de integridad: SHA-256 + timestamp + actas. |
| Administrador | Configuración, asignación de roles, supervisión de pipeline, despliegue. |

## 3. Etapas

| # | Etapa | Estado Django | Entrada | Salida | Responsable | Criterio de aceptación |
|---|---|---|---|---|---|---|
| 1a | Recepción | `recepcion` | Documento físico | Lote registrado con acta de recepción | Archivista/Asistente | Inventario verificado, archivo de origen documentado, responsable de entrega registrado, fecha/hora registrada, condición general evaluada. |
| 1b | Preparación | `preparacion` | Lote recibido | Lote preparado con checklist completado | Archivista/Asistente | Sin grapas/clips, sin objetos ajenos, orden verificado, foliado aplicado si corresponde, estado de conservación documentado, total de folios declarado. |
| 2 | Digitalización / captura | `digitalizacion` | Lote preparado | Imágenes crudas en `inbox` | Operador de escáner | DPI ≥ 300, formato TIFF/JPEG, perfil de color, metadata técnica embebida, cantidad de imágenes = folios declarados. |
| 3 | Control de calidad 1 | `qc1` | Imágenes crudas | Imágenes aprobadas o rechazadas | Inspector independiente | Imagen completa, skew < 1°, contraste/brillo legibles, sin sombras/reflejos/ruido excesivo, resolución ≥ 300 DPI. |
| 4 | Preprocesamiento | `preprocesamiento` | Imágenes aprobadas | Imágenes normalizadas en `preprocessed` | Procesamiento automático | Deskew ±1°, denoise sin perder trazo, crop sin recortes, binarización adaptativa si B/N, resolucion preservada. |
| 5 | Metadatos | `metadatos` | Imágenes normalizadas | Microformato JSON + metadatos aplicados | Catalogador | Dublin Core completo, PREMIS embedido, OCR ejecutado, confianza ≥ umbral, microformato JSON validado contra schema. |
| 6 | Control de calidad 2 | `qc2` | Metadatos + imágenes | Registro validado | Inspector independiente | Metadatos precisos y completos, checksums MD5/SHA256 calculados, naming convention ok, PDF/A-2b generado. |
| 7 | Auditoría | `auditoria` | Registro validado | Lote certificado | Auditor | Trazabilidad completa, cumplimiento de estándares, aprobación formal, eventos PREMIS completos. |
| 8 | Fedatación | `fedatacion` | Lote certificado | Lote fedatado | Fedatario juramentado | Firma digital, sello de tiempo, actas de apertura/cierre, hash SHA-256 del lote. |
| 9 | Certificación | `certificado` | Lote fedatado | Microformato JSON + PDF/A-2b + reporte de calidad | Sistema | JSON schema válido, PDF/A-2b generado, indexado en dashboard/memory_index. |

## 4. Estados y transiciones

```
[recepcion] → [preparacion] → [digitalizacion] → [qc1] → [preprocesamiento] → [metadatos] → [qc2] → [auditoria] → [fedatacion] → [certificado]
                                                                                                                                                          ↓
                                                                                                                                                     [rechazado]
```

Reglas:
- Un documento puede rechazarse en QC1 o QC2 y volver a la etapa anterior.
- La fedatación es opcional por documento, según su tipo y valor legal.
- El dashboard muestra el estado actual del lote y de cada documento.

## 5. Criterios de rechazo

### Recepción
- Inventario físico no coincide con registros declarados.
- Daño estructural irreparable que impide escaneo legible.
- Falta de documentación de archivo de origen o responsable.

### Preparación
- Grapas o clips no retirados.
- Objetos ajenos presentes (post-its, notas, clips).
- Foliado pendiente en documentos que lo requieren.
- Estado de conservación no documentado.
- Folios no declarados o no coinciden con físico.

### QC1
- Imagen incompleta (cortada, falta contenido).
- Skew > 1°.
- Contraste insuficiente para legibilidad.
- Resolución < 300 DPI (para documentos institucionales).
- Presencia de sombras, reflejos o ruido excesivo.

### QC2
- Metadatos Dublin Core incompletos.
- Nomenclatura de archivo incorrecta.
- Checksum no calculado o no coincide.
- OCR no ejecutado (cuando es requerido).
- PDF/A no generado o inválido.

## 6. Microformato JSON canonical

Cada documento produce un JSON canonical con esta estructura:

```json
{
  "schemaVersion": "1.0.0",
  "documentId": "upn_20260719_009",
  "type": "Plan de estudios",
  "source": {
    "physicalLocation": "Archivo Central UPN",
    "lote": "LOTE_20260722_001",
    "folios": 7,
    "estado_conservacion": "Bueno",
    "grapas_detectadas": false,
    "objetos_ajenos": "",
    "foliado_aplicado": true,
    "observaciones_preparacion": "Reparación mínima, sin objetos ajenos."
  },
  "dublinCore": {
    "title": "Plan de estudios 2016-1",
    "creator": "UPN",
    "subject": ["Educación", "Plan de estudios"],
    "description": "Sílabo oficial del curso",
    "date": "2016-01-01",
    "type": "Plan de estudios",
    "format": "application/pdf",
    "language": "es",
    "rights": "Derechos reservados UPN",
    "identifier": "upn_20260719_009"
  },
  "premis": {
    "agent": "M360 Digitalization Pipeline",
    "events": [
      {
        "eventType": "digitization",
        "eventDateTime": "2026-07-22T10:00:00Z",
        "eventOutcome": "success",
        "linkingAgent": "Operador escáner",
        "eventDetail": "DPI=300, formato=JPEG, modo=color"
      },
      {
        "eventType": "ocr",
        "eventDateTime": "2026-07-22T11:00:00Z",
        "eventOutcome": "success",
        "linkingAgent": "Tesseract 5",
        "eventDetail": "confidence=0.96"
      }
    ]
  },
  "processing": {
    "ocrEngine": "tesseract",
    "ocrConfidence": 0.96,
    "convertedToPdfA": true,
    "pdfAPath": "/ruta/a/upn_20260719_009.pdf",
    "masterTiffPath": "/ruta/a/preprocessed/upn_20260719_009.tiff",
    "checksum": {
      "md5": "d41d8cd98f00b204e9800998ecf8427e",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  },
  "structuredContent": {},
  "relations": {}
}
```

## 7. Metadatos

### Dublin Core (mínimo)

| Elemento | Uso en M360 |
|---|---|
| `title` | `DocumentoDigital.titulo` |
| `creator` | `DocumentoDigital.creator` |
| `subject` | `DocumentoDigital.subject` (lista) |
| `description` | `DocumentoDigital.description` |
| `date` | `DocumentoDigital.fecha_documento` |
| `type` | `DocumentoDigital.tipo` |
| `format` | MIME del archivo maestro |
| `language` | `DocumentoDigital.language` |
| `rights` | `DocumentoDigital.rights` |
| `identifier` | `DocumentoDigital.document_id` |

### PREMIS (preservación)

| Entidad | Uso en M360 |
|---|---|
| `agent` | Usuario o sistema que ejecuta la etapa |
| `object` | Documento digital (`document_id`, checksums, rutas) |
| `event` | Cada etapa del pipeline registrada en `EtapaPipeline` |
| `rights` | Derechos asociados al documento |

### JSON Canonicalization

- El microformato JSON se serializa según **RFC 8785** antes de generar checksums o firmar.
- Esto garantiza que pequeñas diferencias de orden de claves no alteren el hash criptográfico.

## 8. Nomenclatura

| Elemento | Patrón |
|---|---|
| Documento | `upn_YYYY-MM-DD_NNN.ext` |
| Carpeta de trabajo | `upn_YYYY-MM-DD_NNN/` |
| Microformato | `upn_YYYY-MM-DD_NNN.json` |
| Lote | `LOTE_YYYYMMDD_NNN` |

`NNN` es secuencia correlativa por día.

## 9. Checksums

Para cada documento se calculan:
- MD5
- SHA256

Se registran en `checksum_md5` y `checksum_sha256` del modelo `DocumentoDigital`.

## 10. Integración con M360

- Cada `LoteDigitalizacion` se asocia a un `project_id` o `course_id` de M360.
- El dashboard se sirve en `/digitalizacion/`.
- La API se expone en `/api/v1/digitalizacion/`.
- Los microformatos JSON se indexan en `memory_index.json` como entries tipo `MICROFORMATO`.

## 11. Quality Management (NARA / 36 CFR 1236)

### 11.1 QM plan
El pipeline implementa un Quality Management plan mínimo que incluye:
- Políticas y funciones por rol.
- Especificaciones de imagen (DPI, formato, perfil de color).
- Especificaciones de metadatos (Dublin Core + PREMIS).
- Especificaciones de formato de archivo (PDF/A-2b).
- Procedimientos de inspección por etapa.
- Acciones correctivas y trazabilidad.

### 11.2 Roles
- QA: Archivista en preparación + Catalogador en metadatos.
- QC: Inspector QC1 + Inspector QC2.
- Validación: Auditor + Fedatario.

### 11.3 Trazabilidad
- Cada transición de estado queda registrada en `EtapaPipeline`.
- Cada evento de preservación queda registrado en el bloque `premis.events` del microformato JSON.
- Los checksums se calculan sobre rutas maestras y se validan en QC2 y certificación.

## 12. Comandos

```bash
# Migrar microformatos JSON existentes
./venv/bin/python manage.py migrar_microformatos

# Levantar servidor de desarrollo
./venv/bin/python manage.py runserver 127.0.0.1:8001
```
