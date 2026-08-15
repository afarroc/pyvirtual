# kpis/views.py
"""
Sprint 7 — KPI-2, KPI-3, KPI-4, KPI-5, KPI-6:
  - login_required en todas las vistas
  - Caching Redis en dashboard (TTL 5 minutos)
  - Namespace corregido en redirects
  - Exportación optimizada con StreamingHttpResponse
  - API JSON para integración con analyst
  - Filtros por fecha (convención del proyecto)
"""

import json
import csv
import uuid
import logging
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Avg, Case, Count, ExpressionWrapper, F, FloatField, IntegerField, Max, Min, Sum, When
from django.db.models.functions import Cast
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import UploadCSVForm, DataGenerationForm
from .models import CallRecord, ExchangeRate

logger = logging.getLogger(__name__)

# ── Cache keys ────────────────────────────────────────────────────────────────
_CACHE_TTL    = 60 * 5   # 5 minutos
_CACHE_PREFIX = 'kpis:dashboard'


# ── Excepciones custom ───────────────────────────────────────────────────────
class DashboardPerformanceError(Exception):
    """Se lanza cuando la generación del dashboard excede el tiempo máximo permitido."""
    pass


class EmptyDashboardDataError(Exception):
    """Se lanza cuando no hay datos suficientes para construir el dashboard."""
    pass


def _cache_key(user_id, suffix=''):
    return f"{_CACHE_PREFIX}:{user_id}:{suffix}"


# ── Helpers ───────────────────────────────────────────────────────────────────

CHART_COLORS = [
    'rgba(59,130,246,0.7)',   # blue
    'rgba(16,185,129,0.7)',   # green
    'rgba(245,158,11,0.7)',   # amber
    'rgba(239,68,68,0.7)',    # red
    'rgba(167,139,250,0.7)',  # purple
    'rgba(45,212,191,0.7)',   # teal
]


def _build_chart(queryset, label_key, value_key='avg_aht'):
    """Construye dict para Chart.js desde un queryset anotado."""
    items = list(queryset)
    return {
        'labels':           [item[label_key] for item in items],
        'data':             [round(float(item[value_key]), 2) for item in items],
        'backgroundColors': [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(items))],
    }


def _get_trend_percentage(current, previous):
    """Calcula porcentaje de cambio entre dos valores."""
    if previous in (0, None):
        return 0
    return round(((current - previous) / previous) * 100, 1)


def _calculate_service_level(qs, threshold_seconds=20):
    """Calcula Service Level: % de llamadas atendidas en < threshold_seconds."""
    total = qs.count()
    if total == 0:
        return 0
    atendidas_en_umbral = qs.filter(aht__lte=threshold_seconds).count()
    return round((atendidas_en_umbral / total) * 100, 1)


def _calculate_fcr(qs):
    """First Call Resolution: % de resolución en primera llamada."""
    total = qs.count()
    if total == 0:
        return 0
    fcr_count = qs.filter(resolved_on_first_call=True).count()
    return round((fcr_count / total) * 100, 1)


def _calculate_abandon_rate(qs):
    """Abandon Rate: % de llamadas abandonadas."""
    total = qs.count()
    if total == 0:
        return 0
    abandoned = qs.filter(abandoned=True).count()
    return round((abandoned / total) * 100, 1)


def _service_level_by_group(qs, field, threshold_seconds=20):
    """Calcula Service Level agrupado por un campo en una sola consulta."""
    return list(
        qs.values(field)
        .annotate(
            total=Count('id'),
            atendidas=Count(
                Case(
                    When(aht__lte=threshold_seconds, then=1),
                    output_field=IntegerField(),
                )
            ),
        )
        .annotate(
            sl=ExpressionWrapper(
                Cast(F('atendidas'), FloatField()) * 100.0 / Cast(F('total'), FloatField()),
                output_field=FloatField(),
            )
        )
        .order_by('-sl')
    )


