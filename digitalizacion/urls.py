from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'lotes', views.LoteViewSet, basename='lote')
router.register(r'documentos', views.DocumentoViewSet, basename='documento')
router.register(r'etapas', views.EtapaViewSet, basename='etapa')
router.register(r'fedatacion', views.FedatacionViewSet, basename='fedatacion')

app_name = 'digitalizacion'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('ejemplo-m360/', views.ejemplo_m360, name='ejemplo_m360'),
    path('preparacion/', views.preparacion, name='preparacion'),
    path('preparacion/lote/<int:lote_id>/', views.preparacion_lote_detail, name='preparacion_lote_detail'),
    path('preparacion/documento/<int:documento_id>/', views.preparacion_documento_detail, name='preparacion_documento_detail'),
    path('acceso/<int:documento_id>/', views.acceso_pdf, name='acceso_pdf'),
    path('acceso/<int:documento_id>/<str:filename>/', views.acceso_pdf, name='acceso_pdf_file'),
    path('procesar/<int:documento_id>/', views.procesar_documento, name='procesar_documento'),
    path('preprocesamiento/<int:documento_id>/', views.preprocesamiento_documento, name='preprocesamiento_documento'),
    # Línea de producción por etapas
    path('digitalizar/<int:documento_id>/', views.digitalizar_documento, name='digitalizar_documento'),
    path('cc1/<int:documento_id>/', views.cc1_documento, name='cc1_documento'),
    path('metadatos/<int:documento_id>/', views.metadatos_documento, name='metadatos_documento'),
    path('qc2/<int:documento_id>/', views.qc2_documento, name='qc2_documento'),
    path('auditoria/<int:documento_id>/', views.auditoria_documento, name='auditoria_documento'),
    path('certificar/<int:documento_id>/', views.certificar_documento, name='certificar_documento'),
]
