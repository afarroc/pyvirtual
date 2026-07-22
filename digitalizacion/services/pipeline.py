import logging
from pathlib import Path
from django.utils import timezone
from .ocr_service import OCRService
from .preprocessor import PreprocessorService
from .pdfa_service import PDFAService
from .checksum_service import ChecksumService
from ..models import LoteDigitalizacion, DocumentoDigital, EtapaPipeline

logger = logging.getLogger(__name__)


class PipelineDigitalizacion:
    ETAPAS = [
        'preparacion', 'digitalizacion', 'qc1', 'preprocesamiento',
        'metadatos', 'qc2', 'auditoria', 'fedatacion', 'certificado'
    ]

    def __init__(self, lote):
        self.lote = lote
        self.scanner = None  # Se puede inyectar ScannerService si se requiere
        self.preprocessor = PreprocessorService()
        self.ocr = OCRService()
        self.pdfa = PDFAService()
        self.checksum = ChecksumService()

    def ejecutar_etapa(self, documento, etapa, usuario=None, **kwargs):
        idx = self.ETAPAS.index(etapa) if etapa in self.ETAPAS else -1
        if idx > 0:
            prev = self.ETAPAS[idx - 1]
            docs_prev = EtapaPipeline.objects.filter(
                lote=self.lote, documento=documento, etapa=prev, estado='ok'
            ).count()
            if docs_prev == 0 and etapa not in ('preparacion', 'digitalizacion'):
                raise ValueError(f"Falta completar etapa {prev} para el documento {documento.document_id}")

        registro = EtapaPipeline.objects.create(
            lote=self.lote,
            documento=documento,
            etapa=etapa,
            estado='ok',
            inicio=timezone.now(),
            usuario=usuario,
        )
        resultado = {'ok': True, 'etapa': etapa, 'documento': documento.document_id}
        
        try:
            if etapa == 'preparacion':
                resultado['preparacion'] = 'ok'
            
            elif etapa == 'digitalizacion':
                resultado['digitalizacion'] = 'ok'
            
            elif etapa == 'qc1':
                resultado['qc1'] = 'ok'
            
            elif etapa == 'preprocesamiento':
                src = documento.ruta_inbox or kwargs.get('ruta_inbox')
                if src:
                    src_path = Path(src)
                    dst = kwargs.get('ruta_preprocessed') or str(
                        src_path.parent.parent.parent / 'preprocessed' / src_path.parent.name / src_path.name
                    )
                if src and dst:
                    res = self.preprocessor.procesar(src, dst)
                    if res.get('ok'):
                        documento.ruta_preprocessed = dst
                        documento.save(update_fields=['ruta_preprocessed'])
                        resultado['preprocessed'] = dst
                    else:
                        registro.estado = 'error'
                        resultado['ok'] = False
                        resultado['error'] = res.get('error')
                else:
                    resultado['skipped'] = 'no input path'

            elif etapa == 'metadatos':
                metadata = {
                    'schemaVersion': '1.0.0',
                    'documentId': documento.document_id,
                    'type': documento.tipo,
                    'dublinCore': {
                        'title': documento.titulo,
                        'creator': documento.creator,
                        'date': str(documento.fecha_documento) if documento.fecha_documento else None,
                        'type': documento.tipo,
                        'language': documento.language,
                        'rights': documento.rights,
                        'identifier': documento.document_id,
                    },
                    'processing': {
                        'ocrEngine': documento.ocr_engine,
                        'ocrConfidence': documento.ocr_confidence,
                        'preprocessing': ['deskew', 'denoise'],
                        'convertedToPdfA': documento.converted_to_pdf_a,
                        'pdfAPath': documento.ruta_acceso,
                    }
                }
                
                # Ejecutar OCR si está pendiente y hay ruta preprocessed
                if documento.ocr_engine == 'pending' and documento.ruta_preprocessed:
                    preprocessed_path = Path(documento.ruta_preprocessed).parent
                    images = sorted(list(preprocessed_path.glob('*.*')))
                    images = [p for p in images if p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.tif', '.tiff')]
                    
                    if images:
                        full_text = []
                        confidences = []
                        for img_path in images:
                            res = self.ocr.ejecutar(str(img_path), lang=documento.language or 'spa')
                            if res.get('ok'):
                                full_text.append(res.get('text', ''))
                                if res.get('confidence') is not None:
                                    confidences.append(res['confidence'])
                        
                        documento.ocr_engine = 'tesseract'
                        documento.ocr_confidence = sum(confidences) / len(confidences) if confidences else None
                        metadata['processing']['ocrEngine'] = documento.ocr_engine
                        metadata['processing']['ocrConfidence'] = documento.ocr_confidence
                        metadata['structuredContent'] = {
                            'pages': [
                                {
                                    'pageNumber': i + 1,
                                    'ocrText': txt,
                                    'confidence': confidences[i] if i < len(confidences) else None,
                                    'layoutType': 'text',
                                }
                                for i, txt in enumerate(full_text)
                            ]
                        }
                        resultado['ocr'] = {
                            'engine': 'tesseract',
                            'pages': len(full_text),
                            'avg_confidence': documento.ocr_confidence,
                        }
                    else:
                        resultado['ocr'] = {'skipped': 'no images found'}
                elif documento.ocr_engine != 'pending':
                    resultado['ocr'] = {'engine': documento.ocr_engine, 'confidence': documento.ocr_confidence}
                else:
                    resultado['ocr'] = {'skipped': 'no preprocessed path'}
                
                documento.microformato_json = metadata
                documento.save(update_fields=['ocr_engine', 'ocr_confidence', 'microformato_json'])
                resultado['metadata'] = 'applied'

            elif etapa == 'qc2':
                missing = []
                if not documento.titulo:
                    missing.append('titulo')
                if not documento.fecha_documento:
                    missing.append('fecha_documento')
                if missing:
                    registro.estado = 'rechazado'
                    registro.observaciones = f"Faltan metadatos: {', '.join(missing)}"
                    resultado['ok'] = False
                    resultado['rechazado'] = True
                    resultado['missing'] = missing
                else:
                    resultado['qc2'] = 'ok'

            elif etapa == 'auditoria':
                resultado['auditoria'] = 'ok'

            elif etapa == 'fedatacion':
                resultado['fedatacion'] = 'ok'

            elif etapa == 'certificado':
                # Calcular checksums
                checksums = self.checksum.calculate_checksums_for_documento(documento)
                documento.checksum_sha256 = checksums['sha256']
                documento.checksum_md5 = checksums['md5']
                
                # Generar PDF/A si hay ruta preprocessed
                if documento.ruta_preprocessed and not documento.converted_to_pdf_a:
                    base_dir = Path(documento.ruta_preprocessed).parent.parent.parent
                    pdfa_path = str(base_dir / 'acceso' / (Path(documento.document_id).name + '.pdf'))
                    pdfa_result = self.pdfa.convertir(documento.ruta_preprocessed, pdfa_path, titulo=documento.titulo)
                    if pdfa_result.get('ok'):
                        documento.ruta_acceso = pdfa_path
                        documento.converted_to_pdf_a = True
                        resultado['pdfa'] = pdfa_path
                    else:
                        logger.error(f"PDF/A failed for {documento.document_id}: {pdfa_result.get('error')}")
                
                documento.save(update_fields=[
                    'checksum_sha256', 'checksum_md5', 'ruta_acceso', 'converted_to_pdf_a'
                ])
                resultado['checksums'] = checksums

        except Exception as e:
            registro.estado = 'error'
            registro.observaciones = str(e)
            resultado['ok'] = False
            resultado['error'] = str(e)
        
        finally:
            registro.fin = timezone.now()
            registro.save()
        
        return resultado