def _get_heatmap_data(qs):
    """Genera datos para heatmap por hora y día de la semana en una sola consulta."""
    from django.db.models import Count
    from django.db.models.functions import ExtractWeekDay, TruncHour

    counts = qs.exclude(hora__isnull=True).annotate(
        weekday=ExtractWeekDay('fecha'),
        hour=TruncHour('hora'),
    ).values('weekday', 'hour').annotate(
        count=Count('id')
    )

    count_map = {}
    for item in counts:
        if item['hour'] is None:
            continue
        hour_val = item['hour'].hour
        weekday_val = item['weekday']
        count_map[(weekday_val, hour_val)] = item['count']

    heatmap = []
    for hour in range(24):
        row = {'hora': f'{hour:02d}:00', 'dias': []}
        for day in range(7):
            django_weekday = (day + 1) % 7 + 1
            count = count_map.get((django_weekday, hour), 0)
            color = 'var(--gray-50)'
            if count > 30:
                color = 'var(--purple-light)'
            elif count > 20:
                color = 'var(--amber-light)'
            elif count > 10:
                color = 'var(--blue-light)'
            row['dias'].append({'valor': count, 'color': color})
        heatmap.append(row)
    return heatmap


def _date_range_from_request(request):
    """Extrae fecha_desde / fecha_hasta del request.GET.
    Si no se proveen, devuelve últimas 12 semanas."""
    today = date.today()
    default_from = today - timedelta(weeks=12)
    try:
        fecha_desde = date.fromisoformat(request.GET.get('desde', str(default_from)))
        fecha_hasta = date.fromisoformat(request.GET.get('hasta', str(today)))
    except ValueError:
        fecha_desde = default_from
        fecha_hasta = today
    return fecha_desde, fecha_hasta


# =============================================================================
# Views
# =============================================================================

@login_required
def kpi_home(request):
    total = CallRecord.objects.count()
    return render(request, 'kpis/home.html', {'total_records': total})


@login_required
def sections_examples(request):
    return render(request, 'kpis/sections_examples.html')


