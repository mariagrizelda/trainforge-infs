
from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),

    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),

    path("clients/", views.clients_list, name="clients"),
    path("clients/new/", views.client_create, name="client_create"),
    path("clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("clients/<int:pk>/edit/", views.client_edit, name="client_edit"),
    path("clients/<int:pk>/archive/", views.client_archive, name="client_archive"),
    path("clients/<int:pk>/restore/", views.client_restore, name="client_restore"),

    path("exercises/", views.exercises_list, name="exercises"),
    path("exercises/new/", views.exercise_create, name="exercise_create"),
    path("exercises/<int:pk>/edit/", views.exercise_edit, name="exercise_edit"),
    path("exercises/<int:pk>/archive/", views.exercise_archive, name="exercise_archive"),

    path("clients/<int:client_id>/plans/new/", views.plan_create, name="plan_create"),
    path("plans/<int:pk>/", views.plan_detail, name="plan_detail"),
    path("plans/<int:pk>/edit/", views.plan_edit, name="plan_edit"),
    path("plans/<int:pk>/archive/", views.plan_archive, name="plan_archive"),
    path("plans/<int:pk>/days/new/", views.plan_day_create, name="plan_day_create"),
    path("plans/days/<int:day_id>/exercises/new/", views.plan_exercise_create, name="plan_exercise_create"),
    path("plans/days/<int:day_id>/delete/", views.plan_day_delete, name="plan_day_delete"),
    path("plans/exercises/<int:pe_id>/delete/", views.plan_exercise_delete, name="plan_exercise_delete"),

    path("calendar/", views.calendar_view, name="calendar"),
    path("calendar/appointments/new/", views.appointment_create, name="appointment_create"),
    path("calendar/appointments/<int:pk>/edit/", views.appointment_edit, name="appointment_edit"),
    path("calendar/appointments/<int:pk>/delete/", views.appointment_delete, name="appointment_delete"),

    path("progress/", views.progress_index, name="progress_index"),
    path("progress/<int:client_id>/", views.progress_view, name="progress"),
    path("progress/<int:client_id>/log/", views.session_log_create, name="session_log_create"),

    path("ai/plan/", views.ai_plan_page, name="ai_plan_page"),
    path("ai/plan/generate/", views.ai_plan_generate, name="ai_plan_generate"),
    path("ai/plan/save/", views.ai_plan_save, name="ai_plan_save"),

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/plans/", views.admin_plans, name="admin_plans"),
    path("admin-dashboard/plans/new/", views.admin_plan_create, name="admin_plan_create"),
    path("admin-dashboard/plans/<int:pk>/edit/", views.admin_plan_edit, name="admin_plan_edit"),
    path("admin-dashboard/plans/<int:pk>/archive/", views.admin_plan_archive, name="admin_plan_archive"),
    path("admin-dashboard/trainers/", views.admin_trainers, name="admin_trainers"),
    path("admin-dashboard/trainers/<int:pk>/assign/", views.admin_trainer_assign, name="admin_trainer_assign"),
    path("admin-dashboard/trainers/<int:pk>/cancel/", views.admin_trainer_cancel, name="admin_trainer_cancel"),
]
