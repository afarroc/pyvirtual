from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rooms.models import Cell, Message

@login_required
def last_room_api(request):
    user = request.user
    last_message = Message.objects.filter(user=user).order_by('-timestamp').first()
    if last_message:
        return JsonResponse({'room_name': str(last_message.room.id)})
    # Si no hay historial, usar 'global'
    return JsonResponse({'room_name': 'global'})
