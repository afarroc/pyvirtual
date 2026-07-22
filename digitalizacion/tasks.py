from celery import shared_task
from .models import LoteDigitalizacion, DocumentoDigital, EtapaPipeline
from django.utils import timezone
import hashlib
import json

@shared_task
def ejecutar_etapa_pipeline(lote_id, documento_id, etapa, usuario_id=None):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    usuario = User.objects.filter(id=usuario_id).first() if usuario_id else None
    lote = LoteDigitalizacion.objects.filter(id=lote_id).first()
    documento = DocumentoDigital.objects.filter(id=documento_id).first()
    if not lote or not documento:
        return {'ok': False, 'error': 'Lote o documento no encontrado'}

    registro = EtapaPipeline.objects.create(
        lote=lote,
        documento=documento,
        etapa=etapa,
        estado='ok',
        inicio=timezone.now(),
        usuario=usuario,
    )

    # Aquí se llamaría al servicio correspondiente (scanner, preprocessor, ocr, pdfa, metadata, fedatacion)
    # Por ahora solo registra la etapa como placeholder del pipeline.
    registro.fin = timezone.now()
    registro.save()
    return {'ok': True, 'etapa': etapa, 'documento': documento.document_id}


@shared_task
def calcular_checksums_documento(documento_id):
    documento = DocumentoDigital.objects.filter(id=documento_id).first()
    if not documento:
        return {'ok': False}

    paths = []
    if documento.ruta_preprocessed:
        paths.append(documento.ruta_preprocessed)
    if documento.ruta_acceso:
        paths.append(documento.ruta_acceso)
    if documento.ruta_master:
        paths.append(documento.ruta_master)

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

    documento.checksum_md5 = md5.hexdigest()
    documento.checksum_sha256 = sha256.hexdigest()
    documento.save(update_fields=['checksum_md5', 'checksum_sha256'])
    return {'ok': True, 'sha256': documento.checksum_sha256}
