
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Appointment, Client, SessionLog, SetLog, TrainingPlan, User
from .views_common import app_context, today_window

@login_required
def dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("admin_dashboard")
    trainer = request.user
    today_start, today_end = today_window()
    week_start = today_start - timedelta(days=today_start.weekday())
    week_end = week_start + timedelta(days=7)
    month_start = today_start.replace(day=1)

    today_appts = (
        Appointment.objects.filter(
            trainer=trainer,
            is_archived=False,
            start_at__gte=today_start,
            start_at__lt=today_end,
        )
        .exclude(status=Appointment.Status.CANCELLED)
        .select_related("client")
        .order_by("start_at")
    )

    week_appts_count = (
        Appointment.objects.filter(
            trainer=trainer,
            is_archived=False,
            start_at__gte=week_start,
            start_at__lt=week_end,
        )
        .exclude(status=Appointment.Status.CANCELLED)
        .count()
    )
    completed_this_week = Appointment.objects.filter(
        trainer=trainer,
        is_archived=False,
        start_at__gte=week_start,
        start_at__lt=week_end,
        status=Appointment.Status.COMPLETED,
    ).count()

    active_clients = Client.objects.filter(trainer=trainer, is_archived=False)
    ai_plans_this_month = TrainingPlan.objects.filter(
        trainer=trainer, generated_by_ai=True, created_at__gte=month_start
    ).count()
    new_prs_recent = SetLog.objects.filter(
        session__trainer=trainer,
        is_personal_record=True,
        session__performed_on__gte=today_start.date() - timedelta(days=7),
    ).count()

    recent_activity = SessionLog.objects.filter(trainer=trainer).order_by(
        "-performed_on"
    )[:5]

    attention = []
    for c in active_clients:
        plan = c.active_plan
        last_session = c.session_logs.order_by("-performed_on").first()
        reason = None
        if plan is None:
            reason = "No training plan assigned yet."
        elif plan.current_week >= plan.weeks:
            reason = "Current plan finishes this week."
        elif last_session is None or (
            today_start.date() - last_session.performed_on
        ) > timedelta(days=7):
            reason = "Missed sessions recently."
        if reason:
            attention.append((c, reason))
    attention = attention[:3]

    next_up = today_appts.first() if today_appts else None

    timeline = []
    track_start_min = 8 * 60
    track_total_min = 12 * 60
    for a in today_appts:
        local = timezone.localtime(a.start_at)
        offset_min = local.hour * 60 + local.minute - track_start_min
        if offset_min < 0 or offset_min >= track_total_min:
            continue
        width_min = min(a.duration_minutes, track_total_min - offset_min)
        timeline.append(
            {
                "appt": a,
                "left_pct": offset_min / track_total_min * 100,
                "width_pct": width_min / track_total_min * 100,
                "is_next": next_up is not None and a.id == next_up.id,
                "local_time": local,
            }
        )

    return render(
        request,
        "dashboard.html",
        {
            **app_context(request, active_nav="dashboard"),
            "today_appts": today_appts,
            "next_up": next_up,
            "timeline": timeline,
            "stat_active": active_clients.count(),
            "stat_week_appts": week_appts_count,
            "stat_completed_week": completed_this_week,
            "stat_ai_plans": ai_plans_this_month,
            "stat_new_prs": new_prs_recent,
            "recent_activity": recent_activity,
            "attention": attention,
            "today": timezone.localdate(),
        },
    )
