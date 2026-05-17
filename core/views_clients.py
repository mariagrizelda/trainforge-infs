
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ClientForm
from .models import Client
from .views_common import app_context

def _scoped(request):
    return Client.objects.filter(trainer=request.user)

@login_required
def clients_list(request):
    q = (request.GET.get("q") or "").strip()
    goal = request.GET.get("goal") or ""

    qs = _scoped(request)
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q))
    if goal:
        qs = qs.filter(goal=goal)
    qs = qs.order_by("full_name")

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page") or 1)

    selected_id = request.GET.get("selected")
    if selected_id:
        try:
            selected = _scoped(request).get(pk=selected_id)
        except Client.DoesNotExist:
            selected = page.object_list[0] if page.object_list else None
    else:
        selected = page.object_list[0] if page.object_list else None

    total_count = _scoped(request).count()

    goals = Client.Goal.choices
    return render(
        request,
        "clients_list.html",
        {
            **app_context(request, active_nav="clients"),
            "page": page,
            "selected": selected,
            "q": q,
            "goal": goal,
            "goals": goals,
            "total_count": total_count,
        },
    )

@login_required
def client_detail(request, pk):
    client = get_object_or_404(_scoped(request), pk=pk)
    active_plan = client.active_plan
    recent_sessions = client.session_logs.order_by("-performed_on")[:5]
    upcoming = client.appointments.filter(
        is_archived=False, start_at__gte=__import__("django").utils.timezone.now()
    ).exclude(status="cancelled").order_by("start_at")[:5]
    body = client.body_metrics.order_by("-recorded_on")[:1].first()

    tab = request.GET.get("tab") or "overview"
    return render(
        request,
        "client_detail.html",
        {
            **app_context(request, active_nav="clients"),
            "client": client,
            "active_plan": active_plan,
            "recent_sessions": recent_sessions,
            "upcoming": upcoming,
            "latest_body": body,
            "tab": tab,
        },
    )

@login_required
def client_create(request):
    form = ClientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        client = form.save(commit=False)
        client.trainer = request.user
        client.save()
        messages.success(request, f"Added {client.full_name}.")
        return redirect("client_detail", pk=client.pk)
    return render(
        request,
        "client_form.html",
        {**app_context(request, active_nav="clients"), "form": form, "client": None},
    )

@login_required
def client_edit(request, pk):
    client = get_object_or_404(_scoped(request), pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Client updated.")
        return redirect("client_detail", pk=client.pk)
    return render(
        request,
        "client_form.html",
        {**app_context(request, active_nav="clients"), "form": form, "client": client},
    )

@login_required
def client_archive(request, pk):

    client = get_object_or_404(_scoped(request), pk=pk)
    if request.method == "POST":
        name = client.full_name
        client.delete()
        messages.info(request, f"Deleted {name}.")
    return HttpResponseRedirect(reverse("clients"))

@login_required
def client_restore(request, pk):

    return HttpResponseRedirect(reverse("clients"))
