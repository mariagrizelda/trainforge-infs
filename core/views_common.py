
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Client, Exercise

def app_context(request, active_nav: str | None = None) -> dict:

    counts = {}
    if request.user.is_authenticated:
        counts = {
            "client_count": Client.objects.filter(
                trainer=request.user, is_archived=False
            ).count(),
            "exercise_count": Exercise.objects.filter(
                trainer=request.user, is_archived=False
            ).count(),
        }
    return {"active_nav": active_nav, **counts}

def today_window():
    today = timezone.localdate()
    start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end = start + timedelta(days=1)
    return start, end

trainer_required = login_required