@login_required
def aht_dashboard(request):
    """
    Dashboard mejorado con métricas SL, FCR, abandonos, heatmap y rankings.
    KPI-2: Caching Redis 5 minutos por usuario + rango de fechas.
    """
    fecha_desde, fecha_hasta = _date_range_from_request(request)
    cache_key = _cache_key(request.user.id, f"{fecha_desde}:{fecha_hasta}")

    ctx = cache.get(cache_key)
    if ctx is None:
        qs = CallRecord.objects.filter(fecha__gte=fecha_desde, fecha__lte=fecha_hasta)

        # Período anterior para tendencias
        delta = fecha_hasta - fecha_desde
        qs_anterior = CallRecord.objects.filter(
            fecha__gte=fecha_desde - delta,
            fecha__lt=fecha_desde,
        )

        try:
            start = timezone.now()
            # ---- Métricas Principales ----
            aht_por_servicio = list(qs.values('servicio').annotate(
                avg_aht=Avg('aht'), total_eventos=Count('id'), total_registros=Count('id')
            ).order_by('-avg_aht'))
            aht_por_canal = list(qs.values('canal').annotate(
                avg_aht=Avg('aht'), total_eventos=Count('id')
            ).order_by('-avg_aht'))
            aht_por_semana = list(qs.values('semana').annotate(
                avg_aht=Avg('aht'), total_eventos=Count('id')
            ).order_by('semana'))
            aht_por_supervisor = list(qs.values('supervisor').annotate(
                avg_aht=Avg('aht'), total_eventos=Count('id'),
                avg_sat=Avg('satisfaccion')
            ).order_by('-avg_aht'))
            aht_por_agente = list(qs.values('agente').annotate(
                avg_aht=Avg('aht'), total_eventos=Count('id'),
                avg_sat=Avg('satisfaccion')
            ).order_by('avg_aht')[:20])

            totales = qs.aggregate(
                total_llamadas=Count('id'),
                aht_promedio=Avg('aht'),
                sat_promedio=Avg('satisfaccion'),
                total_eventos=Sum('eventos'),
                total_evals=Sum('evaluaciones'),
                asa_promedio=Avg('asa'),
            )
            totales_anterior = qs_anterior.aggregate(
                total_llamadas=Count('id'),
                aht_promedio=Avg('aht'),
            )

            if totales['total_llamadas'] == 0:
                raise EmptyDashboardDataError('No hay registros en el rango seleccionado.')

            # ---- Service Level ----
            sl_general = _calculate_service_level(qs)
            sl_por_servicio = _service_level_by_group(qs, 'servicio')
            sl_por_canal = _service_level_by_group(qs, 'canal')

            # ---- FCR y Abandon Rate ----
            fcr_rate = _calculate_fcr(qs)
            abandon_rate = _calculate_abandon_rate(qs)

            # ---- CSAT ----
            csat_por_servicio = list(qs.values('servicio').annotate(
                avg_sat=Avg('satisfaccion'),
                total=Count('id')
            ).order_by('-avg_sat'))

            # ---- Heatmap ----
            heatmap_data = _get_heatmap_data(qs)

            # ---- Top/Bottom Agentes ----
            agentes = qs.values('agente').annotate(
                avg_aht=Avg('aht'),
                total=Count('id'),
                avg_sat=Avg('satisfaccion')
            ).filter(total__gte=5)
            top_agentes = list(agentes.order_by('avg_aht')[:10])
            bottom_agentes = list(agentes.order_by('-avg_aht')[:10])

            elapsed = (timezone.now() - start).total_seconds()
            if elapsed > 8:
                raise DashboardPerformanceError(f'El dashboard tardó {elapsed:.2f}s en generarse.')

            ctx = {
                # Chart data
                'chart_data_json': json.dumps(_build_chart(aht_por_servicio, 'servicio'), ensure_ascii=False),
                'aht_por_canal_json': json.dumps(_build_chart(aht_por_canal, 'canal'), ensure_ascii=False),
                'aht_por_semana_json': json.dumps(_build_chart(aht_por_semana, 'semana'), ensure_ascii=False),
                'aht_por_agente_json': json.dumps(_build_chart(aht_por_agente, 'agente'), ensure_ascii=False),

                # Tablas
                'aht_por_servicio': aht_por_servicio,
                'aht_por_canal': aht_por_canal,
                'aht_por_semana': aht_por_semana,
                'aht_por_supervisor': aht_por_supervisor,
                'aht_por_agente': aht_por_agente,

                # KPIs resumen
                'total_llamadas': totales['total_llamadas'] or 0,
                'aht_promedio': round(totales['aht_promedio'] or 0, 2),
                'aht_promedio_min': round((totales['aht_promedio'] or 0) / 60, 2),
                'sat_promedio': round(totales['sat_promedio'] or 0, 2),
                'total_eventos': totales['total_eventos'] or 0,
                'total_evals': totales['total_evals'] or 0,
                'asa_promedio': round(totales['asa_promedio'] or 0, 2),

                # Tendencias
                'total_llamadas_trend': _get_trend_percentage(
                    totales['total_llamadas'], totales_anterior['total_llamadas']
                ),
                'total_llamadas_trend_abs': abs(_get_trend_percentage(
                    totales['total_llamadas'], totales_anterior['total_llamadas']
                )),
                'aht_trend': _get_trend_percentage(
                    totales['aht_promedio'], totales_anterior['aht_promedio']
                ),
                'aht_trend_abs': abs(_get_trend_percentage(
                    totales['aht_promedio'], totales_anterior['aht_promedio']
                )),

                # Service Level
                'service_level': sl_general,
                'sl_por_servicio': sl_por_servicio,
                'sl_por_canal': sl_por_canal,
                'fcr_rate': fcr_rate,
                'abandon_rate': abandon_rate,

                # CSAT
                'csat_promedio': round(totales['sat_promedio'] or 0, 2),
                'csat_por_servicio': csat_por_servicio,

                # Heatmap
                'heatmap_data': heatmap_data,

                # Rankings
                'top_agentes': top_agentes,
                'bottom_agentes': bottom_agentes,

                'servicio_mas_alto': max(sl_por_servicio, key=lambda x: x['sl'], default=None),
                'servicio_mas_bajo': min(sl_por_servicio, key=lambda x: x['sl'], default=None),

                'cached_at': timezone.now().isoformat(),
            }
            cache.set(cache_key, ctx, timeout=_CACHE_TTL)

        except EmptyDashboardDataError as e:
            logger.warning('aht_dashboard empty data: %s', e)
            return render(request, 'kpis/dashboard_error.html', {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'error_title': 'Sin datos para el período seleccionado',
                'error_message': str(e) or 'No se encontraron registros en el rango de fechas consultado.',
                'error_type': 'empty_data',
            })
        except DashboardPerformanceError as e:
            logger.error('aht_dashboard performance: %s', e)
            return render(request, 'kpis/dashboard_error.html', {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'error_title': 'El dashboard tardó demasiado en generarse',
                'error_message': str(e) or 'La generación del dashboard excedió el tiempo máximo permitido. Intenta reducir el rango de fechas.',
                'error_type': 'performance',
            })
        except Exception as e:
            logger.error('aht_dashboard error: %s', e, exc_info=True)
            return render(request, 'kpis/dashboard_error.html', {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'error_title': 'Error interno al generar el dashboard',
                'error_message': 'Ocurrió un error inesperado. Por favor, intenta nuevamente.',
                'error_type': 'internal',
            })

    ctx.update({
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })
    return render(request, 'kpis/dashboard.html', ctx)


