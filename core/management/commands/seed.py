

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
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
)

User = get_user_model()

PLAN_DEFS = [
    {"name": "Solo", "slug": "solo", "monthly_price_aud": 0, "max_clients": 5,
     "ai_plans_per_month": 5, "description": "Free tier for new trainers."},
    {"name": "Studio", "slug": "studio", "monthly_price_aud": 29, "max_clients": 50,
     "ai_plans_per_month": 50, "description": "For independent trainers with a full book."},
    {"name": "Team", "slug": "team", "monthly_price_aud": 79, "max_clients": 200,
     "ai_plans_per_month": 200, "description": "For small training studios."},
]

MUSCLE_GROUPS = [
    "Chest", "Back", "Shoulders", "Biceps", "Triceps", "Quads", "Hamstrings",
    "Glutes", "Calves", "Core", "Forearms", "Hip flexors",
]

EXERCISES = [
    ("Back Squat", "barbell", "intermediate", 5, 5, 180, ["Quads", "Glutes", "Hamstrings"]),
    ("Front Squat", "barbell", "advanced", 4, 6, 180, ["Quads", "Core"]),
    ("Romanian Deadlift", "barbell", "intermediate", 3, 8, 120, ["Hamstrings", "Glutes", "Back"]),
    ("Conventional Deadlift", "barbell", "advanced", 3, 5, 180, ["Back", "Hamstrings", "Glutes"]),
    ("Bench Press", "barbell", "intermediate", 5, 5, 180, ["Chest", "Triceps", "Shoulders"]),
    ("Overhead Press", "barbell", "intermediate", 4, 6, 150, ["Shoulders", "Triceps"]),
    ("Barbell Row", "barbell", "intermediate", 4, 8, 120, ["Back", "Biceps"]),
    ("Pull-up", "bodyweight", "intermediate", 4, 8, 120, ["Back", "Biceps"]),
    ("Dumbbell Bench Press", "dumbbell", "intermediate", 3, 10, 90, ["Chest", "Triceps"]),
    ("Dumbbell Row", "dumbbell", "beginner", 3, 12, 75, ["Back", "Biceps"]),
    ("Dumbbell Shoulder Press", "dumbbell", "intermediate", 3, 10, 90, ["Shoulders", "Triceps"]),
    ("Goblet Squat", "kettlebell", "beginner", 3, 12, 75, ["Quads", "Glutes"]),
    ("Walking Lunge", "dumbbell", "beginner", 3, 12, 75, ["Quads", "Glutes"]),
    ("Hip Thrust", "barbell", "intermediate", 3, 10, 90, ["Glutes", "Hamstrings"]),
    ("Lat Pulldown", "cable", "beginner", 3, 12, 75, ["Back", "Biceps"]),
    ("Seated Cable Row", "cable", "beginner", 3, 12, 75, ["Back"]),
    ("Cable Triceps Pushdown", "cable", "beginner", 3, 12, 60, ["Triceps"]),
    ("Cable Biceps Curl", "cable", "beginner", 3, 12, 60, ["Biceps"]),
    ("Leg Press", "machine", "beginner", 4, 12, 90, ["Quads", "Glutes"]),
    ("Plank", "bodyweight", "beginner", 3, 12, 60, ["Core"]),
    ("Push-up", "bodyweight", "beginner", 3, 12, 60, ["Chest", "Triceps", "Core"]),
    ("Romanian Single-Leg Deadlift", "dumbbell", "intermediate", 3, 10, 75, ["Hamstrings", "Glutes"]),
]

