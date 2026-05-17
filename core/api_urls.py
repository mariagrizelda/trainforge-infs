
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from . import api

router = DefaultRouter()
router.register("clients", api.ClientViewSet, basename="client")
router.register("exercises", api.ExerciseViewSet, basename="exercise")
router.register("muscle-groups", api.MuscleGroupViewSet, basename="musclegroup")
router.register("plans", api.TrainingPlanViewSet, basename="plan")
router.register("plan-days", api.PlanDayViewSet, basename="planday")
router.register("plan-exercises", api.PlanExerciseViewSet, basename="planexercise")
router.register("appointments", api.AppointmentViewSet, basename="appointment")
router.register("sessions", api.SessionLogViewSet, basename="session")
router.register("set-logs", api.SetLogViewSet, basename="setlog")
router.register("body-metrics", api.BodyMetricViewSet, basename="bodymetric")

urlpatterns = [
    path("", include(router.urls)),
    path("token/", obtain_auth_token, name="api_token"),
    path("me/", api.me_view, name="api_me"),
]
