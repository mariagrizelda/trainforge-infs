
from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import AppointmentForm
from .models import Appointment, Client
from .views_common import app_context

def _week_start(d):
    return d - timedelta(days=d.weekday())

@login_required
def calendar_view(request):
    trainer = request.user
    today = timezone.localdate()
    try:
        anchor = datetime.strptime(request.GET.get("week") or today.isoformat(), "%Y-%m-%d").date()
    except ValueError:
        anchor = today
    week_start = _week_start(anchor)
    week_end = week_start + timedelta(days=7)

    appts = (
        Appointment.objects.filter(
            trainer=trainer,
            is_archived=False,
            start_at__date__gte=week_start,
            start_at__date__lt=week_end,
        )
        .exclude(status=Appointment.Status.CANCELLED)
        .select_related("client")
        .order_by("start_at")
    )

    by_slot = {}
    for a in appts:
        local = timezone.localtime(a.start_at)
        idx = (local.date() - week_start).days
        hour = local.hour
        by_slot.setdefault(idx, {}).setdefault(hour, []).append(a)

    hours = list(range(7, 21))
    days = [(week_start + timedelta(days=i)) for i in range(7)]

    return render(
        request,
        "calendar.html",
        {
            **app_context(request, active_nav="calendar"),
            "days": days,
            "hours": hours,
            "by_slot": by_slot,
            "today": today,
            "week_start": week_start,
            "prev_week": (week_start - timedelta(days=7)).isoformat(),
            "next_week": (week_start + timedelta(days=7)).isoformat(),
            "appts_count": appts.count(),
        },
    )

@login_required
def appointment_create(request):
    initial = {}
    qclient = request.GET.get("client")
    qstart = request.GET.get("start")
    if qclient:
        initial["client"] = qclient
    if qstart:
        try:
            initial["start_at"] = datetime.fromisoformat(qstart)
        except ValueError:
            pass

    form = AppointmentForm(request.POST or None, initial=initial, trainer=request.user)

    conflicts = []
    if request.method == "POST" and form.is_valid():
        appt = form.save(commit=False)
        appt.trainer = request.user

        conflicts = appt.overlapping_qs()
        if conflicts and request.POST.get("force") != "1":
            return render(
                request,
                "appointment_form.html",
                {
                    **app_context(request, active_nav="calendar"),
                    "form": form,
                    "appointment": None,
                    "conflicts": conflicts,
                },
            )
        appt.save()
        messages.success(request, f"Scheduled {appt.client.full_name} at {appt.start_at:%H:%M}.")
        return redirect("calendar")

    return render(
        request,
        "appointment_form.html",
        {
            **app_context(request, active_nav="calendar"),
            "form": form,
            "appointment": None,
            "conflicts": conflicts,
        },
    )

@login_required
def appointment_edit(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, trainer=request.user)
    form = AppointmentForm(request.POST or None, instance=appt, trainer=request.user)
    conflicts = []
    if request.method == "POST" and form.is_valid():
        candidate = form.save(commit=False)
        candidate.trainer = request.user
        candidate.id = appt.id
        conflicts = candidate.overlapping_qs()
        if conflicts and request.POST.get("force") != "1":
            return render(
                request,
                "appointment_form.html",
                {
                    **app_context(request, active_nav="calendar"),
                    "form": form,
                    "appointment": appt,
                    "conflicts": conflicts,
                },
            )
        form.save()
        messages.success(request, "Appointment updated.")
        return redirect("calendar")
    return render(
        request,
        "appointment_form.html",
        {
            **app_context(request, active_nav="calendar"),
            "form": form,
            "appointment": appt,
            "conflicts": conflicts,
        },
    )

@login_required
def appointment_delete(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, trainer=request.user)
    if request.method == "POST":
        appt.delete()
        messages.info(request, "Appointment deleted.")
    return redirect("calendar")
