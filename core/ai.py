

from __future__ import annotations

import logging
from typing import List, Optional

from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, Field, ValidationError

from .models import AIPlanGeneration, Client, Exercise, PlanDay, PlanExercise, TrainingPlan

log = logging.getLogger(__name__)

class PlanExerciseSpec(BaseModel):
    exercise_id: int = Field(description="One of the IDs in the provided exercise library.")
    sets: int = Field(ge=1, le=10)
    reps: str = Field(description="Reps as a string, e.g. '8-12' or '10'.")
    rest_seconds: int = Field(ge=0, le=600)
    coaching_notes: str = Field(default="", max_length=200)

class PlanDaySpec(BaseModel):
    label: str = Field(description="Day label e.g. 'Day A — Push'.")
    exercises: List[PlanExerciseSpec] = Field(min_length=1)

class PlanResponse(BaseModel):

    name: str = Field(description="Plan name.")
    weeks: int = Field(ge=1, le=16, default=4)
    rationale: str = Field(
        description="Short paragraph explaining how the plan fits the client.",
        max_length=600,
    )
    days: List[PlanDaySpec] = Field(min_length=1, max_length=6)

class AIGenerationError(Exception):
    pass

def _client_payload(client: Client) -> dict:
    return {
        "name": client.full_name,
        "goal": client.get_goal_display(),
        "weekly_frequency": client.weekly_frequency,
        "available_equipment": client.available_equipment,
        "injuries": client.injuries,
    }

def _exercise_library_payload(trainer) -> list[dict]:
    return [
        {
            "id": e.id,
            "name": e.name,
            "equipment": e.get_equipment_display(),
            "difficulty": e.get_difficulty_display(),
            "muscle_groups": [m.name for m in e.muscle_groups.all()],
            "default_reps": e.default_reps,
        }
        for e in Exercise.objects.filter(trainer=trainer, is_archived=False).prefetch_related(
            "muscle_groups"
        )
    ]

def _validate_against_library(plan: PlanResponse, allowed_ids: set[int]) -> None:
    for day in plan.days:
        for ex in day.exercises:
            if ex.exercise_id not in allowed_ids:
                raise AIGenerationError(
                    f"Exercise id {ex.exercise_id} is not in the trainer's library."
                )

def _build_prompt():
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import PromptTemplate

    parser = JsonOutputParser(pydantic_object=PlanResponse)
    prompt = PromptTemplate(
        template=(
            "You are a senior strength and conditioning coach.\n"
            "Design a personalised training plan for a client.\n\n"
            "Client profile:\n{client_json}\n\n"
            "Available exercises in the trainer's library "
            "(use exercise_id from this list and nothing else):\n{library_json}\n\n"
            "Constraints:\n"
            "- Build a {weeks}-week plan with {weekly_frequency} workout days per week.\n"
            "- Each day must include 4 to 7 exercises drawn from the library.\n"
            "- Choose exercises that match the equipment listed; avoid anything that "
            "  would aggravate the listed injuries.\n"
            "- Keep volume appropriate for the goal.\n"
            "- Include a short rationale (1 to 3 sentences) explaining the choices.\n\n"
            "{format_instructions}"
        ),
        input_variables=["client_json", "library_json", "weeks", "weekly_frequency"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    return prompt, parser

def generate_plan(client: Client, weeks: int = 4):

    trainer = client.trainer
    library = _exercise_library_payload(trainer)
    allowed_ids = {e["id"] for e in library}

    audit_inputs = {
        "client": _client_payload(client),
        "library_count": len(library),
        "weeks": weeks,
        "weekly_frequency": client.weekly_frequency,
    }

    if not library:
        gen = AIPlanGeneration.objects.create(
            trainer=trainer,
            client=client,
            prompt_inputs=audit_inputs,
            outcome=AIPlanGeneration.Outcome.FAILED,
            error_message="Library is empty. Add some exercises first.",
        )
        raise AIGenerationError("Your exercise library is empty. Add some exercises first.")

    if not settings.OPENAI_API_KEY:
        gen = AIPlanGeneration.objects.create(
            trainer=trainer,
            client=client,
            prompt_inputs=audit_inputs,
            outcome=AIPlanGeneration.Outcome.FAILED,
            error_message="OPENAI_API_KEY is not configured.",
        )
        raise AIGenerationError(
            "AI is not configured. Set OPENAI_API_KEY in the .env file to enable plan generation."
        )

    from langchain_openai import ChatOpenAI

    prompt, parser = _build_prompt()
    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=0.6,
        timeout=120,
    )
    chain = prompt | llm | parser

    inputs = {
        "client_json": _client_payload(client),
        "library_json": library,
        "weeks": weeks,
        "weekly_frequency": client.weekly_frequency,
    }

    last_error: Optional[str] = None
    raw = None
    for attempt in (1, 2):
        try:
            result = chain.invoke(inputs)
            raw = result if isinstance(result, dict) else result.model_dump()
            plan = PlanResponse.model_validate(raw)
            _validate_against_library(plan, allowed_ids)
            outcome = (
                AIPlanGeneration.Outcome.SUCCESS
                if attempt == 1
                else AIPlanGeneration.Outcome.RETRY
            )
            AIPlanGeneration.objects.create(
                trainer=trainer,
                client=client,
                prompt_inputs=audit_inputs,
                raw_response=raw,
                outcome=outcome,
            )
            return plan, raw
        except (ValidationError, AIGenerationError, Exception) as exc:  # noqa: BLE001
            last_error = str(exc)
            log.warning("AI plan generation attempt %s failed: %s", attempt, exc)

    AIPlanGeneration.objects.create(
        trainer=trainer,
        client=client,
        prompt_inputs=audit_inputs,
        raw_response=raw,
        outcome=AIPlanGeneration.Outcome.FAILED,
        error_message=last_error or "unknown",
    )
    detail = (last_error or "unknown").splitlines()[0][:240]
    raise AIGenerationError(f"AI request failed: {detail}")

def save_plan(client: Client, plan: PlanResponse) -> TrainingPlan:

    trainer = client.trainer
    tp = TrainingPlan.objects.create(
        trainer=trainer,
        client=client,
        name=plan.name,
        description=plan.rationale,
        weeks=plan.weeks,
        current_week=1,
        is_active=True,
        generated_by_ai=True,
    )
    for d_idx, day in enumerate(plan.days):
        pd = PlanDay.objects.create(plan=tp, label=day.label, order=d_idx)
        for x_idx, e in enumerate(day.exercises):
            exercise = Exercise.objects.filter(pk=e.exercise_id, trainer=trainer).first()
            if not exercise:
                continue
            PlanExercise.objects.create(
                day=pd,
                exercise=exercise,
                order=x_idx,
                sets=e.sets,
                reps=e.reps,
                rest_seconds=e.rest_seconds,
                coaching_notes=e.coaching_notes,
            )
    return tp
