"""
Servicio de Captura GTD
Responsabilidad: Gestionar la entrada de items al sistema
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from events.models import InboxItem, InboxItemHistory

User = get_user_model()
logger = logging.getLogger(__name__)


class CaptureService:
    SOURCE_CHOICES = [
        ('manual', 'Captura Manual'),
        ('email', 'Correo Electrónico'),
        ('quick_add', 'Agregado Rápido'),
        ('bulk', 'Captura Masiva'),
        ('voice', 'Comando de Voz'),
        ('api', 'API Externa'),
        ('calendar', 'Calendario'),
        ('integration', 'Integración'),
    ]
    
    def __init__(self, user):
        self.user = user
        self.logger = logging.getLogger(__name__)
    
    def capture_item(
        self,
        title: str,
        description: str = '',
        source: str = 'manual',
        context: Optional[Dict[str, Any]] = None,
        priority: str = 'media',
        due_date: Optional[datetime] = None,
        tags: List[str] = None,
        auto_deduplicate: bool = True
    ) -> InboxItem:
        if not title or not title.strip():
            raise ValueError("El título es obligatorio")
        
        normalized_title = self._normalize_text(title)
        
        if auto_deduplicate:
            duplicates = self._find_duplicates(title, description)
            if duplicates:
                self.logger.info(f"Potencial duplicado detectado: '{title}' ({len(duplicates)} similar(es))")
        
        # Construir notas con información de fuente y contexto
        extra_notes = []
        if source:
            extra_notes.append(f"Fuente: {source}")
        if context:
            if isinstance(context, dict):
                extra_notes.append(f"Contexto: {str(context)}")
            else:
                extra_notes.append(f"Contexto: {context}")
        
        # Usar el campo context del modelo para almacenar el contexto
        context_value = str(context) if context else ''
        
        with transaction.atomic():
            inbox_item = InboxItem.objects.create(
                title=title,
                description=description or '',
                created_by=self.user,
                gtd_category='pendiente',
                priority=priority,
                due_date=due_date,
                context=context_value,  # Usar el campo context del modelo
                notes='\n'.join(extra_notes) if extra_notes else '',
                is_processed=False
            )
            
            InboxItemHistory.objects.create(
                inbox_item=inbox_item,
                user=self.user,
                action='captured',
                new_values={
                    'title': title,
                    'source': source,
                    'priority': priority,
                    'has_description': bool(description)
                }
            )
            
            self._notify_capture(inbox_item)
        
        return inbox_item
    
    def _normalize_text(self, text: str) -> str:
        import re
        if not text:
            return ""
        return re.sub(r'[^\w\s]', '', text.lower().strip())
    
    def _find_duplicates(self, title: str, description: str = '', threshold: float = 0.7) -> List[Dict]:
        normalized_title = self._normalize_text(title)
        normalized_description = self._normalize_text(description)
        
        recent_items = InboxItem.objects.filter(
            Q(created_by=self.user) | Q(assigned_to=self.user),
            is_processed=False,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        duplicates = []
        for item in recent_items:
            item_title = self._normalize_text(item.title)
            item_desc = self._normalize_text(item.description or '')
            
            title_sim = SequenceMatcher(None, normalized_title, item_title).ratio()
            
            if normalized_description and item_desc:
                desc_sim = SequenceMatcher(None, normalized_description, item_desc).ratio()
                overall_sim = (title_sim * 0.7) + (desc_sim * 0.3)
            else:
                overall_sim = title_sim
            
            if overall_sim >= threshold:
                duplicates.append({
                    'item': item,
                    'similarity': overall_sim,
                    'title_similarity': title_sim
                })
        
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        return duplicates
    
    def _notify_capture(self, item: InboxItem):
        self.logger.info(f"Item capturado: {item.title} por {self.user.username}")
    
    def get_capture_stats(self) -> Dict[str, int]:
        inbox_items = InboxItem.objects.filter(
            Q(created_by=self.user) | Q(assigned_to=self.user)
        ).distinct()
        
        return {
            'total': inbox_items.count(),
            'processed': inbox_items.filter(is_processed=True).count(),
            'unprocessed': inbox_items.filter(is_processed=False).count(),
            'high_priority': inbox_items.filter(priority='alta', is_processed=False).count(),
            'medium_priority': inbox_items.filter(priority='media', is_processed=False).count(),
            'low_priority': inbox_items.filter(priority='baja', is_processed=False).count(),
        }
    
    def get_today_count(self) -> int:
        today = timezone.now().date()
        start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        return InboxItem.objects.filter(
            Q(created_by=self.user) | Q(assigned_to=self.user),
            created_at__range=(start, end)
        ).count()
    
    def get_week_count(self) -> int:
        week_ago = timezone.now() - timedelta(days=7)
        return InboxItem.objects.filter(
            Q(created_by=self.user) | Q(assigned_to=self.user),
            created_at__gte=week_ago
        ).count()
    
    def get_capture_rate(self) -> float:
        stats = self.get_capture_stats()
        if stats['total'] == 0:
            return 0.0
        return round((stats['processed'] / stats['total']) * 100, 1)
    
    def get_unprocessed_items(self, limit: int = 50) -> List[InboxItem]:
        return InboxItem.objects.filter(
            Q(created_by=self.user) | Q(assigned_to=self.user),
            is_processed=False
        ).distinct().order_by('-priority', '-created_at')[:limit]
    
    def get_processed_items(self, days: int = 7, limit: int = 20) -> List[InboxItem]:
        cutoff = timezone.now() - timedelta(days=days)
        return InboxItem.objects.filter(
            Q(created_by=self.user) | Q(assigned_to=self.user),
            is_processed=True,
            processed_at__gte=cutoff
        ).distinct().order_by('-processed_at')[:limit]
    
    def get_capture_trend(self, days=7):
        """
        Obtiene la tendencia de captura en los últimos días
        """
        from django.db.models import Count
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        trend = InboxItem.objects.filter(
            created_by=self.user,
            created_at__gte=start_date,
            created_at__lte=end_date
        ).extra(
            select={'date': "DATE(created_at)"}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return trend
    
    def get_processed_trend(self, days=7):
        """
        Obtiene la tendencia de procesamiento en los últimos días
        """
        from django.db.models import Count
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        trend = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=True,
            processed_at__gte=start_date,
            processed_at__lte=end_date
        ).extra(
            select={'date': "DATE(processed_at)"}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return trend
    
    def get_gtd_categories_distribution(self):
        """
        Obtiene la distribución de categorías GTD para análisis
        """
        from django.db.models import Count
        
        categories = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=True,
            gtd_category__in=['accionable', 'no_accionable']
        ).values('gtd_category').annotate(
            count=Count('id')
        )
        
        return {item['gtd_category']: item['count'] for item in categories}
    
    def get_action_types_distribution(self):
        """
        Obtiene la distribución de tipos de acción
        """
        from django.db.models import Count
        
        actions = InboxItem.objects.filter(
            created_by=self.user,
            is_processed=True,
            action_type__isnull=False
        ).values('action_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(actions)