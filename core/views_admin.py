

from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery, IntegerField
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import Client, SubscriptionPlan, TrainerSubscription, User

def admin_required(view):

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            return HttpResponseForbidden("Admins only.")
        return view(request, *args, **kwargs)

    return wrapper

class SubscriptionPlanForm(forms.ModelForm):

    class Meta:
        model = SubscriptionPlan
        fields = [
            "name",
            "monthly_price_aud",
            "max_clients",
            "ai_plans_per_month",
            "description",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base = slugify(instance.name)
            slug = base
            n = 2

            while SubscriptionPlan.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance

class TrainerSubscriptionForm(forms.ModelForm):
    class Meta:
        model = TrainerSubscription
        fields = ["plan"]

@admin_required
def admin_dashboard(request):

    total_trainers = User.objects.filter(role=User.Role.TRAINER).count()
    active_subs = TrainerSubscription.objects.filter(is_archived=False).count()
    active_plans = SubscriptionPlan.objects.filter(is_archived=False).count()
    archived_plans = SubscriptionPlan.objects.filter(is_archived=True).count()
    total_clients = Client.objects.count()

    revenue = sum(
        s.plan.monthly_price_aud
        for s in TrainerSubscription.objects.filter(is_archived=False).select_related("plan")
    )

    plans = (
        SubscriptionPlan.objects.annotate(
            subscriber_count=Count(
                "trainersubscription",
                filter=Q(trainersubscription__is_archived=False),
            )
        )
        .order_by("is_archived", "monthly_price_aud", "name")
    )

    recent_trainers = (
        User.objects.filter(role=User.Role.TRAINER)
        .order_by("-date_joined")
        .select_related("subscription__plan")[:6]
    )

    return render(
        request,
        "admin_dashboard.html",
        {
            "total_trainers": total_trainers,
            "active_subs": active_subs,
            "active_plans": active_plans,
            "archived_plans": archived_plans,
            "total_clients": total_clients,
            "revenue": revenue,
            "plans": plans,
            "recent_trainers": recent_trainers,
            "active_nav": "admin_overview",
        },
    )

@admin_required
def admin_plans(request):
    show_archived = request.GET.get("archived") == "1"
    q = (request.GET.get("q") or "").strip()
    qs = SubscriptionPlan.objects.all()
    if not show_archived:
        qs = qs.filter(is_archived=False)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q))
    qs = qs.annotate(
        subscriber_count=Count(
            "trainersubscription",
            filter=Q(trainersubscription__is_archived=False),
        )
    ).order_by("is_archived", "monthly_price_aud", "name")
    page = Paginator(qs, 10).get_page(request.GET.get("page") or 1)
    return render(
        request,
        "admin_plans.html",
        {
            "page": page,
            "q": q,
            "show_archived": show_archived,
            "active_nav": "admin_plans",
        },
    )

@admin_required
def admin_plan_create(request):
    form = SubscriptionPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = form.save()
        messages.success(request, f"Created plan '{plan.name}'.")
        return redirect("admin_plans")
    return render(
        request,
        "admin_plan_form.html",
        {"form": form, "plan": None, "active_nav": "admin_plans"},
    )

@admin_required
def admin_plan_edit(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    form = SubscriptionPlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plan updated.")
        return redirect("admin_plans")
    subscribers = (
        TrainerSubscription.objects.filter(plan=plan, is_archived=False)
        .select_related("trainer")
        .order_by("trainer__email")
    )
    return render(
        request,
        "admin_plan_form.html",
        {
            "form": form,
            "plan": plan,
            "subscribers": subscribers,
            "active_nav": "admin_plans",
        },
    )

@admin_required
def admin_plan_archive(request, pk):

    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    if request.method == "POST":
        plan.is_archived = not plan.is_archived
        plan.save(update_fields=["is_archived"])
        messages.info(
            request,
            f"{'Archived' if plan.is_archived else 'Restored'} plan '{plan.name}'.",
        )
    return redirect("admin_plans")

@admin_required
def admin_trainers(request):
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.filter(role=User.Role.TRAINER).select_related("subscription__plan")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(full_name__icontains=q))

    client_counts = (
        Client.objects.filter(trainer=OuterRef("pk"))
        .order_by()
        .values("trainer")
        .annotate(c=Count("id"))
        .values("c")
    )
    qs = qs.annotate(
        client_count=Coalesce(Subquery(client_counts, output_field=IntegerField()), 0)
    ).order_by("email")
    page = Paginator(qs, 20).get_page(request.GET.get("page") or 1)
    return render(
        request,
        "admin_trainers.html",
        {
            "page": page,
            "q": q,
            "plans": SubscriptionPlan.objects.filter(is_archived=False),
            "active_nav": "admin_trainers",
        },
    )

@admin_required
def admin_trainer_assign(request, pk):
    trainer = get_object_or_404(User, pk=pk, role=User.Role.TRAINER)
    if request.method != "POST":
        return redirect("admin_trainers")
    plan_id = request.POST.get("plan")
    plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_archived=False)
    sub, _ = TrainerSubscription.objects.get_or_create(
        trainer=trainer, defaults={"plan": plan}
    )
    sub.plan = plan
    sub.is_archived = False
    sub.save()
    messages.success(request, f"{trainer.email} is now on the '{plan.name}' plan.")
    return redirect("admin_trainers")

@admin_required
def admin_trainer_cancel(request, pk):

    trainer = get_object_or_404(User, pk=pk, role=User.Role.TRAINER)
    if request.method == "POST":
        sub = getattr(trainer, "subscription", None)
        if sub:
            sub.is_archived = True
            sub.save(update_fields=["is_archived"])
            messages.info(request, f"Archived subscription for {trainer.email}.")
    return redirect("admin_trainers")
