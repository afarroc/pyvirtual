# API REST — Digitalización M360

Base URL: `/api/v1/digitalizacion/`

---

## 1. Lotes

### Listar / Crear lotes

```
GET /api/v1/digitalizacion/lotes/
POST /api/v1/digitalizacion/lotes/
```

**Campos POST:**
- `nombre` (string, requerido)
- `proyecto_m360` (integer, opcional)
- `curso_m360` (integer, opcional)
- `estado` (string, opcional)
- `ruta_base` (string, requerido)
- `metadata_proyecto` (JSON, opcional)

### Detalle de lote

```
GET /api/v1/digitalizacion/lotes/{id}/
PUT /api/v1/digitalizacion/lotes/{id}/
PATCH /api/v1/digitalizacion/lotes/{id}/
DELETE /api/v1/digitalizacion/lotes/{id}/
```

### Etapas de un lote

```
GET /api/v1/digitalizacion/lotes/{id}/etapas/
```

### Fedatación de un lote

```
GET /api/v1/digitalizacion/lotes/{id}/fedatacion/
POST /api/v1/digitalizacion/lotes/{id}/fedatacion/
```

**Campos POST:**
- `fedatario` (integer, ID de usuario, requerido)
- `certificado_numero` (string, requerido)
- `firma_digital` (string, requerido)
- `sello_tiempo` (datetime ISO 8601, requerido)
- `acta_apertura` (string, requerido)
- `acta_cierre` (string, requerido)
- `hash_lote` (string, requerido)

---

## 2. Documentos

### Catálogo de documentos

```
GET /api/v1/digitalizacion/documentos/
GET /api/v1/digitalizacion/documentos/catalog/
```

**Filtros disponibles:**
- `tipo` — tipo de documento
- `ocr_engine` — motor OCR
- `converted_to_pdf_a` — booleano
- `lote` — ID de lote

### Detalle de documento

```
GET /api/v1/digitalizacion/documentos/{id}/
PUT /api/v1/digitalizacion/documentos/{id}/
PATCH /api/v1/digitalizacion/documentos/{id}/
DELETE /api/v1/digitalizacion/documentos/{id}/
```

**Campos actualizables:**
- `tipo`, `titulo`, `creator`, `subject`, `description`
- `fecha_documento`, `language`, `rights`
- `ruta_inbox`, `ruta_preprocessed`, `ruta_acceso`, `ruta_master`
- `checksum_sha256`, `checksum_md5`
- `ocr_engine`, `ocr_confidence`, `converted_to_pdf_a`
- `microformato_json`

---

## 3. Etapas

### Listar etapas

```
GET /api/v1/digitalizacion/etapas/
```

**Filtros disponibles:**
- `lote`
- `documento`
- `etapa`
- `estado`
- `usuario`

---

## 4. Fedatación

### Listar fedataciones

```
GET /api/v1/digitalizacion/fedatacion/
```

---

## 5. Ejemplos de consumo

### Python / requests

```python
import requests

BASE = 'http://127.0.0.1:8001/api/v1/digitalizacion'
TOKEN = 'Bearer <M360_API_KEY>'

headers = {'Authorization': TOKEN, 'Content-Type': 'application/json'}

# Listar documentos
resp = requests.get(f'{BASE}/documentos/', headers=headers)
print(resp.status_code, resp.json())

# Actualizar OCR de un documento
doc_id = 'upn_20260719_009'
payload = {
    'ocr_engine': 'tesseract',
    'ocr_confidence': 0.96,
    'converted_to_pdf_a': True,
    'ruta_acceso': '/Volumes/.../acceso/upn_20260719_009.pdf',
}
resp = requests.patch(
    f'{BASE}/documentos/?document_id={doc_id}',
    headers=headers,
    json=payload
)
print(resp.status_code, resp.json())
```

### cURL

```bash
curl -H "Authorization: Bearer <M360_API_KEY>" \
     http://127.0.0.1:8001/api/v1/digitalizacion/documentos/
```

---

## 6. Autenticación

La API usa el mismo esquema que M360:
- Header: `Authorization: Bearer <M360_API_KEY>`
- El `M360_API_KEY` de producción (Render) es distinto al `.env` local.

---

## 7. Códigos de estado

| Código | Significado |
|---|---|
| 200 | OK |
| 201 | Creado |
| 400 | Solicitud inválida |
| 401 | No autenticado |
| 403 | Sin permisos |
| 404 | No encontrado |
| 500 | Error interno |
