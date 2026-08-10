from django.contrib.auth.decorators import login_required
from django.shortcuts import render

class GTDViewMixin:
    pass

def gtd_context(request):
    return {'user': request.user}
