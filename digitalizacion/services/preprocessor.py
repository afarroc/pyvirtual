import logging
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


class PreprocessorService:
    """
    Preprocesamiento básico de imágenes escaneadas usando Pillow.
    Si la entrada es PDF, convierte la primera página a imagen con PyMuPDF.
    """

    def procesar(self, ruta_entrada: str, ruta_salida: str) -> dict:
        try:
            entrada = Path(ruta_entrada)
            salida = Path(ruta_salida)
            salida.parent.mkdir(parents=True, exist_ok=True)

            if not entrada.exists():
                return {'ok': False, 'error': f'Archivo no encontrado: {ruta_entrada}'}

            # Detectar tipo de archivo
            header = entrada.read_bytes()[:10]
            es_pdf = header.startswith(b'%PDF')

            if es_pdf:
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(str(entrada))
                    if doc.page_count == 0:
                        return {'ok': False, 'error': 'PDF sin páginas'}
                    page = doc[0]
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                    doc.close()
                except Exception as e:
                    return {'ok': False, 'error': f'Error convirtiendo PDF a imagen: {e}'}
            else:
                img = Image.open(entrada)

            original_mode = img.mode

            # Convertir a RGB si es necesario
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # 1. Denoise básico usando filtro median (solo si imagen grande)
            if img.size[0] > 500 and img.size[1] > 500:
                img = img.filter(ImageFilter.MedianFilter(size=3))

            # 2. Mejorar contraste
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)

            # 3. Mejorar nitidez
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)

            # 4. Ajustar brillo si es necesario (detectar imágenes oscuras)
            gray = img.convert('L')
            brightness = sum(gray.getdata()) / len(gray.getdata())
            if brightness < 100:
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.2)

            # Guardar resultado
            fmt = salida.suffix.lower().lstrip('.') or 'jpeg'
            if fmt in ('jpg', 'jpeg'):
                img.save(salida, format='JPEG', quality=95)
            elif fmt == 'png':
                img.save(salida, format='PNG')
            elif fmt in ('tif', 'tiff'):
                img.save(salida, format='TIFF')
            else:
                img.save(salida, format='JPEG', quality=95)

            return {
                'ok': True,
                'input': str(entrada),
                'output': str(salida),
                'mode': original_mode,
                'size': img.size,
                'was_pdf': es_pdf,
            }
        except Exception as e:
            logger.error(f"Error en preprocesamiento: {e}")
            return {'ok': False, 'error': str(e)}
