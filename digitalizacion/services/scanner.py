import subprocess
from pathlib import Path


class ScannerService:
    def listar(self):
        try:
            result = subprocess.run(
                ['python3', '-m', 'scanlib', 'list'],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception as e:
            return f'Error: {e}'

    def escanear(self, dispositivo_idx, destino, prefijo, dpi=300, modo_color='color', formato='jpeg', calidad=95):
        destino_pdf = Path(destino) / f'{prefijo}_scan.pdf'
        cmd = [
            'python3', '-m', 'scanlib', 'scan',
            '-s', str(dispositivo_idx),
            '-o', str(destino_pdf),
            '--dpi', str(dpi),
            '--color-mode', modo_color,
            '--format', formato,
            '--jpeg-quality', str(calidad),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            # Extraer imágenes del PDF si se generó
            imagenes = []
            if destino_pdf.exists() and formato in ('jpeg', 'png'):
                try:
                    import fitz  # PyMuPDF
                    pdf = fitz.open(str(destino_pdf))
                    for i in range(len(pdf)):
                        page = pdf[i]
                        pix = page.get_pixmap(dpi=dpi)
                        img_path = Path(destino) / f'{prefijo}_pagina_{i+1}.{formato}'
                        pix.save(str(img_path))
                        imagenes.append(str(img_path))
                    pdf.close()
                except Exception as e:
                    stderr += f'\nError extrayendo imágenes: {e}'
            
            return {
                'ok': True,
                'stdout': stdout,
                'stderr': stderr,
                'pdf': str(destino_pdf),
                'imagenes': imagenes,
                'files': len(imagenes),
            }
        except subprocess.CalledProcessError as e:
            return {
                'ok': False,
                'stdout': e.stdout,
                'stderr': e.stderr,
                'code': e.returncode,
            }
