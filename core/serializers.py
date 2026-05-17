
from rest_framework import serializers

from .models import (
    AIPlanGeneration,
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
    User,
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "avatar_color"]
        read_only_fields = ["role"]

class MuscleGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuscleGroup
        fields = ["id", "name", "slug"]

class ClientSerializer(serializers.ModelSerializer):
    initials = serializers.CharField(read_only=True)
    active_plan_name = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "goal",
            "weekly_frequency",
            "available_equipment",
            "injuries",
            "preferred_times",
            "notes",
            "avatar_color",
            "added_on",
            "is_archived",
            "initials",
            "active_plan_name",
        ]
        read_only_fields = ["initials", "active_plan_name"]

    def get_active_plan_name(self, obj):
        plan = obj.active_plan
        return plan.name if plan else None

class ExerciseSerializer(serializers.ModelSerializer):
    muscle_groups = serializers.PrimaryKeyRelatedField(
        queryset=MuscleGroup.objects.all(), many=True, required=False
    )
    muscle_group_names = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = [
            "id",
            "name",
            "description",
            "muscle_groups",
            "muscle_group_names",
            "equipment",
            "difficulty",
            "default_sets",
            "default_reps",
            "default_rest_seconds",
            "is_archived",
        ]

    def get_muscle_group_names(self, obj):
        return [mg.name for mg in obj.muscle_groups.all()]

class PlanExerciseSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source="exercise.name", read_only=True)

    class Meta:
        model = PlanExercise
        fields = [
            "id",
            "day",
            "exercise",
            "exercise_name",
            "order",
            "sets",
            "reps",
            "rest_seconds",
            "coaching_notes",
        ]

class PlanDaySerializer(serializers.ModelSerializer):
    exercises = PlanExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = PlanDay
        fields = ["id", "plan", "label", "order", "exercises"]

class TrainingPlanSerializer(serializers.ModelSerializer):
    days = PlanDaySerializer(many=True, read_only=True)
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    progress_pct = serializers.IntegerField(read_only=True)

    class Meta:
        model = TrainingPlan
        fields = [
            "id",
            "client",
            "client_name",
            "name",
            "description",
            "weeks",
            "current_week",
            "is_active",
            "generated_by_ai",
            "is_archived",
            "progress_pct",
            "days",
        ]

class AppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    client_color = serializers.CharField(source="client.avatar_color", read_only=True)
    end_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "client",
            "client_name",
            "client_color",
            "plan_day",
            "start_at",
            "duration_minutes",
            "status",
            "location",
            "notes",
            "recurrence_parent",
            "end_at",
            "is_archived",
        ]

class SetLogSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source="exercise.name", read_only=True)

    class Meta:
        model = SetLog
        fields = [
            "id",
            "session",
            "exercise",
            "exercise_name",
            "set_number",
            "reps",
            "weight_kg",
            "rpe",
            "is_personal_record",
        ]

class SessionLogSerializer(serializers.ModelSerializer):
    sets = SetLogSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source="client.full_name", read_only=True)

    class Meta:
        model = SessionLog
        fields = [
            "id",
            "client",
            "client_name",
            "appointment",
            "plan_day",
            "performed_on",
            "notes",
            "sets",
        ]

class BodyMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyMetric
        fields = ["id", "client", "recorded_on", "weight_kg", "body_fat_pct", "notes"]

class AIPlanGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIPlanGeneration
        fields = "__all__"
        read_only_fields = ["trainer", "created_at"]
