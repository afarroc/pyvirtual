import uuid
import json
import re

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class CategoriaChoices(models.TextChoices):
    PERSONAL   = 'personal',   'Personal'
    VIAJE      = 'viaje',      'Viaje'
    TRABAJO    = 'trabajo',    'Trabajo'
    META       = 'meta',       'Meta'
    IDEA       = 'idea',       'Idea'
    RECUERDO   = 'recuerdo',   'Recuerdo'
    DIARIO     = 'diario',     'Diario'
    REFLEXION  = 'reflexion',  'Reflexión'


class MoodChoices(models.TextChoices):
    MUY_BIEN   = 'muy_bien',   '😄 Muy bien'
    BIEN       = 'bien',       '🙂 Bien'
    NEUTRAL    = 'neutral',    '😐 Neutral'
    MAL        = 'mal',        '😕 Mal'
    MUY_MAL    = 'muy_mal',    '😞 Muy mal'


class BitacoraEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo    = models.CharField(max_length=200)
    contenido = models.TextField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bitacora_entries',
    )
    categoria = models.CharField(
        max_length=50,
        choices=CategoriaChoices.choices,
        default=CategoriaChoices.PERSONAL,
    )
    mood = models.CharField(
        max_length=20,
        choices=MoodChoices.choices,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    related_event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bitacora_entries',
    )
    related_task = models.ForeignKey(
        'events.Task',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bitacora_entries',
    )
    related_project = models.ForeignKey(
        'events.Project',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bitacora_entries',
    )
    related_room = models.ForeignKey(
        'rooms.Cell',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bitacora_entries',
    )
    tags = models.ManyToManyField('events.Tag', blank=True)
    structured_content = models.JSONField(
        default=list,
        blank=True,
        help_text="Bloques de contenido estructurado insertados desde courses",
    )
    latitud  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    fecha_creacion      = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Entrada de Bitácora"
        verbose_name_plural = "Entradas de Bitácora"

    def __str__(self):
        return f"{self.titulo} - {self.created_by.username}"

    def get_structured_content_blocks(self):
        """Devuelve la lista de bloques de contenido estructurado."""
        return self.structured_content if self.structured_content else []


class BitacoraAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class TipoChoices(models.TextChoices):
        IMAGE    = 'image',    'Imagen'
        AUDIO    = 'audio',    'Audio'
        VIDEO    = 'video',    'Video'
        DOCUMENT = 'document', 'Documento'

    entry       = models.ForeignKey(BitacoraEntry, on_delete=models.CASCADE, related_name='attachments')
    archivo     = models.FileField(upload_to='bitacora/attachments/')
    tipo        = models.CharField(max_length=20, choices=TipoChoices.choices)
    descripcion = models.CharField(max_length=200, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adjunto de Bitácora"
        verbose_name_plural = "Adjuntos de Bitácora"

    def __str__(self):
        return f"{self.tipo} - {self.entry.titulo}"
