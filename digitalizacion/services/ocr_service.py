import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_LOCAL_TESSERACT = _BASE_DIR / 'tools' / 'tesseract' / 'Tesseract.app' / 'Contents' / 'MacOS' / 'tesseract'
_LOCAL_TESSDATA = _BASE_DIR / 'tools' / 'tesseract' / 'Tesseract.app' / 'Contents' / 'Resources'


class OCRService:
    """
    Servicio OCR basado en Tesseract + pytesseract.
    - Si el binario de Tesseract no está disponible, devuelve un resultado
      controlado para no bloquear el pipeline.
    - Acepta `tesseract_cmd` para inyectar la ruta del binario cuando no
      esté en PATH (ej. instalación manual sin brew).
    - Usa `tessdata_prefix` para localizar los archivos de idioma cuando
      Tesseract está empaquetado como bundle local.
    """

    RUTAS_BINARIO = [
        str(_LOCAL_TESSERACT),
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract',
        '/opt/local/bin/tesseract',
        '/usr/bin/tesseract',
        '/Applications/Tesseract OCR.app/Contents/MacOS/tesseract',
        '/Applications/tesseract/tesseract',
        shutil.which('tesseract'),
    ]

    RUTAS_TESSDATA = [
        str(_LOCAL_TESSDATA),
        '/usr/local/share/tessdata',
        '/opt/homebrew/share/tessdata',
        '/opt/local/share/tessdata',
        '/usr/share/tesseract-ocr/4.00/tessdata',
        '/usr/share/tesseract-ocr/5/tessdata',
    ]

    def __init__(self, tesseract_cmd=None, tessdata_prefix=None):
        self.tesseract_cmd = tesseract_cmd or self._detectar_binario()
        self.tessdata_prefix = tessdata_prefix or self._detectar_tessdata()

    def _detectar_binario(self):
        for ruta in self.RUTAS_BINARIO:
            if ruta and Path(ruta).exists() and Path(ruta).is_file():
                return str(ruta)
        return None

    def _detectar_tessdata(self):
        for ruta in self.RUTAS_TESSDATA:
            if ruta and Path(ruta).exists() and Path(ruta).is_dir():
                return str(ruta)
        return None

    def _configurar_env(self):
        if self.tesseract_cmd:
            os.environ.setdefault('TESSERACT_CMD', self.tesseract_cmd)
        if self.tessdata_prefix:
            os.environ.setdefault('TESSDATA_PREFIX', self.tessdata_prefix)

    def ejecutar(self, ruta_imagen: str, lang: str = 'spa') -> dict:
        if not self.tesseract_cmd:
            logger.warning(
                "Tesseract no disponible en PATH ni en rutas conocidas. "
                "Instalar Tesseract manualmente o pasar `tesseract_cmd`."
            )
            return {
                'ok': False,
                'engine': 'pending',
                'text': '',
                'confidence': None,
                'language': lang,
                'error': 'tesseract binary not found',
            }

        lang = 'spa' if lang == 'es' else lang
        self._configurar_env()

        try:
            import pytesseract
            from PIL import Image

            if hasattr(pytesseract, 'pytesseract'):
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            img = Image.open(ruta_imagen)
            texto = pytesseract.image_to_string(img, lang=lang)
            conf = pytesseract.image_to_data(
                img, lang=lang, output_type=pytesseract.Output.DICT
            )

            confidences = [c for c in conf.get('conf', []) if c != -1]
            avg_conf = (
                sum(confidences) / len(confidences) / 100.0 if confidences else None
            )

            return {
                'ok': True,
                'engine': 'tesseract',
                'text': texto.strip(),
                'confidence': avg_conf,
                'language': lang,
            }
        except ImportError:
            logger.warning("pytesseract no disponible; OCR pendiente.")
            return {
                'ok': False,
                'engine': 'pending',
                'text': '',
                'confidence': None,
                'language': lang,
                'error': 'pytesseract not installed',
            }
        except Exception as e:
            logger.error(f"Error ejecutando OCR: {e}")
            return {
                'ok': False,
                'engine': 'error',
                'text': '',
                'confidence': None,
                'language': lang,
                'error': str(e),
            }
