import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from django.utils import timezone
from digitalizacion.models import LoteDigitalizacion, DocumentoDigital, EtapaPipeline
from digitalizacion.services.pipeline import PipelineDigitalizacion

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta el pipeline de digitalización para documentos pendientes"

    def add_arguments(self, parser):
        parser.add_argument(
            '--lote-id',
            type=int,
            help='ID de lote específico a procesar'
        )
        parser.add_argument(
            '--doc-id',
            type=str,
            help='ID de documento específico a procesar'
        )
        parser.add_argument(
            '--etapa',
            type=str,
            choices=[
                'preparacion', 'digitalizacion', 'qc1', 'preprocesamiento',
                'metadatos', 'qc2', 'auditoria', 'fedatacion', 'certificado'
            ],
            help='Etapa específica a ejecutar'
        )
        parser.add_argument(
            '--avanzar',
            action='store_true',
            help='Avanzar automáticamente a la siguiente etapa'
        )

    def get_siguiente_etapa(self, documento):
        """Obtiene la siguiente etapa del pipeline para un documento."""
        etapas_completadas = set(
            documento.etapas.values_list('etapa', flat=True)
        )
        pipeline = [
            'preparacion', 'digitalizacion', 'qc1', 'preprocesamiento',
            'metadatos', 'qc2', 'auditoria', 'fedatacion', 'certificado'
        ]
        for etapa in pipeline:
            if etapa not in etapas_completadas:
                return etapa
        return None

    def handle(self, *args, **options):
        documentos = DocumentoDigital.objects.all()
        
        if options['lote_id']:
            documentos = documentos.filter(lote_id=options['lote_id'])
        
        if options['doc_id']:
            documentos = documentos.filter(document_id=options['doc_id'])
        
        # Excluir documentos certificados o rechazados
        documentos = documentos.exclude(
            lote__estado__in=['certificado', 'rechazado']
        ).select_related('lote')

        if not documentos.exists():
            self.stdout.write(self.style.WARNING("No hay documentos pendientes."))
            return

        total = documentos.count()
        procesados = 0
        errores = 0

        for documento in documentos:
            try:
                if options['etapa']:
                    etapa = options['etapa']
                else:
                    etapa = self.get_siguiente_etapa(documento)
                    if not etapa:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{documento.document_id}: pipeline completo, saltando."
                            )
                        )
                        continue

                pipeline = PipelineDigitalizacion(documento.lote)
                resultado = pipeline.ejecutar_etapa(
                    documento=documento,
                    etapa=etapa,
                    usuario=None,
                )

                if resultado.get('ok'):
                    procesados += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{documento.document_id}: etapa '{etapa}' completada."
                        )
                    )
                else:
                    errores += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"{documento.document_id}: error en '{etapa}': {resultado.get('error')}"
                        )
                    )

            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"{documento.document_id}: excepción: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Pipeline completado: {procesados}/{total} procesados, {errores} errores."
            )
        )
