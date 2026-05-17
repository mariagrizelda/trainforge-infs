
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PlanDayForm, PlanExerciseForm, TrainingPlanForm
from .models import Client, Exercise, PlanDay, PlanExercise, TrainingPlan
from .views_common import app_context

@login_required
def plan_create(request, client_id):
    client = get_object_or_404(Client, pk=client_id, trainer=request.user)
    form = TrainingPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.client = client
        plan.trainer = request.user
        plan.save()

        PlanDay.objects.create(plan=plan, label="Day A", order=0)
        messages.success(request, f"Created plan '{plan.name}'.")
        return redirect("plan_detail", pk=plan.pk)
    return render(
        request,
        "plan_form.html",
        {
            **app_context(request, active_nav="clients"),
            "form": form,
            "client": client,
            "plan": None,
        },
    )

@login_required
def plan_detail(request, pk):
    plan = get_object_or_404(
        TrainingPlan.objects.select_related("client").prefetch_related(
            "days__exercises__exercise"
        ),
        pk=pk,
        trainer=request.user,
    )
    exercises = (
        Exercise.objects.filter(trainer=request.user, is_archived=False).order_by("name")
    )
    return render(
        request,
        "plan_detail.html",
        {
            **app_context(request, active_nav="clients"),
            "plan": plan,
            "exercises": exercises,
        },
    )

@login_required
def plan_edit(request, pk):
    plan = get_object_or_404(TrainingPlan, pk=pk, trainer=request.user)
    form = TrainingPlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Plan updated.")
        return redirect("plan_detail", pk=plan.pk)
    return render(
        request,
        "plan_form.html",
        {
            **app_context(request, active_nav="clients"),
            "form": form,
            "client": plan.client,
            "plan": plan,
        },
    )

@login_required
def plan_archive(request, pk):

    plan = get_object_or_404(TrainingPlan, pk=pk, trainer=request.user)
    client_pk = plan.client_id
    if request.method == "POST":
        plan.delete()
        messages.info(request, "Plan deleted.")
    return redirect("client_detail", pk=client_pk)

@login_required
def plan_day_create(request, pk):
    plan = get_object_or_404(TrainingPlan, pk=pk, trainer=request.user)
    if request.method == "POST":
        label = request.POST.get("label", "").strip() or f"Day {chr(65 + plan.days.count())}"
        order = plan.days.count()
        PlanDay.objects.create(plan=plan, label=label, order=order)
        messages.success(request, "Added a day.")
    return redirect("plan_detail", pk=plan.pk)

@login_required
def plan_day_delete(request, day_id):
    day = get_object_or_404(PlanDay, pk=day_id, plan__trainer=request.user)
    plan_pk = day.plan_id
    if request.method == "POST":
        day.delete()
        messages.info(request, "Day removed.")
    return redirect("plan_detail", pk=plan_pk)

@login_required
def plan_exercise_create(request, day_id):
    day = get_object_or_404(PlanDay, pk=day_id, plan__trainer=request.user)
    if request.method == "POST":
        form = PlanExerciseForm(request.POST)

        form.fields["exercise"].queryset = Exercise.objects.filter(trainer=request.user)
        if form.is_valid():
            pe = form.save(commit=False)
            pe.day = day
            pe.order = day.exercises.count()
            pe.save()
            messages.success(request, f"Added {pe.exercise.name}.")
        else:
            errors = "; ".join(
                f"{f}: {', '.join(map(str, errs))}" for f, errs in form.errors.items()
            )
            messages.error(request, f"Couldn't add — {errors}")
    return redirect("plan_detail", pk=day.plan_id)

@login_required
def plan_exercise_delete(request, pe_id):
    pe = get_object_or_404(PlanExercise, pk=pe_id, day__plan__trainer=request.user)
    plan_pk = pe.day.plan_id
    if request.method == "POST":
        pe.delete()
    return redirect("plan_detail", pk=plan_pk)
