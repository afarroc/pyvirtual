from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q, Sum
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse, Http404
from pathlib import Path
from .models import LoteDigitalizacion, DocumentoDigital, EtapaPipeline, Fedatacion
from .serializers import (
    LoteDigitalizacionSerializer,
    DocumentoDigitalSerializer,
    EtapaPipelineSerializer,
    FedatacionSerializer,
)
from .forms import LoteDigitalizacionForm, DocumentoDigitalForm


class LoteViewSet(viewsets.ModelViewSet):
    queryset = LoteDigitalizacion.objects.all()
    serializer_class = LoteDigitalizacionSerializer

    @action(detail=True, methods=['get'])
    def etapas(self, request, pk=None):
        lote = self.get_object()
        etapas = lote.etapas.all()
        serializer = EtapaPipelineSerializer(etapas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def fedatacion(self, request, pk=None):
        lote = self.get_object()
        if request.method == 'POST':
            serializer = FedatacionSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(lote=lote)
                lote.estado = 'certificado'
                lote.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            fed = lote.fedatacion
            serializer = FedatacionSerializer(fed)
            return Response(serializer.data)
        except Fedatacion.DoesNotExist:
            return Response({'detail': 'Sin fedatación'}, status=status.HTTP_404_NOT_FOUND)


class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = DocumentoDigital.objects.all()
    serializer_class = DocumentoDigitalSerializer

    @action(detail=False, methods=['get'])
    def catalog(self, request):
        docs = DocumentoDigital.objects.all().order_by('-created_at')
        serializer = DocumentoDigitalSerializer(docs, many=True)
        return Response({
            'count': docs.count(),
            'results': serializer.data,
        })


class EtapaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EtapaPipeline.objects.all()
    serializer_class = EtapaPipelineSerializer


class FedatacionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Fedatacion.objects.all()
    serializer_class = FedatacionSerializer


def dashboard(request):
    docs = DocumentoDigital.objects.all().order_by('-created_at')[:50]
    lotes = LoteDigitalizacion.objects.all().order_by('-created_at')[:20]
    total = DocumentoDigital.objects.count()
    pendientes_qc1 = DocumentoDigital.objects.filter(ocr_engine='pending', converted_to_pdf_a=False).count()
    convertidos_pdfa = DocumentoDigital.objects.filter(converted_to_pdf_a=True).count()
    tipos = DocumentoDigital.objects.values('tipo').annotate(c=Count('id')).order_by('-c')
    tipos_choices = [(item['tipo'], item['c']) for item in tipos]

    context = {
        'docs': docs,
        'lotes': lotes,
        'stats': {
            'total': total,
            'pendientes_qc1': pendientes_qc1,
            'convertidos_pdfa': convertidos_pdfa,
        },
        'tipos': tipos_choices,
        'conteos_tipo': {item['tipo']: item['c'] for item in tipos},
        'now': None,
    }
    return render(request, 'digitalizacion/home.html', context)


def ejemplo_m360(request):
    return render(request, 'digitalizacion/ejemplo_m360.html')


def recepcion(request):
    lotes = LoteDigitalizacion.objects.filter(estado='preparacion').order_by('-created_at')
    stats = {
        'lotes': lotes.count(),
    }

    form_lote = LoteDigitalizacionForm()

    helpers = {
        'checklist': [
            'Inventario físico verificado contra registros declarados',
            'Archivo de origen documentado',
            'Responsable de entrega registrado',
            'Fecha y hora de recepción registrada',
            'Condición general del lote evaluada',
        ],
        'nomenclatura': {
            'documento': 'upn_YYYY-MM-DD_NNN',
            'lote': 'LOTE_YYYYMMDD_NNN',
        },
        'manual_link': '/digitalizacion/docs/PIPELINE.md',
        'qm_plan': 'NARA 36 CFR 1236 Subpart E',
        'siguiente_etapa': 'preparacion',
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'crear_lote':
            form_lote = LoteDigitalizacionForm(request.POST)
            if form_lote.is_valid():
                lote = form_lote.save(commit=False)
                lote.estado = 'preparacion'
                lote.created_by = request.user if request.user.is_authenticated else None
                lote.save()
                messages.success(request, f"Lote '{lote.nombre}' creado y registrado en recepción.")
                return redirect('digitalizacion:recepcion')
            else:
                messages.error(request, "Error al crear lote. Verifica los datos.")
        elif action == 'cerrar_recepcion':
            lote_id = request.POST.get('lote_id')
            if lote_id:
                try:
                    lote = LoteDigitalizacion.objects.get(id=lote_id, estado='preparacion')
                    docs_count = lote.documentos.count()
                    if docs_count == 0:
                        messages.error(request, "No se puede cerrar recepción: el lote no tiene documentos.")
                    else:
                        lote.acta_recepcion = (
                            f"Acta de recepción — lote {lote.nombre}. "
                            f"Documentos: {docs_count}. "
                            f"Folios totales: {sum(d.folios or 0 for d in lote.documentos.all())}. "
                            f"Responsable: {request.user.get_full_name() if request.user.is_authenticated else 'Anónimo'}. "
                            f"Fecha: {timezone.now().date().isoformat()}. "
                            f"QM plan: NARA 36 CFR 1236 Subpart E."
                        )
                        lote.save()
                        EtapaPipeline.objects.create(
                            lote=lote,
                            documento=None,
                            etapa='recepcion',
                            estado='ok',
                            inicio=timezone.now(),
                            fin=timezone.now(),
                            usuario=request.user if request.user.is_authenticated else None,
                            observaciones=f"Recepción cerrada. {docs_count} documentos registrados.",
                            metadata={
                                'documentos': docs_count,
                                'folios': sum(d.folios or 0 for d in lote.documentos.all()),
                                'checklist': helpers['checklist'],
                                'qm_plan': helpers['qm_plan'],
                            },
                        )
                        EtapaPipeline.objects.create(
                            lote=lote,
                            documento=None,
                            etapa='preparacion',
                            estado='en_progreso',
                            inicio=timezone.now(),
                            fin=None,
                            usuario=request.user if request.user.is_authenticated else None,
                            observaciones=f"Preparación iniciada. {docs_count} documentos pendientes de acondicionamiento físico.",
                            metadata={
                                'documentos_pendientes': docs_count,
                                'folios_esperados': sum(d.folios or 0 for d in lote.documentos.all()),
                            },
                        )
                        messages.success(request, f"Lote '{lote.nombre}' recibido formalmente. Ahora debe realizar la preparación física.")
                except LoteDigitalizacion.DoesNotExist:
                    messages.error(request, "Lote no encontrado o ya fue cerrado.")
            else:
                messages.error(request, "Debes seleccionar un lote para cerrar.")
            return redirect('digitalizacion:recepcion')

    return render(request, 'digitalizacion/recepcion.html', {
        'lotes': lotes,
        'stats': stats,
        'form_lote': form_lote,
        'helpers': helpers,
    })


def recepcion_lote_detail(request, lote_id):
    lote = get_object_or_404(LoteDigitalizacion, pk=lote_id)
    documentos = lote.documentos.all().order_by('-created_at')
    total_folios = sum(d.folios or 0 for d in documentos)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cerrar_recepcion':
            return redirect('digitalizacion:recepcion')
        if action == 'editar_lote':
            form = LoteDigitalizacionForm(request.POST, instance=lote)
            if form.is_valid():
                form.save()
                messages.success(request, 'Lote actualizado.')
                return redirect('digitalizacion:recepcion_lote_detail', lote_id=lote.id)
            else:
                messages.error(request, 'Error al actualizar lote. Verifica los datos.')
        elif action == 'eliminar_lote':
            if lote.documentos.exists():
                messages.error(request, 'No se puede eliminar un lote con documentos.')
                return redirect('digitalizacion:recepcion_lote_detail', lote_id=lote.id)
            lote.delete()
            messages.success(request, 'Lote eliminado.')
            return redirect('digitalizacion:recepcion')
    else:
        form = LoteDigitalizacionForm(instance=lote)
    return render(request, 'digitalizacion/recepcion_lote_detail.html', {
        'lote': lote,
        'documentos': documentos,
        'form': form,
        'total_folios': total_folios,
    })


def recepcion_lote_detail(request, lote_id):
    lote = get_object_or_404(LoteDigitalizacion, pk=lote_id)
    documentos = lote.documentos.all().order_by('-created_at')
    total_folios = sum(d.folios or 0 for d in documentos)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cerrar_recepcion':
            return redirect('digitalizacion:recepcion')
        if action == 'editar_lote':
            form = LoteDigitalizacionForm(request.POST, instance=lote)
            if form.is_valid():
                form.save()
                messages.success(request, 'Lote actualizado.')
                return redirect('digitalizacion:recepcion_lote_detail', lote_id=lote.id)
            else:
                messages.error(request, 'Error al actualizar lote. Verifica los datos.')
        elif action == 'eliminar_lote':
            if lote.documentos.exists():
                messages.error(request, 'No se puede eliminar un lote con documentos.')
                return redirect('digitalizacion:recepcion_lote_detail', lote_id=lote.id)
            lote.delete()
            messages.success(request, 'Lote eliminado.')
            return redirect('digitalizacion:recepcion')
    else:
        form = LoteDigitalizacionForm(instance=lote)
    return render(request, 'digitalizacion/recepcion_lote_detail.html', {
        'lote': lote,
        'documentos': documentos,
        'form': form,
        'total_folios': total_folios,
    })


def recepcion_documento_detail(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, pk=documento_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'editar_documento':
            form = DocumentoDigitalForm(request.POST, instance=doc, lote=doc.lote)
            if form.is_valid():
                form.save()
                messages.success(request, 'Documento actualizado.')
                return redirect('digitalizacion:recepcion_documento_detail', documento_id=doc.id)
            else:
                messages.error(request, 'Error al actualizar documento. Verifica los datos.')
        elif action == 'eliminar_documento':
            lote_id = doc.lote.id
            doc.delete()
            messages.success(request, 'Documento eliminado.')
            return redirect('digitalizacion:recepcion_lote_detail', lote_id=lote_id)
    else:
        form = DocumentoDigitalForm(instance=doc, lote=doc.lote)
    return render(request, 'digitalizacion/recepcion_documento_detail.html', {
        'doc': doc,
        'lote': doc.lote,
        'form': form,
    })


def preparacion(request):
    lotes_qs = LoteDigitalizacion.objects.filter(estado='preparacion').order_by('-created_at')
    lotes = [l for l in lotes_qs if l.etapas.filter(etapa='recepcion', estado='ok').exists()]
    documentos = DocumentoDigital.objects.filter(lote__estado='preparacion', lote__etapas__etapa='recepcion', lote__etapas__estado='ok').distinct().order_by('-created_at')
    stats = {
        'lotes': len(lotes),
        'documentos': documentos.count(),
        'folios_pendientes': sum(d.folios or 0 for d in documentos),
    }

    form_doc = DocumentoDigitalForm()

    helpers = {
        'checklist': [
            'Sin grapas ni clips',
            'Sin objetos ajenos',
            'Orden verificado',
            'Foliado aplicado si corresponde',
            'Estado de conservación documentado',
        ],
        'nomenclatura': {
            'documento': 'upn_YYYY-MM-DD_NNN',
            'lote': 'LOTE_YYYYMMDD_NNN',
        },
        'manual_link': '/digitalizacion/docs/PIPELINE.md',
        'qm_plan': 'NARA 36 CFR 1236 Subpart E',
    }

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'agregar_documento':
            form_doc = DocumentoDigitalForm(request.POST)
            if form_doc.is_valid():
                doc = form_doc.save(commit=False)
                doc.save()
                messages.success(request, f"Documento '{doc.document_id}' agregado al lote.")
                return redirect('digitalizacion:preparacion')
            else:
                messages.error(request, "Error al agregar documento. Verifica los datos.")
        elif action == 'cerrar_preparacion':
            lote_id = request.POST.get('lote_id')
            if lote_id:
                try:
                    lote = LoteDigitalizacion.objects.get(id=lote_id, estado='preparacion')
                    if not lote.etapas.filter(etapa='recepcion', estado='ok').exists():
                        messages.error(request, "El lote no tiene recepción cerrada. Cierre la recepción primero.")
                        return redirect('digitalizacion:preparacion')
                    docs_qs = lote.documentos.all()
                    checklist_ok = True
                    checklist_detalle = []
                    for doc in docs_qs:
                        faltantes = []
                        if doc.grapas_detectadas:
                            faltantes.append('grapas detectadas')
                        if doc.objetos_ajenos:
                            faltantes.append('objetos ajenos')
                        if not doc.foliado_aplicado and doc.tipo.lower() in [
                            'plan de estudios', 'examen', 'acta', 'certificado', 'resolución'
                        ]:
                            faltantes.append('foliado pendiente')
                        if not doc.estado_conservacion:
                            faltantes.append('estado de conservación vacío')
                        if faltantes:
                            checklist_ok = False
                            checklist_detalle.append(f"{doc.document_id}: {', '.join(faltantes)}")
                    if not checklist_ok:
                        messages.error(
                            request,
                            'No se puede cerrar preparación: ' + '; '.join(checklist_detalle)
                        )
                    else:
                        lote.estado = 'digitalizacion'
                        lote.acta_recepcion = (
                            f"Acta de recepción — lote {lote.nombre}. "
                            f"Documentos: {docs_qs.count()}. "
                            f"Responsable: {request.user.get_full_name() if request.user.is_authenticated else 'Anónimo'}. "
                            f"Fecha: {timezone.now().date().isoformat()}."
                        )
                        lote.save()
                        EtapaPipeline.objects.create(
                            lote=lote,
                            documento=None,
                            etapa='preparacion',
                            estado='ok',
                            inicio=timezone.now(),
                            fin=timezone.now(),
                            usuario=request.user if request.user.is_authenticated else None,
                            observaciones=f"Preparación cerrada. {docs_qs.count()} documentos registrados.",
                            metadata={
                                'documentos': docs_qs.count(),
                                'checklist': helpers['checklist'],
                            },
                        )
                        EtapaPipeline.objects.create(
                            lote=lote,
                            documento=None,
                            etapa='digitalizacion',
                            estado='en_progreso',
                            inicio=timezone.now(),
                            fin=None,
                            usuario=request.user if request.user.is_authenticated else None,
                            observaciones=f"Digitalización iniciada. {docs_qs.count()} documentos pendientes de captura.",
                            metadata={
                                'documentos_pendientes': docs_qs.count(),
                            },
                        )
                        messages.success(request, f"Lote '{lote.nombre}' cerrado y pasado a digitalización.")
                except LoteDigitalizacion.DoesNotExist:
                    messages.error(request, "Lote no encontrado o ya fue cerrado.")
            else:
                messages.error(request, "Debes seleccionar un lote para cerrar.")
            return redirect('digitalizacion:preparacion_lote_detail', lote_id=lote.id)

    return render(request, 'digitalizacion/preparacion.html', {
        'lotes': lotes,
        'documentos': documentos,
        'stats': stats,
        'form_doc': form_doc,
        'helpers': helpers,
    })


def preparacion_lote_detail(request, lote_id):
    lote = get_object_or_404(LoteDigitalizacion, pk=lote_id)
    if not lote.etapas.filter(etapa='recepcion', estado='ok').exists():
        messages.error(request, 'El lote no tiene recepción cerrada. Cierre la recepción primero.')
        return redirect('digitalizacion:recepcion')
    documentos = lote.documentos.all().order_by('-created_at')
    total_folios = sum(d.folios or 0 for d in documentos)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cerrar_preparacion':
            return redirect('digitalizacion:preparacion')
        if action == 'editar_lote':
            form = LoteDigitalizacionForm(request.POST, instance=lote)
            if form.is_valid():
                form.save()
                messages.success(request, 'Lote actualizado.')
                return redirect('digitalizacion:preparacion_lote_detail', lote_id=lote.id)
            else:
                messages.error(request, 'Error al actualizar lote. Verifica los datos.')
        elif action == 'eliminar_lote':
            if lote.documentos.exists():
                messages.error(request, 'No se puede eliminar un lote con documentos.')
                return redirect('digitalizacion:preparacion_lote_detail', lote_id=lote.id)
            lote.delete()
            messages.success(request, 'Lote eliminado.')
            return redirect('digitalizacion:preparacion')
    else:
        form = LoteDigitalizacionForm(instance=lote)
    return render(request, 'digitalizacion/preparacion_lote_detail.html', {
        'lote': lote,
        'documentos': documentos,
        'form': form,
        'total_folios': total_folios,
    })


def preparacion_documento_detail(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, pk=documento_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'editar_documento':
            form = DocumentoDigitalForm(request.POST, instance=doc, lote=doc.lote)
            if form.is_valid():
                form.save()
                messages.success(request, 'Documento actualizado.')
                return redirect('digitalizacion:preparacion_documento_detail', documento_id=doc.id)
            else:
                messages.error(request, 'Error al actualizar documento. Verifica los datos.')
        elif action == 'eliminar_documento':
            lote_id = doc.lote.id
            doc.delete()
            messages.success(request, 'Documento eliminado.')
            return redirect('digitalizacion:preparacion_lote_detail', lote_id=lote_id)
    else:
        form = DocumentoDigitalForm(instance=doc, lote=doc.lote)
    return render(request, 'digitalizacion/preparacion_documento_detail.html', {
        'doc': doc,
        'lote': doc.lote,
        'form': form,
    })


def acceso_pdf(request, documento_id, filename=None):
    try:
        doc = DocumentoDigital.objects.get(id=documento_id)
    except DocumentoDigital.DoesNotExist:
        raise Http404("Documento no encontrado")

    if filename:
        inbox_path = Path(doc.ruta_inbox)
        if inbox_path.is_file():
            inbox_path = inbox_path.parent
        if not inbox_path.is_dir():
            raise Http404("Inbox no disponible")
        file_path = inbox_path / filename
        if not file_path.exists() or not file_path.is_file():
            raise Http404("Archivo no encontrado")
        return FileResponse(file_path.open('rb'))
    
    ruta = doc.ruta_acceso
    if not ruta:
        raise Http404("Documento sin PDF/A generado")

    path = Path(ruta)
    if not path.exists():
        raise Http404("Archivo no encontrado")

    return FileResponse(path.open('rb'), content_type='application/pdf')


def procesar_documento(request, documento_id):
    from digitalizacion.services.pipeline import PipelineDigitalizacion
    from pathlib import Path
    import os
    
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    lote = doc.lote
    
    if request.method == 'POST':
        etapa = request.POST.get('etapa', 'preprocesamiento')
        avanzar = request.POST.get('avanzar') == '1'
        
        # Manejar subida de archivos a inbox
        if request.FILES.getlist('inbox_files'):
            if not doc.ruta_inbox:
                base = Path(lote.ruta_base) if lote.ruta_base else Path('/tmp/digitalizacion')
                inbox_dir = base / 'inbox' / doc.document_id
                inbox_dir.mkdir(parents=True, exist_ok=True)
                doc.ruta_inbox = str(inbox_dir)
                doc.save(update_fields=['ruta_inbox'])
            
            inbox_path = Path(doc.ruta_inbox)
            inbox_path.mkdir(parents=True, exist_ok=True)
            for f in request.FILES.getlist('inbox_files'):
                dest = inbox_path / f.name
                with open(dest, 'wb+') as destino:
                    for chunk in f.chunks():
                        destino.write(chunk)
        
        pipeline = PipelineDigitalizacion(lote)
        logs = []
        
        try:
            if avanzar:
                etapas_completadas = set(
                    doc.etapas.values_list('etapa', flat=True)
                )
                pipeline_order = [
                    'preparacion', 'digitalizacion', 'qc1', 'preprocesamiento',
                    'metadatos', 'qc2', 'auditoria', 'fedatacion', 'certificado'
                ]
                
                start_idx = 0
                for i, e in enumerate(pipeline_order):
                    if e not in etapas_completadas:
                        start_idx = i
                        break
                
                for e in pipeline_order[start_idx:]:
                    if e in etapas_completadas:
                        continue
                    try:
                        resultado = pipeline.ejecutar_etapa(
                            documento=doc,
                            etapa=e,
                            usuario=request.user if request.user.is_authenticated else None,
                        )
                        logs.append(resultado)
                        if resultado.get('ok'):
                            etapas_completadas.add(e)
                        else:
                            break
                    except Exception as ex:
                        logs.append({'ok': False, 'etapa': e, 'error': str(ex)})
                        break
            else:
                resultado = pipeline.ejecutar_etapa(
                    documento=doc,
                    etapa=etapa,
                    usuario=request.user if request.user.is_authenticated else None,
                )
                logs.append(resultado)
                
        except Exception as e:
            logs.append({'ok': False, 'error': str(e)})
        
        doc.refresh_from_db()
        
        context = {
            'doc': doc,
            'lote': lote,
            'logs': logs,
            'etapas': LoteDigitalizacion.ESTADO_CHOICES,
        }
        return render(request, 'digitalizacion/procesar.html', context)
    
    context = {
        'doc': doc,
        'lote': lote,
        'logs': [],
        'etapas': LoteDigitalizacion.ESTADO_CHOICES,
    }
    return render(request, 'digitalizacion/procesar.html', context)


# Etapa 4: Preprocesamiento
def preprocesamiento_documento(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    ctx = _get_pipeline_context(documento_id, 'preprocesamiento')
    
    if not ctx['puede_acceder']:
        messages.error(request, "Completa CC1 antes del preprocesamiento.")
        return redirect('digitalizacion:cc1_documento', documento_id=documento_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        usuario = request.user if request.user.is_authenticated else None
        
        if action == 'aprobar':
            from digitalizacion.services.pipeline import PipelineDigitalizacion
            pipeline = PipelineDigitalizacion(doc.lote)
            resultado = pipeline.ejecutar_etapa(documento=doc, etapa='preprocesamiento', usuario=usuario, estado='ok')
            messages.success(request, "Preprocesamiento aprobado. Documento pasa a metadatos.")
        elif action == 'rechazar':
            motivo = request.POST.get('motivo', 'Sin motivo')
            from digitalizacion.services.pipeline import PipelineDigitalizacion
            pipeline = PipelineDigitalizacion(doc.lote)
            resultado = pipeline.ejecutar_etapa(documento=doc, etapa='preprocesamiento', usuario=usuario, estado='rechazado', observaciones=motivo)
            messages.error(request, f"Preprocesamiento rechazado: {motivo}")
        
        return redirect('digitalizacion:preprocesamiento_documento', documento_id=documento_id)
    
    return render(request, 'digitalizacion/etapas/preprocesamiento.html', ctx)


# ============================================================
# LÍNEA DE PRODUCCIÓN — VISTAS POR ETAPA
# ============================================================

ETAPA_ORDER = [
    'preparacion', 'digitalizacion', 'qc1', 'preprocesamiento',
    'metadatos', 'qc2', 'auditoria', 'fedatacion', 'certificado'
]

ETAPA_LABELS = {
    'preparacion': 'Preparación',
    'digitalizacion': 'Digitalización',
    'qc1': 'Control de Calidad 1',
    'preprocesamiento': 'Preprocesamiento',
    'metadatos': 'Metadatos + OCR',
    'qc2': 'Control de Calidad 2',
    'auditoria': 'Auditoría',
    'fedatacion': 'Fedatación',
    'certificado': 'Certificado',
}

ETAPA_DESCRIPTIONS = {
    'preparacion': 'Recepción, acondicionamiento y registro del documento.',
    'digitalizacion': 'Captura por escáner. Imágenes crudas en inbox.',
    'qc1': 'Control de calidad 1: orientación, recortes, sombras, desenfoque.',
    'preprocesamiento': 'Deskew + denoise. Imágenes corregidas en preprocessed.',
    'metadatos': 'Dublin Core + PREMIS + OCR + microformato JSON.',
    'qc2': 'Validación de metadatos, PDF/A-2b, checksum y confianza OCR.',
    'auditoria': 'Bitácora, eventos PREMIS y reporte de calidad.',
    'fedatacion': 'Certificación de integridad: SHA-256 + timestamp.',
    'certificado': 'Documento certificado y listo para archivado.',
}


def _get_pipeline_context(documento_id, etapa_actual=None):
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    lote = doc.lote
    etapas_completadas = set(doc.etapas.values_list('etapa', flat=True))
    
    # Determinar siguiente etapa si no se especifica
    if etapa_actual is None:
        for e in ETAPA_ORDER:
            if e not in etapas_completadas:
                etapa_actual = e
                break
        else:
            etapa_actual = 'certificado'
    
    # Validar secuencia
    idx = ETAPA_ORDER.index(etapa_actual) if etapa_actual in ETAPA_ORDER else -1
    etapa_prev = ETAPA_ORDER[idx - 1] if idx > 0 else None
    puede_acceder = True
    if etapa_prev and etapa_prev not in etapas_completadas and etapa_actual not in ('preparacion', 'digitalizacion'):
        puede_acceder = False
    
    pipeline_timeline = []
    for e in ETAPA_ORDER:
        pipeline_timeline.append({
            'key': e,
            'label': ETAPA_LABELS.get(e, e),
            'completed': e in etapas_completadas,
            'current': e == etapa_actual,
            'description': ETAPA_DESCRIPTIONS.get(e, ''),
        })
    
    return {
        'doc': doc,
        'lote': lote,
        'etapa_actual': etapa_actual,
        'etapa_label': ETAPA_LABELS.get(etapa_actual, etapa_actual),
        'etapa_description': ETAPA_DESCRIPTIONS.get(etapa_actual, ''),
        'puede_acceder': puede_acceder,
        'pipeline_timeline': pipeline_timeline,
        'etapas': LoteDigitalizacion.ESTADO_CHOICES,
    }


def _ejecutar_etapa_y_redirigir(doc, etapa, usuario, request, template_name, extra_context=None):
    from digitalizacion.services.pipeline import PipelineDigitalizacion
    pipeline = PipelineDigitalizacion(doc.lote)
    logs = []
    try:
        resultado = pipeline.ejecutar_etapa(
            documento=doc,
            etapa=etapa,
            usuario=usuario,
        )
        logs.append(resultado)
    except Exception as ex:
        logs.append({'ok': False, 'etapa': etapa, 'error': str(ex)})
    
    doc.refresh_from_db()
    context = {
        'doc': doc,
        'lote': doc.lote,
        'logs': logs,
        'etapa_actual': etapa,
        'etapa_label': ETAPA_LABELS.get(etapa, etapa),
        'etapa_description': ETAPA_DESCRIPTIONS.get(etapa, ''),
        'pipeline_timeline': _get_pipeline_context(doc.id, etapa)['pipeline_timeline'],
        'etapas': LoteDigitalizacion.ESTADO_CHOICES,
    }
    if extra_context:
        context.update(extra_context)
    return render(request, template_name, context)


# Etapa 1: Preparación (ya existe como vista `preparacion`)

# Etapa 2: Digitalización / captura
def digitalizar_documento(request, documento_id):
    from digitalizacion.services.scanner import ScannerService
    from pathlib import Path
    import os
    
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    ctx = _get_pipeline_context(documento_id, 'digitalizacion')
    scanner = ScannerService()
    scan_devices = []
    scan_error = None
    
    try:
        raw = scanner.listar()
        if raw.startswith('Error:'):
            scan_error = raw
        else:
            scan_devices = []
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('-'):
                    continue
                parts = line.split()
                if parts and parts[0].isdigit():
                    scan_devices.append(line)
    except Exception as e:
        scan_error = str(e)
    
    ctx['scan_devices'] = scan_devices
    ctx['scan_error'] = scan_error
    
    if not ctx['puede_acceder']:
        messages.error(request, "Completa la etapa de preparación antes de digitalizar.")
        return redirect('digitalizacion:preparacion')
    
    scan_result = None
    upload_message = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'completar_digitalizacion':
            usuario = request.user if request.user.is_authenticated else None
            from digitalizacion.services.pipeline import PipelineDigitalizacion
            pipeline = PipelineDigitalizacion(doc.lote)
            resultado = pipeline.ejecutar_etapa(documento=doc, etapa='digitalizacion', usuario=usuario, estado='ok')
            if resultado.get('ok'):
                messages.success(request, "Digitalización completada. Avanzando a CC1.")
                return redirect('digitalizacion:cc1_documento', documento_id=doc.id)
            else:
                messages.error(request, f"Error al completar digitalización: {resultado.get('error')}")
                return redirect('digitalizacion:digitalizar_documento', documento_id=doc.id)
        
        # Manejar subida de archivos a inbox
        if request.FILES.getlist('inbox_files'):
            if not doc.ruta_inbox:
                ruta_base = (doc.lote.ruta_base or '').strip()
                if not ruta_base or ruta_base == '/':
                    ruta_base = '/tmp/digitalizacion'
                base = Path(ruta_base)
                inbox_dir = base / 'inbox' / doc.document_id
                inbox_dir.mkdir(parents=True, exist_ok=True)
                doc.ruta_inbox = str(inbox_dir)
                doc.save(update_fields=['ruta_inbox'])
            
            inbox_path = Path(doc.ruta_inbox)
            if inbox_path.is_file():
                inbox_path = inbox_path.parent
            inbox_path.mkdir(parents=True, exist_ok=True)
            for f in request.FILES.getlist('inbox_files'):
                dest = inbox_path / f.name
                with open(dest, 'wb+') as destino:
                    for chunk in f.chunks():
                        destino.write(chunk)
            upload_message = f"Imágenes subidas a {inbox_path}"
        
        # Escaneo directo
        scan_enabled = request.POST.get('scan_enabled') == '1'
        if scan_enabled and scan_devices:
            dispositivo_idx = int(request.POST.get('dispositivo_idx', 0))
            dpi = int(request.POST.get('dpi', 300))
            modo_color = request.POST.get('modo_color', 'color')
            formato = request.POST.get('formato', 'jpeg')
            calidad = int(request.POST.get('calidad', 95))
            
            if not doc.ruta_inbox:
                ruta_base = (doc.lote.ruta_base or '').strip()
                if not ruta_base or ruta_base == '/':
                    ruta_base = '/tmp/digitalizacion'
                base = Path(ruta_base)
                inbox_dir = base / 'inbox' / doc.document_id
                inbox_dir.mkdir(parents=True, exist_ok=True)
                doc.ruta_inbox = str(inbox_dir)
                doc.save(update_fields=['ruta_inbox'])
            
            destino = Path(doc.ruta_inbox)
            if destino.is_file():
                destino = destino.parent
            destino.mkdir(parents=True, exist_ok=True)
            
            scan_result = scanner.escanear(
                dispositivo_idx=dispositivo_idx,
                destino=str(destino),
                prefijo=doc.document_id,
                dpi=dpi,
                modo_color=modo_color,
                formato=formato,
                calidad=calidad,
            )
        elif scan_enabled and not scan_devices:
            messages.error(request, "No hay escáner disponible. Conecta un escáner y verifica scanlib.")
    
    # Listar archivos en inbox
    inbox_files = []
    if doc.ruta_inbox:
        inbox_path = Path(doc.ruta_inbox)
        if inbox_path.is_dir():
            inbox_files = sorted([f.name for f in inbox_path.iterdir() if f.is_file()])
        elif inbox_path.is_file():
            inbox_files = [inbox_path.name]
    
    ctx['inbox_files'] = inbox_files
    ctx['scan_result'] = scan_result
    ctx['upload_message'] = upload_message
    ctx['folios_esperados'] = doc.folios or 0
    
    if scan_result and scan_result.get('ok'):
        messages.success(request, f"Escaneo completado: {scan_result.get('files', 0)} páginas generadas.")
    elif scan_result and not scan_result.get('ok'):
        messages.error(request, f"Error en escaneo: {scan_result.get('stderr', scan_result.get('error'))}")
    
    return render(request, 'digitalizacion/etapas/digitalizar.html', ctx)


# Etapa 3: CC1
def cc1_documento(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    ctx = _get_pipeline_context(documento_id, 'qc1')
    
    if not ctx['puede_acceder']:
        messages.error(request, "Completa la etapa de digitalización antes de CC1.")
        return redirect('digitalizacion:digitalizar_documento', documento_id=documento_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        usuario = request.user if request.user.is_authenticated else None
        
        if action == 'aprobar':
            from digitalizacion.services.pipeline import PipelineDigitalizacion
            pipeline = PipelineDigitalizacion(doc.lote)
            resultado = pipeline.ejecutar_etapa(documento=doc, etapa='qc1', usuario=usuario, estado='ok')
            messages.success(request, "CC1 aprobada. Documento pasa a preprocesamiento.")
        elif action == 'rechazar':
            motivo = request.POST.get('motivo', 'Sin motivo')
            from digitalizacion.services.pipeline import PipelineDigitalizacion
            pipeline = PipelineDigitalizacion(doc.lote)
            resultado = pipeline.ejecutar_etapa(documento=doc, etapa='qc1', usuario=usuario, estado='rechazado', observaciones=motivo)
            messages.error(request, f"CC1 rechazada: {motivo}")
        
        return redirect('digitalizacion:cc1_documento', documento_id=documento_id)
    
    return render(request, 'digitalizacion/etapas/cc1.html', ctx)


# Etapa 4: Metadatos + OCR
def metadatos_documento(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    ctx = _get_pipeline_context(documento_id, 'metadatos')
    
    if not ctx['puede_acceder']:
        messages.error(request, "Completa CC1 antes de metadatos.")
        return redirect('digitalizacion:cc1_documento', documento_id=documento_id)
    
    if request.method == 'POST':
        from digitalizacion.services.pipeline import PipelineDigitalizacion
        pipeline = PipelineDigitalizacion(doc.lote)
        usuario = request.user if request.user.is_authenticated else None
        
        # Actualizar metadatos básicos desde formulario
        doc.titulo = request.POST.get('titulo', doc.titulo)
        doc.creator = request.POST.get('creator', doc.creator)
        doc.fecha_documento = request.POST.get('fecha_documento', doc.fecha_documento) or doc.fecha_documento
        doc.language = request.POST.get('language', doc.language) or doc.language
        doc.rights = request.POST.get('rights', doc.rights) or doc.rights
        doc.description = request.POST.get('description', doc.description)
        subject = request.POST.get('subject', '')
        doc.subject = [s.strip() for s in subject.split(',') if s.strip()]
        doc.save()
        
        resultado = pipeline.ejecutar_etapa(documento=doc, etapa='metadatos', usuario=usuario)
        
        if resultado.get('ok'):
            messages.success(request, "Metadatos guardados y OCR ejecutado.")
        else:
            messages.error(request, f"Error en metadatos: {resultado.get('error')}")
        
        return redirect('digitalizacion:metadatos_documento', documento_id=documento_id)
    
    return render(request, 'digitalizacion/etapas/metadatos.html', ctx)


# Etapa 5: QC2
def qc2_documento(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    ctx = _get_pipeline_context(documento_id, 'qc2')
    
    if not ctx['puede_acceder']:
        messages.error(request, "Completa metadatos antes de QC2.")
        return redirect('digitalizacion:metadatos_documento', documento_id=documento_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        usuario = request.user if request.user.is_authenticated else None
        
        if action == 'aprobar':
            from digitalizacion.services.pipeline import PipelineDigitalizacion
            pipeline = PipelineDigitalizacion(doc.lote)
            resultado = pipeline.ejecutar_etapa(documento=doc, etapa='qc2', usuario=usuario, estado='ok')
            if resultado.get('ok'):
                messages.success(request, "QC2 aprobada. Documento pasa a auditoría.")
            else:
                messages.error(request, f"QC2 rechazada: {resultado.get('missing', [])}")
        elif action == 'rechazar':
            motivo = request.POST.get('motivo', 'Sin motivo')
            messages.error(request, f"QC2 rechazada: {motivo}")
        
        return redirect('digitalizacion:qc2_documento', documento_id=documento_id)
    
    return render(request, 'digitalizacion/etapas/qc2.html', ctx)


# Etapa 6: Auditoría
def auditoria_documento(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    ctx = _get_pipeline_context(documento_id, 'auditoria')
    
    if not ctx['puede_acceder']:
        messages.error(request, "Completa QC2 antes de auditoría.")
        return redirect('digitalizacion:qc2_documento', documento_id=documento_id)
    
    if request.method == 'POST':
        usuario = request.user if request.user.is_authenticated else None
        from digitalizacion.services.pipeline import PipelineDigitalizacion
        pipeline = PipelineDigitalizacion(doc.lote)
        resultado = pipeline.ejecutar_etapa(documento=doc, etapa='auditoria', usuario=usuario, estado='ok')
        
        if resultado.get('ok'):
            messages.success(request, "Auditoría completada. Documento pasa a fedatación.")
        else:
            messages.error(request, f"Error en auditoría: {resultado.get('error')}")
        
        return redirect('digitalizacion:auditoria_documento', documento_id=documento_id)
    
    # Obtener bitácora de etapas
    etapas_bitacora = doc.etapas.all().order_by('inicio')
    ctx['etapas_bitacora'] = etapas_bitacora
    
    return render(request, 'digitalizacion/etapas/auditoria.html', ctx)


# Etapa 7: Certificación / Fedatación
def certificar_documento(request, documento_id):
    doc = get_object_or_404(DocumentoDigital, id=documento_id)
    ctx = _get_pipeline_context(documento_id, 'certificado')
    
    if not ctx['puede_acceder']:
        messages.error(request, "Completa auditoría antes de certificar.")
        return redirect('digitalizacion:auditoria_documento', documento_id=documento_id)
    
    if request.method == 'POST':
        usuario = request.user if request.user.is_authenticated else None
        from digitalizacion.services.pipeline import PipelineDigitalizacion
        pipeline = PipelineDigitalizacion(doc.lote)
        
        # Ejecutar certificación (checksum + PDF/A)
        resultado = pipeline.ejecutar_etapa(documento=doc, etapa='certificado', usuario=usuario, estado='ok')
        
        if resultado.get('ok'):
            # Crear registro de fedatación
            from .models import Fedatacion
            if not hasattr(doc.lote, 'fedatacion'):
                Fedatacion.objects.create(
                    lote=doc.lote,
                    fedatario=usuario,
                    certificado_numero=f"CERT-{doc.document_id}",
                    firma_digital=f"SHA256:{resultado.get('checksums', {}).get('sha256', '')}",
                    sello_tiempo=timezone.now(),
                    acta_apertura=f"Acta de apertura - {doc.document_id}",
                    acta_cierre=f"Acta de cierre - {doc.document_id}",
                    hash_lote=resultado.get('checksums', {}).get('sha256', ''),
                )
            messages.success(request, "Documento certificado y fedatado exitosamente.")
        else:
            messages.error(request, f"Error en certificación: {resultado.get('error')}")
        
        return redirect('digitalizacion:certificar_documento', documento_id=documento_id)
    
    return render(request, 'digitalizacion/etapas/certificar.html', ctx)
