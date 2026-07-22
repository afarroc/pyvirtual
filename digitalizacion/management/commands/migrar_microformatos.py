import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from digitalizacion.models import LoteDigitalizacion, DocumentoDigital

BASE = Path("/Volumes/Macintosh HD - Datos/otros_proyectos/Administracion_UPN/Documentos_Escaneados")
MICROFORMATOS = BASE / "microformatos"

User = get_user_model()


class Command(BaseCommand):
    help = "Migra microformatos JSON existentes al modelo DocumentoDigital"

    def handle(self, *args, **options):
        if not MICROFORMATOS.exists():
            self.stdout.write(self.style.ERROR(f"No existe {MICROFORMATOS}"))
            return

        user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("No hay usuarios para asignar created_by"))
            return

        lote, _ = LoteDigitalizacion.objects.get_or_create(
            nombre="Migración inicial workspace → M360",
            defaults={
                'estado': 'certificado',
                'ruta_base': str(BASE),
                'metadata_proyecto': {'origen': 'workspace/fotos_laboratorio', 'fecha_migracion': '2026-07-19'},
                'created_by': user,
            }
        )

        migrated = 0
        skipped = 0
        for p in sorted(MICROFORMATOS.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"Skip {p.name}: {e}"))
                continue

            document_id = data.get('documentId') or p.stem
            titulo = data.get('dublinCore', {}).get('title') or p.stem
            tipo = data.get('type') or 'Documento digital'
            creator = data.get('dublinCore', {}).get('creator', '')
            subject = data.get('dublinCore', {}).get('subject', [])
            description = data.get('dublinCore', {}).get('description', '')
            fecha = data.get('dublinCore', {}).get('date', '')
            language = data.get('dublinCore', {}).get('language', 'es')
            rights = data.get('dublinCore', {}).get('rights', '')
            original_files = data.get('source', {}).get('originalFiles', [])
            ruta_inbox = ''
            ruta_preprocessed = ''
            if original_files:
                first = next((f for f in original_files if f), '')
                if first:
                    ruta_inbox = str(BASE / first)
                    try:
                        rel = Path(ruta_inbox).relative_to(BASE)
                        ruta_preprocessed = str(BASE / 'preprocessed' / rel)
                    except ValueError:
                        ruta_preprocessed = str(BASE / 'preprocessed' / Path(ruta_inbox).name)
            processing = data.get('processing', {})
            ocr_engine = processing.get('ocrEngine', 'pending') or 'pending'
            ocr_confidence = processing.get('ocrConfidence')
            converted_to_pdf_a = bool(processing.get('convertedToPdfA'))
            checksum_sha256 = processing.get('checksum', {}).get('sha256', '')
            checksum_md5 = processing.get('checksum', {}).get('md5', '')
            microformato_json = data

            doc, created = DocumentoDigital.objects.update_or_create(
                document_id=document_id,
                defaults={
                    'lote': lote,
                    'tipo': tipo,
                    'titulo': titulo,
                    'creator': creator,
                    'subject': subject,
                    'description': description,
                    'fecha_documento': fecha or None,
                    'language': language,
                    'rights': rights,
                    'ruta_inbox': ruta_inbox,
                    'ruta_preprocessed': ruta_preprocessed,
                    'ruta_acceso': processing.get('pdfAPath', ''),
                    'ruta_master': processing.get('masterTiffPath', ''),
                    'checksum_sha256': checksum_sha256,
                    'checksum_md5': checksum_md5,
                    'ocr_engine': ocr_engine,
                    'ocr_confidence': ocr_confidence,
                    'converted_to_pdf_a': converted_to_pdf_a,
                    'microformato_json': microformato_json,
                }
            )
            migrated += 1
            self.stdout.write(self.style.SUCCESS(f"{'Creado' if created else 'Actualizado'}: {doc.document_id} — {doc.titulo}"))

        self.stdout.write(self.style.SUCCESS(f"Migración completada: {migrated} documentos, {skipped} omitidos."))
