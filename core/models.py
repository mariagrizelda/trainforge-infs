

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

class UserManager(BaseUserManager):

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email required")
        email = self.normalize_email(email)

        extra.setdefault("username", email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", "admin")
        return self._create_user(email, password, **extra)

class User(AbstractUser):

    class Role(models.TextChoices):
        TRAINER = "trainer", "Personal trainer"
        ADMIN = "admin", "SaaS admin"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.TRAINER)
    full_name = models.CharField(max_length=120, blank=True)
    avatar_color = models.CharField(
        max_length=7,
        default="#203F9A",
        help_text="Hex color for the user avatar circle.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email

    @property
    def initials(self) -> str:
        name = (self.full_name or self.email).strip()
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return name[:2].upper()

class SubscriptionPlan(models.Model):

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    monthly_price_aud = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_clients = models.PositiveIntegerField(default=5)
    ai_plans_per_month = models.PositiveIntegerField(default=10)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["monthly_price_aud", "name"]

    def __str__(self) -> str:
        return self.name

class TrainerSubscription(models.Model):

    trainer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
        limit_choices_to={"role": "trainer"},
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    started_at = models.DateTimeField(default=timezone.now)
    is_archived = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.trainer.email} on {self.plan.name}"

class TenantOwnedModel(models.Model):

    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        limit_choices_to={"role": "trainer"},
    )
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Client(TenantOwnedModel):
    class Goal(models.TextChoices):
        HYPERTROPHY = "hypertrophy", "Hypertrophy"
        STRENGTH = "strength", "Strength"
        FAT_LOSS = "fat_loss", "Fat loss"
        GENERAL = "general", "General fitness"
        REHAB = "rehab", "Rehab"

    full_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    goal = models.CharField(max_length=20, choices=Goal.choices, default=Goal.GENERAL)
    weekly_frequency = models.PositiveSmallIntegerField(default=3)
    available_equipment = models.CharField(
        max_length=200,
        blank=True,
        help_text="Free text list. e.g. 'barbell, dumbbells, cable, bench'.",
    )
    injuries = models.TextField(blank=True)
    preferred_times = models.CharField(
        max_length=200,
        blank=True,
        help_text="Free text. e.g. 'weekday mornings, Saturday'.",
    )
    notes = models.TextField(blank=True)
    avatar_color = models.CharField(max_length=7, default="#94C2DA")
    added_on = models.DateField(default=timezone.now)

    class Meta:
        ordering = ["full_name"]
        indexes = [models.Index(fields=["trainer", "is_archived"])]

    def __str__(self) -> str:
        return self.full_name

    @property
    def initials(self) -> str:
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.full_name[:2].upper()

    @property
    def active_plan(self):
        return (
            self.training_plans.filter(is_archived=False, is_active=True)
            .order_by("-created_at")
            .first()
        )

class BodyMetric(models.Model):

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="body_metrics")
    recorded_on = models.DateField(default=timezone.now)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    body_fat_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-recorded_on"]

    def __str__(self) -> str:
        return f"{self.client.full_name} @ {self.recorded_on}"

class MuscleGroup(models.Model):

    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

class Exercise(TenantOwnedModel):
    class Equipment(models.TextChoices):
        BODYWEIGHT = "bodyweight", "Bodyweight"
        BARBELL = "barbell", "Barbell"
        DUMBBELL = "dumbbell", "Dumbbell"
        MACHINE = "machine", "Machine"
        CABLE = "cable", "Cable"
        BAND = "band", "Resistance band"
        KETTLEBELL = "kettlebell", "Kettlebell"
        OTHER = "other", "Other"

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    muscle_groups = models.ManyToManyField(MuscleGroup, related_name="exercises", blank=True)
    equipment = models.CharField(
        max_length=20, choices=Equipment.choices, default=Equipment.BODYWEIGHT
    )
    difficulty = models.CharField(
        max_length=20, choices=Difficulty.choices, default=Difficulty.INTERMEDIATE
    )
    default_sets = models.PositiveSmallIntegerField(default=3)
    default_reps = models.PositiveSmallIntegerField(default=10)
    default_rest_seconds = models.PositiveSmallIntegerField(default=90)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["trainer", "is_archived"])]
        constraints = [
            models.UniqueConstraint(
                fields=["trainer", "name"], name="exercise_unique_per_trainer"
            )
        ]

    def __str__(self) -> str:
        return self.name

