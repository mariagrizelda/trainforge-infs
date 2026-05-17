
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Appointment, BodyMetric, Client, Exercise, PlanDay, PlanExercise, SessionLog, SetLog, TrainingPlan

User = get_user_model()

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember = forms.BooleanField(required=False)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        data = super().clean()
        email = data.get("email")
        password = data.get("password")
        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError("Email or password is wrong.")
            self.user = user
        return data

class SignupForm(forms.Form):
    full_name = forms.CharField(max_length=120)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    terms = forms.BooleanField()

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("That email is already in use.")
        return email.lower()

    def clean_password(self):
        pw = self.cleaned_data["password"]
        validate_password(pw)
        return pw

    def save(self):
        return User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            full_name=self.cleaned_data["full_name"],
            role=User.Role.TRAINER,
        )

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "full_name",
            "email",
            "phone",
            "goal",
            "weekly_frequency",
            "available_equipment",
            "injuries",
            "preferred_times",
            "notes",
        ]
        widgets = {
            "injuries": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = [
            "name",
            "description",
            "muscle_groups",
            "equipment",
            "difficulty",
            "default_sets",
            "default_reps",
            "default_rest_seconds",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "muscle_groups": forms.CheckboxSelectMultiple(),
        }

class TrainingPlanForm(forms.ModelForm):
    class Meta:
        model = TrainingPlan
        fields = ["name", "description", "weeks", "current_week", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

class PlanDayForm(forms.ModelForm):
    class Meta:
        model = PlanDay
        fields = ["label", "order"]

class PlanExerciseForm(forms.ModelForm):
    class Meta:
        model = PlanExercise

        fields = ["exercise", "sets", "reps", "rest_seconds", "coaching_notes"]

class _PlanDayClientWidget(forms.Select):

    def __init__(self, plan_day_to_client, *args, **kwargs):
        self._pd_to_client = plan_day_to_client
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)

        if value:
            raw = getattr(value, "value", value)
            try:
                cid = self._pd_to_client.get(int(raw))
                if cid:
                    option["attrs"]["data-client"] = str(cid)
            except (ValueError, TypeError):
                pass
        return option

class AppointmentForm(forms.ModelForm):
    start_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    class Meta:
        model = Appointment
        fields = [
            "client",
            "plan_day",
            "start_at",
            "duration_minutes",
            "status",
            "location",
            "notes",
        ]

    def __init__(self, *args, trainer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if trainer is not None:
            self.fields["client"].queryset = Client.objects.filter(
                trainer=trainer, is_archived=False
            )
            plan_days = (
                PlanDay.objects.filter(plan__trainer=trainer, plan__is_archived=False)
                .select_related("plan", "plan__client")
                .order_by("plan__client__full_name", "order")
            )
            pd_to_client = {pd.pk: pd.plan.client_id for pd in plan_days}
            self.fields["plan_day"].queryset = plan_days
            new_widget = _PlanDayClientWidget(pd_to_client)
            new_widget.choices = self.fields["plan_day"].choices
            self.fields["plan_day"].widget = new_widget
            self.fields["plan_day"].required = False

class SessionLogForm(forms.ModelForm):
    class Meta:
        model = SessionLog
        fields = ["client", "plan_day", "performed_on", "notes"]
        widgets = {
            "performed_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, trainer=None, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if trainer is not None:
            self.fields["client"].queryset = Client.objects.filter(
                trainer=trainer, is_archived=False
            )
        if client is not None:
            self.fields["plan_day"].queryset = PlanDay.objects.filter(
                plan__client=client
            )
        elif trainer is not None:
            self.fields["plan_day"].queryset = PlanDay.objects.filter(
                plan__trainer=trainer
            )
        self.fields["plan_day"].required = False

class SetLogForm(forms.ModelForm):
    class Meta:
        model = SetLog
        fields = ["exercise", "set_number", "reps", "weight_kg", "rpe"]

class BodyMetricForm(forms.ModelForm):
    class Meta:
        model = BodyMetric
        fields = ["recorded_on", "weight_kg", "body_fat_pct", "notes"]
        widgets = {"recorded_on": forms.DateInput(attrs={"type": "date"})}
