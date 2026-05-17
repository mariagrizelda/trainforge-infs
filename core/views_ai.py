
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .ai import AIGenerationError, PlanResponse, generate_plan, save_plan
from .models import Client, Exercise
from .views_common import app_context

def _exercise_name_map(trainer):
    return dict(
        Exercise.objects.filter(trainer=trainer).values_list("id", "name")
    )

@login_required
def ai_plan_page(request):

    clients = Client.objects.filter(trainer=request.user, is_archived=False).order_by(
        "full_name"
    )
    selected = None
    cid = request.GET.get("client")
    if cid:
        selected = clients.filter(pk=cid).first()
    return render(
        request,
        "ai_plan.html",
        {
            **app_context(request, active_nav="ai"),
            "clients": clients,
            "selected": selected,
        },
    )

@require_POST
@login_required
def ai_plan_generate(request):

    client = get_object_or_404(
        Client, pk=request.POST.get("client"), trainer=request.user
    )
    try:
        weeks = max(1, min(16, int(request.POST.get("weeks") or 4)))
    except ValueError:
        weeks = 4

    try:
        plan, raw = generate_plan(client, weeks=weeks)
    except AIGenerationError as exc:
        return render(
            request,
            "partials/_ai_plan_error.html",
            {"error": str(exc), "client": client},
        )

    request.session["ai_plan_draft"] = {"client_id": client.id, "plan": plan.model_dump()}

    return render(
        request,
        "partials/_ai_plan_draft.html",
        {
            "plan": plan,
            "client": client,
            "exercise_names": _exercise_name_map(request.user),
        },
    )

@require_POST
@login_required
def ai_plan_save(request):

    draft = request.session.get("ai_plan_draft")
    if not draft:
        return HttpResponse(
            '<div class="alert alert-warning small">Draft expired. Please regenerate.</div>',
            status=400,
        )
    client = get_object_or_404(Client, pk=draft["client_id"], trainer=request.user)
    try:
        plan = PlanResponse.model_validate(draft["plan"])
    except Exception as exc:  # noqa: BLE001
        return HttpResponse(
            f'<div class="alert alert-danger small">Could not parse draft: {exc}</div>',
            status=400,
        )
    tp = save_plan(client, plan)

    request.session.pop("ai_plan_draft", None)
    messages.success(request, f"Saved AI plan for {client.full_name}.")
    return HttpResponse(
        f'<div class="alert alert-success small">'
        f'Saved! <a class="text-decoration-underline" href="/plans/{tp.id}/">Open the plan</a>.'
        f'</div>'
    )