@login_required
def kpi_api(request):
    """
    KPI-3: API JSON para integración con analyst ETL y Dashboard.
    GET /kpis/api/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD&format=summary|records
    """
    fecha_desde, fecha_hasta = _date_range_from_request(request)
    fmt = request.GET.get('format', 'summary')

    qs = CallRecord.objects.filter(fecha__gte=fecha_desde, fecha__lte=fecha_hasta)

    if fmt == 'records':
        # Lista paginada de registros
        page     = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 100)), 500)
        offset   = (page - 1) * per_page
        total    = qs.count()
        records  = list(qs.values(
            'id', 'fecha', 'semana', 'agente', 'supervisor',
            'servicio', 'canal', 'eventos', 'aht', 'evaluaciones', 'satisfaccion',
        )[offset:offset+per_page])
        # Serializar UUID y date
        for r in records:
            r['id']    = str(r['id'])
            r['fecha'] = str(r['fecha'])
        return JsonResponse({
            'success': True,
            'total': total, 'page': page, 'per_page': per_page,
            'records': records,
        })

    # Summary (default)
    summary = qs.aggregate(
        total     = Count('id'),
        avg_aht   = Avg('aht'),
        avg_sat   = Avg('satisfaccion'),
        max_aht   = Max('aht'),
        min_aht   = Min('aht'),
        total_ev  = Sum('eventos'),
    )
    by_serv = list(qs.values('servicio').annotate(
        total=Count('id'), avg_aht=Avg('aht')).order_by('-avg_aht'))
    by_canal = list(qs.values('canal').annotate(
        total=Count('id'), avg_aht=Avg('aht')).order_by('-avg_aht'))

    return JsonResponse({
        'success':  True,
        'desde':    str(fecha_desde),
        'hasta':    str(fecha_hasta),
        'summary':  {k: round(v, 4) if isinstance(v, float) else v for k, v in summary.items()},
        'by_servicio': by_serv,
        'by_canal':    by_canal,
    })


@login_required
def export_data(request):
    """
    KPI-6: Exportación optimizada con StreamingHttpResponse.
    Soporta filtros de fecha: ?desde=&hasta=
    """
    fecha_desde, fecha_hasta = _date_range_from_request(request)
    qs = CallRecord.objects.filter(
        fecha__gte=fecha_desde, fecha__lte=fecha_hasta
    ).order_by('fecha', 'agente').values(
        'fecha', 'semana', 'agente', 'supervisor',
        'servicio', 'canal', 'eventos', 'aht', 'evaluaciones', 'satisfaccion',
    )

    def rows():
        yield ['fecha', 'semana', 'agente', 'supervisor', 'servicio',
               'canal', 'eventos', 'aht', 'evaluaciones', 'satisfaccion']
        for r in qs.iterator(chunk_size=500):
            yield [r['fecha'], r['semana'], r['agente'], r['supervisor'],
                   r['servicio'], r['canal'], r['eventos'],
                   r['aht'], r['evaluaciones'], r['satisfaccion']]

    class EchoWriter:
        def write(self, value): return value

    writer  = csv.writer(EchoWriter())
    response = StreamingHttpResponse(
        (writer.writerow(row) for row in rows()),
        content_type='text/csv; charset=utf-8-sig',
    )
    fname = f"call_records_{fecha_desde}_{fecha_hasta}.csv"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


