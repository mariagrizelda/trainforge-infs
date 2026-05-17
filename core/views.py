
from .views_auth import landing, login_view, signup_view, logout_view  # noqa: F401
from .views_dashboard import dashboard  # noqa: F401
from .views_clients import (  # noqa: F401
    clients_list,
    client_create,
    client_detail,
    client_edit,
    client_archive,
    client_restore,
)
from .views_exercises import (  # noqa: F401
    exercises_list,
    exercise_create,
    exercise_edit,
    exercise_archive,
)
from .views_plans import (  # noqa: F401
    plan_create,
    plan_detail,
    plan_edit,
    plan_archive,
    plan_day_create,
    plan_exercise_create,
    plan_day_delete,
    plan_exercise_delete,
)
from .views_calendar import (  # noqa: F401
    calendar_view,
    appointment_create,
    appointment_edit,
    appointment_delete,
)
from .views_progress import (  # noqa: F401
    progress_index,
    progress_view,
    session_log_create,
)
from .views_ai import (  # noqa: F401
    ai_plan_page,
    ai_plan_generate,
    ai_plan_save,
)
from .views_admin import (  # noqa: F401
    admin_dashboard,
    admin_plans,
    admin_plan_create,
    admin_plan_edit,
    admin_plan_archive,
    admin_trainers,
    admin_trainer_assign,
    admin_trainer_cancel,
)
