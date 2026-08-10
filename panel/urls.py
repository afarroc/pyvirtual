# panel/urls.py — enrutador raíz del proyecto
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views import RedisTestView
from bitacora.views import upload_image

urlpatterns = [
    # CKEditor5 (global — requerido por bitacora)
    path('ckeditor5/upload/', upload_image, name='ck_editor_5_upload_file'),

    # Admin
    path('admin/', admin.site.urls),

    # Apps
    path('',           include('core.urls')),
    path('accounts/',  include('accounts.urls')),
    path('analyst/',   include('analyst.urls',  namespace='analyst')),
    path('bitacora/',  include('bitacora.urls', namespace='bitacora')),
    # board eliminado
    path('bots/',      include('bots.urls',     namespace='bots')),
    path('campaigns/', include('campaigns.urls')),
    path('chat/',      include('chat.urls',     namespace='chat')),
    path('courses/',   include('courses.urls')),
    path('cv/',        include('cv.urls',       namespace='cv')),
    path('digitalizacion/', include('digitalizacion.urls', namespace='digitalizacion')),
    path('events/',    include('events.urls')),
    path('gtd/',       include('gtd.urls', namespace='gtd')),
    path('help/',      include('help.urls',     namespace='help')),
    path('kpis/',      include('kpis.urls')),
    path('memento/',   include('memento.urls')),
    path('passgen/',   include('passgen.urls')),
    path('rooms/',     include('rooms.urls',    namespace='rooms')),
    path('sim/',       include('sim.urls',      namespace='sim')),
    path('simcity/',   include('simcity.urls',  namespace='simcity')),

    # API — todos los endpoints viven en api/urls.py (namespace 'api')
    path('api/', include('api.urls', namespace='api')),

    # Diagnóstico Redis (requiere login — ver views.py)
    path('redis-test/', RedisTestView.as_view(), name='redis_test'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Media servido desde servidor remoto Termux — no servir localmente
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
