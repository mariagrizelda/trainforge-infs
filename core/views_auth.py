
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm, SignupForm
from .models import User

def _home_for(user):

    if user.role == User.Role.ADMIN:
        return "admin_dashboard"
    return "dashboard"

def landing(request):
    if request.user.is_authenticated:
        return redirect(_home_for(request.user))
    return render(request, "landing.html")

def login_view(request):
    if request.user.is_authenticated:
        return redirect(_home_for(request.user))
    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        if not form.cleaned_data.get("remember"):
            request.session.set_expiry(0)
        messages.success(request, f"Welcome back, {form.user.full_name or form.user.email}.")
        return redirect(request.GET.get("next") or _home_for(form.user))
    return render(request, "auth_login.html", {"form": form})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect(_home_for(request.user))
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Welcome to TrainForge! Try adding your first client.")
        return redirect(_home_for(user))
    return render(request, "auth_signup.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.info(request, "You're signed out.")
    return redirect("landing")
