import hashlib
from pathlib import Path


class ChecksumService:
    @staticmethod
    def calculate_file_checksums(path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {'md5': '', 'sha256': ''}
        
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
                sha256.update(chunk)
        return {
            'md5': md5.hexdigest(),
            'sha256': sha256.hexdigest(),
        }

    @staticmethod
    def calculate_checksums_for_documento(documento):
        checksums = {'md5': '', 'sha256': ''}
        paths = []
        if documento.ruta_preprocessed:
            paths.append(documento.ruta_preprocessed)
        if documento.ruta_acceso:
            paths.append(documento.ruta_acceso)
        if documento.ruta_master:
            paths.append(documento.ruta_master)
        
        if not paths:
            return checksums
        
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        for path in paths:
            try:
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        md5.update(chunk)
                        sha256.update(chunk)
            except FileNotFoundError:
                continue
        
        checksums['md5'] = md5.hexdigest()
        checksums['sha256'] = sha256.hexdigest()
        return checksums
