from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class LoteDigitalizacion(models.Model):
    ESTADO_CHOICES = [
        ('preparacion', 'Preparación'),
        ('digitalizacion', 'Digitalización'),
        ('qc1', 'Control de Calidad 1'),
        ('preprocesamiento', 'Preprocesamiento'),
        ('metadatos', 'Metadatos'),
        ('qc2', 'Control de Calidad 2'),
        ('auditoria', 'Auditoría'),
        ('fedatacion', 'Fedatación'),
        ('certificado', 'Certificado'),
        ('rechazado', 'Rechazado'),
    ]

    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=255)
    proyecto_m360 = models.ForeignKey('events.Project', null=True, blank=True, on_delete=models.SET_NULL)
    curso_m360 = models.ForeignKey('courses.Course', null=True, blank=True, on_delete=models.SET_NULL)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='preparacion')
    ruta_base = models.CharField(max_length=512)
    metadata_proyecto = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='lotes_digitalizacion')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Lote de digitalización'
        verbose_name_plural = 'Lotes de digitalización'

    def __str__(self):
        return self.nombre


class DocumentoDigital(models.Model):
    lote = models.ForeignKey(LoteDigitalizacion, related_name='documentos', on_delete=models.CASCADE)
    document_id = models.CharField(max_length=64, unique=True)
    tipo = models.CharField(max_length=128)
    titulo = models.CharField(max_length=255)
    creator = models.CharField(max_length=255, blank=True)
    subject = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    fecha_documento = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=8, default='es')
    rights = models.CharField(max_length=255, blank=True)
    ruta_inbox = models.CharField(max_length=512)
    ruta_preprocessed = models.CharField(max_length=512)
    ruta_acceso = models.CharField(max_length=512, blank=True)
    ruta_master = models.CharField(max_length=512, blank=True)
    checksum_sha256 = models.CharField(max_length=128, blank=True)
    checksum_md5 = models.CharField(max_length=128, blank=True)
    ocr_engine = models.CharField(max_length=64, default='pending')
    ocr_confidence = models.FloatField(null=True, blank=True)
    converted_to_pdf_a = models.BooleanField(default=False)
    microformato_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Documento digital'
        verbose_name_plural = 'Documentos digitales'

    def __str__(self):
        return f"{self.document_id} — {self.titulo}"


class EtapaPipeline(models.Model):
    ESTADO_CHOICES = [
        ('ok', 'OK'),
        ('error', 'Error'),
        ('rechazado', 'Rechazado'),
    ]

    lote = models.ForeignKey(LoteDigitalizacion, related_name='etapas', on_delete=models.CASCADE)
    documento = models.ForeignKey(DocumentoDigital, null=True, blank=True, on_delete=models.CASCADE, related_name='etapas')
    etapa = models.CharField(max_length=20, choices=LoteDigitalizacion.ESTADO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ok')
    usuario = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-inicio']
        verbose_name = 'Etapa de pipeline'
        verbose_name_plural = 'Etapas de pipeline'

    def __str__(self):
        return f"{self.lote.nombre} → {self.etapa} ({self.estado})"


class Fedatacion(models.Model):
    lote = models.OneToOneField(LoteDigitalizacion, on_delete=models.CASCADE, related_name='fedatacion')
    fedatario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='fedataciones')
    certificado_numero = models.CharField(max_length=128)
    firma_digital = models.TextField()
    sello_tiempo = models.DateTimeField()
    acta_apertura = models.CharField(max_length=512)
    acta_cierre = models.CharField(max_length=512)
    hash_lote = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fedatación'
        verbose_name_plural = 'Fedataciones'

    def __str__(self):
        return f"Fedatación {self.lote.nombre} — {self.fedatario}"
