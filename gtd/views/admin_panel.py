from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    return render(request, 'gtd/admin_panel/dashboard.html', {
        'title': 'Panel Admin GTD',
    })

@login_required
def settings(request):
    return render(request, 'gtd/admin_panel/settings.html', {
        'title': 'Configuración GTD',
    })

@login_required
def audit_log(request):
    return render(request, 'gtd/admin_panel/audit_log.html', {
        'title': 'Auditoría GTD',
    })
