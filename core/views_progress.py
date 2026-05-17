
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SessionLogForm
from .models import Client, Exercise, SessionLog, SetLog
from .views_common import app_context

@login_required
def progress_index(request):
    clients = Client.objects.filter(trainer=request.user, is_archived=False).order_by("full_name")
    return render(
        request,
        "progress_index.html",
        {**app_context(request, active_nav="progress"), "clients": clients},
    )

@login_required
def progress_view(request, client_id):
    client = get_object_or_404(Client, pk=client_id, trainer=request.user)

    sets = SetLog.objects.filter(
        session__client=client, session__trainer=request.user
    ).select_related("exercise", "session")

    exercises_used = sorted({s.exercise for s in sets}, key=lambda e: e.name)

    selected_ex_id = request.GET.get("exercise")
    if selected_ex_id is None and exercises_used:
        selected_ex_id = str(exercises_used[0].id)

    top_set_series = []
    if selected_ex_id:
        per_session_top: dict[date, Decimal] = {}
        for s in sets:
            if str(s.exercise_id) != str(selected_ex_id):
                continue
            d = s.session.performed_on
            cur = per_session_top.get(d)
            if cur is None or s.weight_kg > cur:
                per_session_top[d] = s.weight_kg
        top_set_series = [
            {"date": d.isoformat(), "weight": float(w)}
            for d, w in sorted(per_session_top.items())
        ]

    today = date.today()
    eight_weeks_ago = today - timedelta(days=7 * 7)
    weekly_volume = defaultdict(Decimal)
    for s in sets:
        if s.session.performed_on < eight_weeks_ago:
            continue
        wk_start = s.session.performed_on - timedelta(days=s.session.performed_on.weekday())
        weekly_volume[wk_start] += Decimal(s.reps) * s.weight_kg
    weekly_volume_data = [
        {"week": wk.isoformat(), "volume": float(v)}
        for wk, v in sorted(weekly_volume.items())
    ]

    recent_prs = (
        SetLog.objects.filter(
            session__client=client, session__trainer=request.user, is_personal_record=True
        )
        .select_related("exercise", "session")
        .order_by("-session__performed_on")[:8]
    )

    start_h = today - timedelta(days=89)
    session_days = set(
        SessionLog.objects.filter(
            client=client,
            trainer=request.user,
            performed_on__gte=start_h,
        ).values_list("performed_on", flat=True)
    )
    heatmap = []
    cur = start_h
    while cur <= today:
        heatmap.append({"date": cur.isoformat(), "logged": cur in session_days})
        cur += timedelta(days=1)

    total_sessions = SessionLog.objects.filter(
        client=client, trainer=request.user
    ).count()
    total_pr_count = SetLog.objects.filter(
        session__client=client, session__trainer=request.user, is_personal_record=True
    ).count()
    total_volume = SetLog.objects.filter(
        session__client=client, session__trainer=request.user
    ).aggregate(v=Sum("weight_kg"))["v"] or 0

    return render(
        request,
        "progress.html",
        {
            **app_context(request, active_nav="progress"),
            "client": client,
            "exercises_used": exercises_used,
            "selected_ex_id": int(selected_ex_id) if selected_ex_id else None,
            "top_set_series": top_set_series,
            "weekly_volume_data": weekly_volume_data,
            "recent_prs": recent_prs,
            "heatmap": heatmap,
            "total_sessions": total_sessions,
            "total_pr_count": total_pr_count,
            "total_volume": float(total_volume),
        },
    )

@login_required
def session_log_create(request, client_id):

    client = get_object_or_404(Client, pk=client_id, trainer=request.user)
    form = SessionLogForm(
        request.POST or None,
        trainer=request.user,
        client=client,
        initial={"client": client},
    )

    if request.method == "POST" and form.is_valid():
        session = form.save(commit=False)
        session.trainer = request.user
        session.client = client
        session.save()

        exids = request.POST.getlist("set_exercise")
        reps = request.POST.getlist("set_reps")
        weights = request.POST.getlist("set_weight")
        rpes = request.POST.getlist("set_rpe")

        per_ex_counter = defaultdict(int)
        for ex_id, r, w, rpe in zip(exids, reps, weights, rpes):
            if not ex_id or not r:
                continue
            try:
                exercise = Exercise.objects.get(pk=ex_id, trainer=request.user)
            except Exercise.DoesNotExist:
                continue
            per_ex_counter[exercise.id] += 1
            set_no = per_ex_counter[exercise.id]
            weight = Decimal(w or "0")

            prev_max = (
                SetLog.objects.filter(
                    session__client=client,
                    session__trainer=request.user,
                    exercise=exercise,
                )
                .aggregate(m=Max("weight_kg"))["m"] or Decimal("0")
            )
            is_pr = weight > prev_max
            SetLog.objects.create(
                session=session,
                exercise=exercise,
                set_number=set_no,
                reps=int(r),
                weight_kg=weight,
                rpe=Decimal(rpe) if rpe else None,
                is_personal_record=is_pr,
            )

        messages.success(request, "Session logged.")
        return redirect("progress", client_id=client.id)

    exercises = Exercise.objects.filter(trainer=request.user, is_archived=False).order_by("name")
    return render(
        request,
        "session_log_form.html",
        {
            **app_context(request, active_nav="progress"),
            "client": client,
            "form": form,
            "exercises": exercises,
        },
    )
