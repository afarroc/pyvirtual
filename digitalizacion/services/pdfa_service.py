import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFAService:
    """
    Genera PDF a partir de imágenes escaneadas.
    Nota: usa Pillow como workaround hasta lograr PDF/A-2b estricto con pypdf/reportlab.
    """

    def convertir(self, ruta_imagen: str, ruta_salida: str, titulo: str = '') -> dict:
        try:
            from PIL import Image

            ruta_img = Path(ruta_imagen)
            ruta_out = Path(ruta_salida)
            ruta_out.parent.mkdir(parents=True, exist_ok=True)

            if not ruta_img.exists():
                return {'ok': False, 'error': f'Imagen no encontrada: {ruta_imagen}'}

            img = Image.open(ruta_img)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Guardar como PDF usando Pillow
            img.save(ruta_out, format='PDF', resolution=300.0)

            return {
                'ok': True,
                'output': str(ruta_out),
                'pages': 1,
                'width': img.size[0],
                'height': img.size[1],
                'note': 'PDF generado con Pillow; PDF/A-2b pendiente de validación/regeneración.',
            }
        except Exception as e:
            logger.error(f"Error generando PDF/A: {e}")
            return {'ok': False, 'error': str(e)}