@login_required
def generate_fake_data(request):
    """Genera datos sintéticos para testing."""
    if request.method == 'POST':
        form = DataGenerationForm(request.POST)
        if form.is_valid():
            try:
                from faker import Faker
                import random
                import numpy as np

                if form.cleaned_data.get('clear_existing'):
                    CallRecord.objects.all().delete()
                    messages.info(request, "Datos existentes eliminados.")

                fake = Faker('es_ES')
                np.random.seed(form.cleaned_data.get('random_seed') or None)

                weeks        = form.cleaned_data['weeks']
                recs_per_wk  = form.cleaned_data['records_per_week']
                services     = form.cleaned_data['services']
                channels     = form.cleaned_data['channels']
                num_agents   = form.cleaned_data['num_agents']
                num_sups     = form.cleaned_data['num_supervisors']

                agentes      = [fake.unique.name() for _ in range(num_agents)]
                supervisores = [fake.unique.name() for _ in range(num_sups)]
                sup_dist     = np.random.dirichlet(np.ones(num_sups), size=1)[0]

                # Fecha base = hoy menos N semanas
                base_date = date.today() - timedelta(weeks=weeks)

                records = []
                for week_idx in range(weeks):
                    semana_fecha = base_date + timedelta(weeks=week_idx)
                    semana_num   = semana_fecha.isocalendar()[1]
                    for _ in range(recs_per_wk):
                        servicio = random.choices(services, weights=form.cleaned_data['service_weights'], k=1)[0]
                        canal    = random.choices(channels, weights=form.cleaned_data['channel_weights'], k=1)[0]
                        sup_idx  = np.random.choice(range(num_sups), p=sup_dist)

                        if servicio == 'Reclamos':
                            eventos = int(np.random.normal(85, 10))
                            aht     = np.random.normal(1350, 100)
                            sat     = np.random.normal(7.0, 0.8)
                        elif servicio == 'Consultas':
                            eventos = int(np.random.normal(45, 10))
                            aht     = np.random.normal(400 if canal != 'Mail' else 1100, 50)
                            sat     = np.random.normal(6.5, 0.7)
                        else:
                            eventos = int(np.random.normal(55, 12))
                            aht     = np.random.normal(900, 200)
                            sat     = np.random.normal(7.5, 0.5)

                        if canal in ['Chat', 'WhatsApp', 'Social Media']:
                            aht = max(200, aht * 0.35)

                        records.append(CallRecord(
                            fecha        = semana_fecha,
                            semana       = semana_num,
                            agente       = random.choice(agentes),
                            supervisor   = supervisores[sup_idx],
                            servicio     = servicio,
                            canal        = canal,
                            eventos      = max(5, min(150, eventos)),
                            aht          = round(max(100, min(2000, aht)), 2),
                            evaluaciones = random.randint(
                                form.cleaned_data['min_evaluations'],
                                form.cleaned_data['max_evaluations'],
                            ),
                            satisfaccion = round(max(1.0, min(10.0, sat)), 2),
                            created_by   = request.user,
                            hora         = datetime.time(
                                hour=random.randint(8, 18),
                                minute=random.randint(0, 59),
                            ),
                            asa          = round(random.uniform(5, 30), 2),
                            resolved_on_first_call = random.random() < 0.7,
                            abandoned              = random.random() < 0.1,
                        ))

                batch_size = form.cleaned_data.get('batch_size', 500)
                CallRecord.objects.bulk_create(records, batch_size=batch_size)

                # Invalidar cache del usuario
                cache.delete_pattern(f"{_CACHE_PREFIX}:{request.user.id}:*") \
                    if hasattr(cache, 'delete_pattern') else None

                messages.success(request, f'{weeks * recs_per_wk} registros generados.')
                return redirect('kpis:dashboard')

            except Exception as e:
                logger.error("generate_fake_data: %s", e, exc_info=True)
                messages.error(request, f'Error: {e}')
                return redirect('kpis:generate_data')
    else:
        form = DataGenerationForm()

    return render(request, 'kpis/generate_data.html', {'form': form})
