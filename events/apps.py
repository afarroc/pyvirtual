# apps.py
from django.apps import AppConfig

class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'
    verbose_name = 'events'

    def ready(self):
        import events.templatetags.schedule_filters
        import events.templatetags.custom_tags
        import events.templatetags.signals
        import events.signals  # Importar señales principales
        import events.signals_system_events  # Importar señales de system events
        # import initial_data

        # initial_data.create_default_users() # Eliminado
