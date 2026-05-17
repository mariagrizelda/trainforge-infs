

from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Appointment,
    BodyMetric,
    Client,
    Exercise,
    MuscleGroup,
    PlanDay,
    PlanExercise,
    SessionLog,
    SetLog,
    TrainingPlan,
)
from .permissions import IsTrainerOwned
from .serializers import (
    AppointmentSerializer,
    BodyMetricSerializer,
    ClientSerializer,
    ExerciseSerializer,
    MuscleGroupSerializer,
    PlanDaySerializer,
    PlanExerciseSerializer,
    SessionLogSerializer,
    SetLogSerializer,
    TrainingPlanSerializer,
)

class _TenantOwnedViewSet(viewsets.ModelViewSet):

    permission_classes = [IsTrainerOwned]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def perform_create(self, serializer):
        serializer.save(trainer=self.request.user)

class ClientViewSet(_TenantOwnedViewSet):
    serializer_class = ClientSerializer
    search_fields = ["full_name", "email", "phone"]
    ordering_fields = ["full_name", "added_on", "created_at"]

    def get_queryset(self):
        qs = Client.objects.filter(trainer=self.request.user)
        if self.request.query_params.get("include_archived") != "1":
            qs = qs.filter(is_archived=False)
        goal = self.request.query_params.get("goal")
        if goal:
            qs = qs.filter(goal=goal)
        return qs.order_by("full_name")

class ExerciseViewSet(_TenantOwnedViewSet):
    serializer_class = ExerciseSerializer
    search_fields = ["name", "description"]
    ordering_fields = ["name", "difficulty"]

    def get_queryset(self):
        qs = Exercise.objects.filter(trainer=self.request.user)
        if self.request.query_params.get("include_archived") != "1":
            qs = qs.filter(is_archived=False)
        return qs.prefetch_related("muscle_groups").order_by("name")

class MuscleGroupViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = MuscleGroupSerializer
    queryset = MuscleGroup.objects.all().order_by("name")
    permission_classes = [IsAuthenticated]

class TrainingPlanViewSet(_TenantOwnedViewSet):
    serializer_class = TrainingPlanSerializer
    search_fields = ["name", "client__full_name"]

    def get_queryset(self):
        qs = TrainingPlan.objects.filter(trainer=self.request.user)
        if self.request.query_params.get("include_archived") != "1":
            qs = qs.filter(is_archived=False)
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs.select_related("client").prefetch_related(
            "days__exercises__exercise"
        )

class PlanDayViewSet(viewsets.ModelViewSet):
    serializer_class = PlanDaySerializer
    permission_classes = [IsTrainerOwned]

    def get_queryset(self):
        return PlanDay.objects.filter(plan__trainer=self.request.user)

class PlanExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = PlanExerciseSerializer
    permission_classes = [IsTrainerOwned]

    def get_queryset(self):
        return PlanExercise.objects.filter(day__plan__trainer=self.request.user)

class AppointmentViewSet(_TenantOwnedViewSet):
    serializer_class = AppointmentSerializer
    search_fields = ["client__full_name", "notes", "location"]
    ordering_fields = ["start_at"]

    def get_queryset(self):
        qs = Appointment.objects.filter(trainer=self.request.user)
        if self.request.query_params.get("include_archived") != "1":
            qs = qs.filter(is_archived=False)
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(start_at__gte=start)
        if end:
            qs = qs.filter(start_at__lt=end)
        return qs.select_related("client").order_by("start_at")

class SessionLogViewSet(_TenantOwnedViewSet):
    serializer_class = SessionLogSerializer

    def get_queryset(self):
        qs = SessionLog.objects.filter(trainer=self.request.user)
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs.prefetch_related("sets__exercise").order_by("-performed_on")

class SetLogViewSet(viewsets.ModelViewSet):
    serializer_class = SetLogSerializer
    permission_classes = [IsTrainerOwned]

    def get_queryset(self):
        return SetLog.objects.filter(session__trainer=self.request.user)

class BodyMetricViewSet(viewsets.ModelViewSet):
    serializer_class = BodyMetricSerializer
    permission_classes = [IsTrainerOwned]

    def get_queryset(self):
        return BodyMetric.objects.filter(client__trainer=self.request.user).order_by(
            "-recorded_on"
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    u = request.user
    return Response(
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "avatar_color": u.avatar_color,
            "initials": u.initials,
        }
    )
