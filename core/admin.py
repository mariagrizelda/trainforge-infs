

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

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
    SubscriptionPlan,
    TrainerSubscription,
    TrainingPlan,
    User,
)

@admin.action(description="Archive selected")
def archive_selected(modeladmin, request, queryset):
    queryset.update(is_archived=True)

@admin.action(description="Restore selected")
def restore_selected(modeladmin, request, queryset):
    queryset.update(is_archived=False)

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "full_name", "role", "is_staff", "date_joined")
    list_filter = ("role", "is_staff", "is_superuser")
    search_fields = ("email", "full_name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "role", "avatar_color", "first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "role", "password1", "password2"),
        }),
    )

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monthly_price_aud",
        "max_clients",
        "ai_plans_per_month",
        "is_archived",
        "created_at",
    )
    list_filter = ("is_archived",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    actions = [archive_selected, restore_selected]
    list_per_page = 25

@admin.register(TrainerSubscription)
class TrainerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("trainer", "plan", "started_at", "is_archived")
    list_filter = ("plan", "is_archived")
    autocomplete_fields = ("trainer", "plan")
    list_per_page = 25
    actions = [archive_selected, restore_selected]

class BodyMetricInline(admin.TabularInline):
    model = BodyMetric
    extra = 0

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "trainer", "goal", "weekly_frequency", "is_archived")
    list_filter = ("goal", "is_archived")
    search_fields = ("full_name", "email", "phone")
    autocomplete_fields = ("trainer",)
    inlines = [BodyMetricInline]
    actions = [archive_selected, restore_selected]
    list_per_page = 25

@admin.register(MuscleGroup)
class MuscleGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("name", "trainer", "equipment", "difficulty", "is_archived")
    list_filter = ("equipment", "difficulty", "is_archived")
    search_fields = ("name", "description")
    autocomplete_fields = ("trainer",)
    filter_horizontal = ("muscle_groups",)
    actions = [archive_selected, restore_selected]
    list_per_page = 25

class PlanExerciseInline(admin.TabularInline):
    model = PlanExercise
    extra = 0
    autocomplete_fields = ("exercise",)

class PlanDayInline(admin.TabularInline):
    model = PlanDay
    extra = 0

@admin.register(TrainingPlan)
class TrainingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "client",
        "trainer",
        "weeks",
        "current_week",
        "generated_by_ai",
        "is_archived",
    )
    list_filter = ("is_archived", "generated_by_ai")
    search_fields = ("name", "client__full_name")
    autocomplete_fields = ("trainer", "client")
    inlines = [PlanDayInline]
    actions = [archive_selected, restore_selected]
    list_per_page = 25

@admin.register(PlanDay)
class PlanDayAdmin(admin.ModelAdmin):
    list_display = ("label", "plan", "order")
    autocomplete_fields = ("plan",)
    search_fields = ("label", "plan__name")
    inlines = [PlanExerciseInline]

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "trainer", "start_at", "duration_minutes", "status", "is_archived")
    list_filter = ("status", "is_archived")
    search_fields = ("client__full_name", "notes", "location")
    autocomplete_fields = ("trainer", "client", "plan_day")
    date_hierarchy = "start_at"
    actions = [archive_selected, restore_selected]
    list_per_page = 25

class SetLogInline(admin.TabularInline):
    model = SetLog
    extra = 0
    autocomplete_fields = ("exercise",)

@admin.register(SessionLog)
class SessionLogAdmin(admin.ModelAdmin):
    list_display = ("client", "performed_on", "trainer", "is_archived")
    list_filter = ("is_archived",)
    autocomplete_fields = ("trainer", "client", "plan_day", "appointment")
    inlines = [SetLogInline]
    date_hierarchy = "performed_on"
    actions = [archive_selected, restore_selected]
    list_per_page = 25

@admin.register(AIPlanGeneration)
class AIPlanGenerationAdmin(admin.ModelAdmin):
    list_display = ("trainer", "client", "outcome", "created_at")
    list_filter = ("outcome",)
    readonly_fields = ("created_at",)
    list_per_page = 25
