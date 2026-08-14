# kpis/models.py
"""
Modelos de métricas de contact center.

KPI-1 Sprint 7:
  - UUID PK (convención del proyecto)
  - `fecha` DateField (convención del proyecto — NO usar semana para filtros)
  - `semana` conservado como campo calculado para compatibilidad con datos existentes
  - Índices compuestos para queries frecuentes
  - `created_by` FK estándar
  - `login_required` en todas las vistas (ver views.py)
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings


SERVICIO_CHOICES = [
    ('Reclamos',   'Reclamos'),
    ('Consultas',  'Consultas'),
    ('Ventas',     'Ventas'),
    ('Soporte',    'Soporte'),
    ('Cobranzas',  'Cobranzas'),
]

CANAL_CHOICES = [
    ('Phone',        'Teléfono'),
    ('Mail',         'Email'),
    ('Chat',         'Chat'),
    ('WhatsApp',     'WhatsApp'),
    ('Social Media', 'Redes Sociales'),
]


class CallRecord(models.Model):
    """
    Registro de métricas semanales por agente / servicio / canal.

    Convención de fechas (proyecto):
      `fecha`  → DateField — usar para filtros de rango temporal
      `semana` → IntegerField — conservado para compatibilidad (semana ISO)

    Integración analyst ETL:
      ETL source type 'model' → app: kpis, model: CallRecord
      Orden: fecha ASC, agente ASC
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Dimensiones temporales
    fecha        = models.DateField(
        verbose_name='Fecha',
        help_text='Primer día de la semana a la que corresponde el registro',
        db_index=True,
    )
    semana       = models.IntegerField(
        verbose_name='Semana',
        help_text='Número de semana ISO (calculado de fecha)',
        db_index=True,
    )

    # Dimensiones de negocio
    agente       = models.CharField('Agente', max_length=100, db_index=True)
    supervisor   = models.CharField('Supervisor', max_length=100, db_index=True)
    servicio     = models.CharField('Servicio', max_length=50, choices=SERVICIO_CHOICES, db_index=True)
    canal        = models.CharField('Canal', max_length=50, choices=CANAL_CHOICES, db_index=True)

    # Métricas
    eventos      = models.IntegerField('Eventos', validators=[MinValueValidator(0)])
    aht          = models.FloatField('AHT (segundos)', validators=[MinValueValidator(0)])
    evaluaciones = models.IntegerField('Evaluaciones', default=0, validators=[MinValueValidator(0)])
    satisfaccion = models.FloatField(
        'Satisfacción (1-10)', default=0.0,
        validators=[MinValueValidator(0)],
    )

    # Métricas avanzadas (nuevas)
    resolved_on_first_call = models.BooleanField('Resuelto en primera llamada', default=False)
    abandoned              = models.BooleanField('Llamada abandonada', default=False)
    asa                    = models.FloatField('ASA (segundos)', default=0.0, validators=[MinValueValidator(0)])
    hora                   = models.TimeField('Hora del evento', null=True, blank=True, db_index=True)

    # Auditoría
    created_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='call_records',
        verbose_name='Creado por',
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Registro de llamadas'
        verbose_name_plural = 'Registros de llamadas'
        ordering            = ['-fecha', 'agente']
        indexes = [
            # Query principal: dashboard por rango de fechas
            models.Index(fields=['fecha', 'servicio'],      name='kpis_cr_fecha_serv'),
            models.Index(fields=['fecha', 'canal'],         name='kpis_cr_fecha_canal'),
            models.Index(fields=['fecha', 'agente'],        name='kpis_cr_fecha_agente'),
            models.Index(fields=['fecha', 'supervisor'],    name='kpis_cr_fecha_sup'),
            # Query por semana (compatibilidad)
            models.Index(fields=['semana', 'servicio'],     name='kpis_cr_sem_serv'),
        ]

    def __str__(self):
        return f"{self.agente} — {self.fecha} (sem {self.semana})"

    def save(self, *args, **kwargs):
        # Auto-calcular semana desde fecha si no se provee
        if self.fecha and not self.semana:
            self.semana = self.fecha.isocalendar()[1]
        super().save(*args, **kwargs)

    @property
    def aht_min(self):
        """AHT en minutos (2 decimales)."""
        return round(self.aht / 60, 2)


class ExchangeRate(models.Model):
    """
    Tasas de cambio PEN/USD por mes.
    Usa `date` = primer día del mes.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date       = models.DateField(
        verbose_name='Fecha de referencia',
        help_text='Primer día del mes al que corresponde la tasa',
        unique=True,
        db_index=True,
    )
    rate       = models.DecimalField(
        verbose_name='Tasa de cambio',
        max_digits=10,
        decimal_places=6,
        validators=[MinValueValidator(0)],
        help_text='Tasa promedio PEN/USD — Compra interbancaria',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-date']
        verbose_name        = 'Tasa de Cambio'
        verbose_name_plural = 'Tasas de Cambio'

    def __str__(self):
        return f"{self.date.strftime('%b%y').lower()}: {self.rate} PEN/USD"

    @property
    def period(self):
        """Compatibilidad con formato MmmYY."""
        return self.date.strftime('%b%y').lower()
