# Pipeline de digitalización — Digitalización UPN

## 1. Propósito

Definir la línea de producción end-to-end desde la captura del documento físico hasta la publicación del microformato JSON canonical.

## 2. Etapas

| # | Etapa | Estado Django | Entrada | Salida | Responsable | Criterio de aceptación |
|---|---|---|---|---|---|---|
| 1 | Preparación de documentos | `preparacion` | Documento físico | Lote preparado | Archivista/Asistente | Sin grapas, sin objetos ajenos, orden verificado, foliado aplicado, estado de conservación documentado |
| 2 | Digitalización | `digitalizacion` | Lote preparado | Imágenes crudas | Operador de escáner | Resolución/DPI, formato TIFF/JPEG, perfil de color, metadata técnica embebida |
| 3 | Control de calidad 1 | `qc1` | Imágenes crudas | Imágenes aprobadas o rechazadas | Inspector independiente | Imagen nítida, completa, sin distorsión, contraste adecuado; rechazo si error > 1% (NARA) |
| 4 | Preprocesamiento | `preprocesamiento` | Imágenes aprobadas | Imágenes normalizadas | Procesamiento automático | Deskew, denoise, crop, OCR-ready; se preserva original |
| 5 | Metadatos | `metadatos` | Imágenes normalizadas | Metadatos aplicados | Catalogador | Dublin Core + PREMIS + metadata técnica; schema validado |
| 6 | Control de calidad 2 | `qc2` | Metadatos + imágenes | Registro validado | Inspector independiente | Metadatos precisos, completos, checksums correctos, naming convention ok |
| 7 | Auditoría | `auditoria` | Registro validado | Lote certificado | Auditor | Trazabilidad completa, cumplimiento de estándares, aprobación formal |
| 8 | Fedatación | `fedatacion` | Lote certificado | Lote fedatado | Fedatario juramentado | Firma digital, sello de tiempo, actas de apertura/cierre |
| 9 | Certificación | `certificado` | Lote fedatado | Microformato JSON + PDF/A | Sistema | JSON schema válido, PDF/A-2b generado, indexado en dashboard |

## 3. Estados y transiciones

```
[preparacion] → [digitalizacion] → [qc1] → [preprocesamiento] → [metadatos] → [qc2] → [auditoria] → [fedatacion] → [certificado]
                                                                                                                                        ↓
                                                                                                                               [rechazado]
```

Reglas:
- Un documento puede rechazarse en QC1 o QC2 y volver a la etapa anterior.
- La fedatación es opcional por documento, según su tipo.
- El dashboard muestra el estado actual del lote y de cada documento.

## 4. Criterios de rechazo

### QC1
- Imagen incompleta (cortada, falta contenido)
- Skew > 1°
- Contraste insuficiente para legibilidad
- Resolución < 300 DPI (para documentos institucionales)
- Presencia de sombras, reflejos o ruido excesivo

### QC2
- Metadatos Dublin Core incompletos
- Nomenclatura de archivo incorrecta
- Checksum no calculado
- OCR no ejecutado (cuando es requerido)
- PDF/A no generado (cuando es requerido)

## 5. Metadatos

### Dublin Core (mínimo)

- `title`: título del documento
- `creator`: autor o entidad responsable
- `subject`: lista de temas
- `description`: descripción del contenido
- `date`: fecha del documento
- `type`: tipo de documento
- `format`: formato MIME
- `language`: idioma
- `rights`: derechos
- `identifier`: ID único

### PREMIS (preservación)

- `agent`: agente de preservación
- `object`: entidad preservada
- `event`: acción de preservación
- `rights`: derechos de preservación

## 6. Nomenclatura

| Elemento | Patrón |
|---|---|
| Documento | `upn_YYYY-MM-DD_NNN.ext` |
| Carpeta de trabajo | `upn_YYYY-MM-DD_NNN/` |
| Microformato | `upn_YYYY-MM-DD_NNN.json` |
| Lote | `LOTE_YYYYMMDD_NNN` |

`NNN` es secuencia correlativa por día.

## 7. Checksums

Para cada documento se calculan:
- MD5
- SHA256

Se registran en `checksum_md5` y `checksum_sha256` del modelo `DocumentoDigital`.

## 8. Microformato JSON

Cada documento produce un JSON canonical con esta estructura:

```json
{
  "schemaVersion": "1.0.0",
  "documentId": "upn_20260719_009",
  "type": "Plan de estudios",
  "source": {...},
  "dublinCore": {...},
  "processing": {
    "ocrEngine": "tesseract",
    "ocrConfidence": 0.96,
    "convertedToPdfA": true,
    "pdfAPath": "...",
    "masterTiffPath": "...",
    "checksum": {
      "md5": "...",
      "sha256": "..."
    }
  },
  "structuredContent": {...},
  "relations": {...}
}
```

## 9. Integración con M360

- Cada `LoteDigitalizacion` se asocia a un `project_id` o `course_id` de M360.
- El dashboard se sirve en `/digitalizacion/`.
- La API se expone en `/api/v1/digitalizacion/`.
- Los microformatos JSON se indexan en `memory_index.json` como entries tipo `MICROFORMATO`.

## 10. Comandos

```bash
# Migrar microformatos JSON existentes
./venv/bin/python manage.py migrar_microformatos

# Levantar servidor de desarrollo
./venv/bin/python manage.py runserver 127.0.0.1:8001
```
