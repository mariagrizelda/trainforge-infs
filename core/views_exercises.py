
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ExerciseForm
from .models import Exercise, MuscleGroup
from .views_common import app_context

def _scoped(request):
    return Exercise.objects.filter(trainer=request.user)

@login_required
def exercises_list(request):
    q = (request.GET.get("q") or "").strip()
    equipment = request.GET.get("equipment") or ""
    mg = request.GET.get("muscle") or ""

    qs = _scoped(request)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if equipment:
        qs = qs.filter(equipment=equipment)
    if mg:
        qs = qs.filter(muscle_groups__slug=mg)

    qs = qs.prefetch_related("muscle_groups").distinct().order_by("name")
    page = Paginator(qs, 24).get_page(request.GET.get("page") or 1)

    return render(
        request,
        "exercises_list.html",
        {
            **app_context(request, active_nav="exercises"),
            "page": page,
            "q": q,
            "equipment": equipment,
            "muscle": mg,
            "muscle_groups": MuscleGroup.objects.all(),
            "equipments": Exercise.Equipment.choices,
        },
    )

@login_required
def exercise_create(request):
    form = ExerciseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ex = form.save(commit=False)
        ex.trainer = request.user
        ex.save()
        form.save_m2m()
        messages.success(request, f"Added '{ex.name}' to your library.")
        return redirect("exercises")
    return render(
        request,
        "exercise_form.html",
        {**app_context(request, active_nav="exercises"), "form": form, "exercise": None},
    )

@login_required
def exercise_edit(request, pk):
    ex = get_object_or_404(_scoped(request), pk=pk)
    form = ExerciseForm(request.POST or None, instance=ex)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Exercise updated.")
        return redirect("exercises")
    return render(
        request,
        "exercise_form.html",
        {**app_context(request, active_nav="exercises"), "form": form, "exercise": ex},
    )

@login_required
def exercise_archive(request, pk):

    from django.db.models import ProtectedError

    ex = get_object_or_404(_scoped(request), pk=pk)
    if request.method == "POST":
        name = ex.name
        try:
            ex.delete()
            messages.info(request, f"Deleted '{name}'.")
        except ProtectedError:
            messages.error(
                request,
                f"Can't delete '{name}' — it's still referenced by one or more "
                "training plans or session logs. Remove those references first.",
            )
    return redirect("exercises")
