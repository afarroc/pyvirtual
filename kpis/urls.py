# kpis/urls.py
from django.urls import path
from . import views

app_name = 'kpis'

urlpatterns = [
    path('',                      views.kpi_home,           name='home'),
    path('dashboard/',            views.aht_dashboard,      name='dashboard'),
    path('api/',                  views.kpi_api,             name='api'),
    path('export/',               views.export_data,         name='export_data'),
    path('generate-data/',        views.generate_fake_data,  name='generate_data'),
    path('sections-examples/',    views.sections_examples,   name='sections_examples'),
]