CLIENT_DEFS = [
    ("Sarah Kawamoto", "sarah@example.com", "hypertrophy", 4, "barbell, dumbbells, cable, bench", "#E84797"),
    ("Marcus Tanaka", "marcus@example.com", "strength", 3, "barbell, rack, bench", "#94C2DA"),
    ("Priya Ramachandran", "priya@example.com", "fat_loss", 3, "dumbbells, kettlebell, bands", "#203F9A"),
    ("Yuki Ito", "yuki@example.com", "hypertrophy", 4, "barbell, dumbbells, cable", "#D97757"),
    ("Jordan Lee", "jordan@example.com", "fat_loss", 3, "dumbbells, bodyweight", "#7BA89A"),
    ("Dani Kim", "dani@example.com", "strength", 4, "barbell, rack, dumbbells", "#A8759A"),
    ("Rachel Hayes", "rachel@example.com", "general", 2, "dumbbells, bands", "#203F9A"),
]

class Command(BaseCommand):
    help = "Seed the database with a demo trainer and realistic data."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first.")
        parser.add_argument("--trainer-email", default="maria@trainforge.test")
        parser.add_argument("--trainer-password", default="trainforge1234")
        parser.add_argument("--admin-email", default="admin@trainforge.test")
        parser.add_argument("--admin-password", default="adminadmin")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            self.stdout.write(self.style.WARNING("Resetting demo data..."))
            User.objects.filter(email=opts["trainer_email"]).delete()
            SubscriptionPlan.objects.all().delete()
            MuscleGroup.objects.all().delete()

        plans_by_slug = {}
        for p in PLAN_DEFS:
            plan, _ = SubscriptionPlan.objects.update_or_create(slug=p["slug"], defaults=p)
            plans_by_slug[p["slug"]] = plan

        mg_by_name = {}
        for name in MUSCLE_GROUPS:
            mg, _ = MuscleGroup.objects.get_or_create(
                slug=name.lower().replace(" ", "-"), defaults={"name": name}
            )
            mg.name = name
            mg.save()
            mg_by_name[name] = mg

        if not User.objects.filter(email=opts["admin_email"]).exists():
            User.objects.create_superuser(
                email=opts["admin_email"],
                password=opts["admin_password"],
                full_name="TrainForge Admin",
                role=User.Role.ADMIN,
            )

        trainer, created = User.objects.get_or_create(
            email=opts["trainer_email"],
            defaults={
                "full_name": "Maria Grizelda",
                "role": User.Role.TRAINER,
                "username": opts["trainer_email"],
            },
        )
        if created:
            trainer.set_password(opts["trainer_password"])
            trainer.save()

        TrainerSubscription.objects.get_or_create(
            trainer=trainer, defaults={"plan": plans_by_slug["solo"]}
        )

        Exercise.objects.filter(trainer=trainer).delete()
        ex_by_name = {}
        for (name, equip, diff, sets, reps, rest, mgs) in EXERCISES:
            e = Exercise.objects.create(
                trainer=trainer,
                name=name,
                description=f"{name}: focus on controlled tempo and full range of motion.",
                equipment=equip,
                difficulty=diff,
                default_sets=sets,
                default_reps=reps,
                default_rest_seconds=rest,
            )
            e.muscle_groups.set([mg_by_name[m] for m in mgs])
            ex_by_name[name] = e

        Client.objects.filter(trainer=trainer).delete()
        clients = []
        today = date.today()
        for i, (name, email, goal, freq, equip, color) in enumerate(CLIENT_DEFS):
            c = Client.objects.create(
                trainer=trainer,
                full_name=name,
                email=email,
                goal=goal,
                weekly_frequency=freq,
                available_equipment=equip,
                avatar_color=color,
                added_on=today - timedelta(days=20 + i * 5),
                preferred_times="Weekday evenings",
            )

            for k in range(2):
                BodyMetric.objects.create(
                    client=c,
                    recorded_on=today - timedelta(days=30 - k * 14),
                    weight_kg=Decimal(str(60 + i * 2 + k)),
                    body_fat_pct=Decimal("22.0") - Decimal(k),
                )
            clients.append(c)

        for ci, client in enumerate(clients[:5]):
            tp = TrainingPlan.objects.create(
                trainer=trainer,
                client=client,
                name={
                    "hypertrophy": "4-Week Hypertrophy Block",
                    "strength": "5x5 Strength Build",
                    "fat_loss": "Fat Loss & Conditioning",
                    "general": "Total Body Foundations",
                    "rehab": "Return to Lift",
                }.get(client.goal, "Starter Plan"),
                description="Two- or three-day split tailored to the client's goal.",
                weeks=4,
                current_week=(ci % 4) + 1,
                is_active=True,
            )

            if client.goal == "strength":
                days = [
                    ("Day A — Squat & Press", ["Back Squat", "Bench Press", "Barbell Row", "Plank"]),
                    ("Day B — Deadlift & Pull", ["Conventional Deadlift", "Overhead Press", "Pull-up", "Plank"]),
                ]
            elif client.goal == "hypertrophy":
                days = [
                    ("Day A — Push", ["Bench Press", "Overhead Press", "Cable Triceps Pushdown", "Push-up"]),
                    ("Day B — Pull", ["Pull-up", "Dumbbell Row", "Cable Biceps Curl", "Plank"]),
                    ("Day C — Legs", ["Back Squat", "Romanian Deadlift", "Hip Thrust", "Walking Lunge"]),
                ]
            elif client.goal == "fat_loss":
                days = [
                    ("Day A — Full body", ["Goblet Squat", "Dumbbell Bench Press", "Dumbbell Row", "Plank"]),
                    ("Day B — Lower & core", ["Romanian Single-Leg Deadlift", "Walking Lunge", "Hip Thrust", "Plank"]),
                ]
            else:
                days = [
                    ("Day A — Basics", ["Goblet Squat", "Push-up", "Dumbbell Row", "Plank"]),
                ]

            for di, (label, names) in enumerate(days):
                pd = PlanDay.objects.create(plan=tp, label=label, order=di)
                for xi, n in enumerate(names):
                    ex = ex_by_name.get(n)
                    if not ex:
                        continue
                    PlanExercise.objects.create(
                        day=pd,
                        exercise=ex,
                        order=xi,
                        sets=ex.default_sets,
                        reps=f"{ex.default_reps}",
                        rest_seconds=ex.default_rest_seconds,
                    )

        Appointment.objects.filter(trainer=trainer).delete()
        now = timezone.localtime(timezone.now())
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        slot_options = [(0, 9), (0, 14), (1, 11), (2, 9), (2, 16), (3, 8), (4, 17), (5, 10)]
        for i, client in enumerate(clients):
            day_off, hour = slot_options[i % len(slot_options)]
            start = week_start + timedelta(days=day_off, hours=hour)
            plan = client.active_plan
            plan_day = plan.days.first() if plan else None
            Appointment.objects.create(
                trainer=trainer,
                client=client,
                plan_day=plan_day,
                start_at=start,
                duration_minutes=60 if i % 2 == 0 else 45,
                location="The Iron Practice",
            )

        SessionLog.objects.filter(trainer=trainer).delete()
        for ci, client in enumerate(clients[:3]):
            plan = client.active_plan
            day = plan.days.first() if plan else None
            for delta_days in (5, 12, 19, 26):
                session = SessionLog.objects.create(
                    trainer=trainer,
                    client=client,
                    plan_day=day,
                    performed_on=today - timedelta(days=delta_days),
                    notes="Good session.",
                )
                if not day:
                    continue
                for pe in day.exercises.all()[:3]:
                    base = 40 + ci * 8
                    for s_no in (1, 2, 3):
                        weight = Decimal(base + (26 - delta_days) // 2 + s_no)
                        SetLog.objects.create(
                            session=session,
                            exercise=pe.exercise,
                            set_number=s_no,
                            reps=pe.exercise.default_reps,
                            weight_kg=weight,
                            rpe=Decimal("7.5"),
                            is_personal_record=(delta_days == 5 and s_no == 3),
                        )

        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
        self.stdout.write(f"  Admin:   {opts['admin_email']} / {opts['admin_password']}")
        self.stdout.write(f"  Trainer: {opts['trainer_email']} / {opts['trainer_password']}")
