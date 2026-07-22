from django.contrib import admin
from .models import LoteDigitalizacion, DocumentoDigital, EtapaPipeline, Fedatacion

@admin.register(LoteDigitalizacion)
class LoteDigitalizacionAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'estado', 'created_by', 'created_at']
    list_filter = ['estado', 'created_at']
    search_fields = ['nombre', 'ruta_base']

@admin.register(DocumentoDigital)
class DocumentoDigitalAdmin(admin.ModelAdmin):
    list_display = ['document_id', 'titulo', 'tipo', 'lote', 'converted_to_pdf_a', 'ocr_engine', 'created_at']
    list_filter = ['tipo', 'converted_to_pdf_a', 'ocr_engine', 'created_at']
    search_fields = ['document_id', 'titulo']

@admin.register(EtapaPipeline)
class EtapaPipelineAdmin(admin.ModelAdmin):
    list_display = ['lote', 'etapa', 'estado', 'usuario', 'inicio', 'fin']
    list_filter = ['etapa', 'estado', 'inicio']

@admin.register(Fedatacion)
class FedatacionAdmin(admin.ModelAdmin):
    list_display = ['lote', 'fedatario', 'certificado_numero', 'sello_tiempo', 'created_at']
    list_filter = ['sello_tiempo', 'created_at']
    search_fields = ['certificado_numero', 'lote__nombre']
