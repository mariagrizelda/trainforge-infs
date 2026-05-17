# TrainForge

A Django + DRF SaaS for personal trainers — INFS7202 individual project (s49057861).
Trainers add clients, build training plans, schedule sessions on a weekly calendar,
log progress with PR detection, and generate AI workout plans.

## Stack

- **Backend:** Django 5.1, Django REST Framework, SQLite (dev), session + token auth
- **Frontend:** Server-rendered Django templates with Bootstrap 5, HTMX for inline updates, Chart.js for charts
- **AI:** LangChain + OpenAI (configurable model, default `gpt-5.4-mini`) with a Pydantic schema and validation loop
- **Auth:** Django auth (email login) plus `django-allauth` for Google OAuth

## Getting started

```bash
# 1. Create + activate a virtualenv
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt   # or use the pip install line below

# 3. Apply migrations
python manage.py migrate

# 4. Seed demo data
python manage.py seed

# 5. Run the dev server
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

### Demo accounts

| Role    | Email                       | Password         |
| ------- | --------------------------- | ---------------- |
| Trainer | `maria@trainforge.test`     | `trainforge1234` |
| Admin   | `admin@trainforge.test`     | `adminadmin`     |

## Configuration

Copy `.env.example` to `.env` and edit:

```dotenv
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=1
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.4-mini
```

Without an `OPENAI_API_KEY` the AI plan generator returns a friendly "AI not configured"
message instead of crashing, and the audit log records the failure.

### Google OAuth

The "Continue with Google" button on the login and signup pages becomes
visible the moment a Google OAuth client id is set in `.env`. Setup:

1. Open <https://console.cloud.google.com/apis/credentials> and choose
   **Create credentials → OAuth client ID → Web application**.
2. Set the authorised JavaScript origin to `http://localhost:8000` (and the
   eventual production URL) and the authorised redirect URI to
   `http://localhost:8000/accounts/google/login/callback/`.
3. Copy the resulting client id and secret into `.env`:

   ```dotenv
   GOOGLE_OAUTH_CLIENT_ID=...
   GOOGLE_OAUTH_CLIENT_SECRET=...
   ```

4. Restart `runserver`. No migrations or admin steps required — the credentials
   are read from settings, not a SocialApp DB row.

When a user signs in with Google for the first time, `TFSocialAccountAdapter`
creates the matching `User` row with `role=trainer`, copies `full_name` from
the Google profile, mirrors the email into the legacy `username` column, and
assigns a deterministic avatar colour from the brand palette. If a user with
the same email already exists, the social account is linked to that user
instead of creating a duplicate.

## Feature map (INFS7202 rubric)

| Rubric item | Where it lives |
| --- | --- |
| 2.1 Landing page + email/Google login | `templates/landing.html`, `auth_login.html`, `auth_signup.html`; `views_auth.py` |
| 2.2 Role authorisation | `@login_required` + DRF `IsTrainerOwned`; every queryset filters by `trainer=request.user` |
| 2.3 Admin manages SaaS subscriptions | `core/admin.py` — `SubscriptionPlanAdmin` with archive actions and paging |
| 2.4 CRUD clients | `views_clients.py`, `templates/clients_list.html`, `client_form.html`, `client_detail.html` |
| 2.5 CRUD exercises | `views_exercises.py`, `templates/exercises_list.html`, `exercise_form.html` |
| 3.4 Calendar with appointments | `views_calendar.py`, `templates/calendar.html`, `appointment_form.html` (conflict detection included) |
| 3.5 Personalised training plans with reps/notes | `views_plans.py`, `templates/plan_detail.html` |
| 3.6 Client progress tracking | `views_progress.py`, `templates/progress.html` (Chart.js line, bar, heatmap, PR list) |
| 4.1 Themed responsive design | `static/css/trainforge.css`, Bootstrap 5 grid throughout |
| 4.2 Logical workflows | Inline empty states, dashboard watchlist, conflict warnings, toast messages |
| 5.1 GenAI feature | `core/ai.py`, `views_ai.py`, `templates/ai_plan.html` — schema-constrained prompting with retry, validation against trainer library, audit log |

## Project layout

```
trainforge/                # Django project (settings, root urls)
core/                      # Single app — models, views, API, admin, seed
  models.py                # User, Subscription*, Client, Exercise, TrainingPlan, Appointment, SessionLog, AIPlanGeneration...
  api.py + serializers.py  # DRF endpoints, every viewset tenant-scoped
  views_*.py               # Server-rendered views, one module per feature
  ai.py                    # LangChain + Pydantic AI plan generator
  templatetags/tf_extras.py# dict lookup + JSON helper for templates
  management/commands/seed.py
templates/                 # Bootstrap-based templates matching the mockup aesthetic
  base.html                # Loads Bootstrap, Tenor Sans/Inter Tight fonts, HTMX, Chart.js
  _app_shell.html          # Sidebar + topbar shell for the logged-in app
  partials/                # HTMX fragments
static/css/trainforge.css  # Palette + component overrides on Bootstrap
mockups/                   # Original Tailwind HTML mockups for reference
```

## REST API

All endpoints require authentication (`Authorization: Token <token>` or session cookie).
Get a token via `POST /api/token/` with `username` (your email) and `password`.

```
GET    /api/me/
GET    /api/clients/                # tenant-scoped
POST   /api/clients/
GET    /api/exercises/
POST   /api/exercises/
GET    /api/plans/?client=<id>
GET    /api/appointments/?start=<iso>&end=<iso>
GET    /api/sessions/?client=<id>
GET    /api/body-metrics/
GET    /api/muscle-groups/          # read-only shared dictionary
```

Every list view supports `?search=`, ordering via `?ordering=`, and `?include_archived=1`
to also return archived rows.

## AI plan generator — how it works

`core/ai.py` implements **schema-constrained prompting with a validation loop** (the
approach chosen in §4 of the design document):

1. Build a structured prompt containing the client profile and the trainer's exercise
   library (with stable IDs).
2. Use LangChain's `PydanticOutputParser` to coerce the LLM output into `PlanResponse`.
3. Validate that every `exercise_id` returned belongs to the trainer's library.
4. On failure, retry **once**; if it still fails, return a friendly error so the user
   can build the plan manually.
5. Record the call in `AIPlanGeneration` with inputs, raw output, outcome and any error
   message. This audit log is visible in the Django admin.

Responsible-AI safeguards:

- Plans are always presented as a *draft* — the trainer must click **Save** to persist.
- Each plan retains `generated_by_ai=True` so it can be reviewed differently.
- Exercises are constrained to the library, preventing the model from inventing moves
  the trainer hasn't approved.
- Failures don't crash the UI — the user is always offered the manual path.

## Tests

Quick smoke run:

```bash
python manage.py check
python manage.py test  # (no test cases yet — add as needed)
```