class TrainingPlan(TenantOwnedModel):

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="training_plans")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    weeks = models.PositiveSmallIntegerField(default=4)
    current_week = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    generated_by_ai = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} — {self.client.full_name}"

    @property
    def progress_pct(self) -> int:
        if not self.weeks:
            return 0
        return min(100, int(round(self.current_week / self.weeks * 100)))

class PlanDay(models.Model):

    plan = models.ForeignKey(TrainingPlan, on_delete=models.CASCADE, related_name="days")
    label = models.CharField(max_length=40, help_text="e.g. 'Day A — Push'")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["plan", "order"]

    def __str__(self) -> str:
        return self.label

class PlanExercise(models.Model):

    day = models.ForeignKey(PlanDay, on_delete=models.CASCADE, related_name="exercises")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField(default=0)
    sets = models.PositiveSmallIntegerField(default=3)
    reps = models.CharField(
        max_length=20, default="10", help_text="Free text, e.g. '8-12' or 'AMRAP'."
    )
    rest_seconds = models.PositiveSmallIntegerField(default=90)
    coaching_notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["day", "order"]

    def __str__(self) -> str:
        return f"{self.exercise.name} ({self.sets} × {self.reps})"

class Appointment(TenantOwnedModel):

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="appointments")
    plan_day = models.ForeignKey(
        PlanDay, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointments"
    )
    start_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    location = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=200, blank=True)

    recurrence_parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurrences",
    )

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["trainer", "start_at"]),
            models.Index(fields=["trainer", "is_archived", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.client.full_name} @ {self.start_at:%Y-%m-%d %H:%M}"

    @property
    def end_at(self):
        return self.start_at + timedelta(minutes=self.duration_minutes)

    def overlapping_qs(self):

        end = self.end_at
        qs = (
            Appointment.objects.filter(
                trainer=self.trainer,
                is_archived=False,
                start_at__lt=end,
            )
            .exclude(status=self.Status.CANCELLED)
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        return [a for a in qs if a.end_at > self.start_at]

class SessionLog(TenantOwnedModel):

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="session_logs")
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_log",
    )
    plan_day = models.ForeignKey(
        PlanDay, on_delete=models.SET_NULL, null=True, blank=True, related_name="session_logs"
    )
    performed_on = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-performed_on"]

    def __str__(self) -> str:
        return f"{self.client.full_name} on {self.performed_on}"

class SetLog(models.Model):

    session = models.ForeignKey(SessionLog, on_delete=models.CASCADE, related_name="sets")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT)
    set_number = models.PositiveSmallIntegerField()
    reps = models.PositiveSmallIntegerField()
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    rpe = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Rate of Perceived Exertion (1-10).",
    )
    is_personal_record = models.BooleanField(default=False)

    class Meta:
        ordering = ["session", "exercise", "set_number"]

    def __str__(self) -> str:
        return f"{self.exercise.name} set {self.set_number}: {self.reps} × {self.weight_kg}kg"

class AIPlanGeneration(models.Model):

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        RETRY = "retry", "Retried"
        FAILED = "failed", "Failed"

    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True)
    resulting_plan = models.ForeignKey(
        TrainingPlan, on_delete=models.SET_NULL, null=True, blank=True
    )
    prompt_inputs = models.JSONField(default=dict)
    raw_response = models.JSONField(null=True, blank=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices)
    error_message = models.TextField(blank=True)
    trainer_feedback = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"AI plan for {self.client} ({self.outcome})"
