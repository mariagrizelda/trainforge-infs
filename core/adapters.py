

from __future__ import annotations

import random

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

AVATAR_COLORS = [
    "#1F3A8A",
    "#C7416F",
    "#6F94B0",
    "#7BA89A",
    "#A8759A",
    "#D97757",
    "#1F7A4C",
    "#3F3F3F",
]

def _pick_color(seed: str) -> str:

    rng = random.Random(seed or "tf")
    return rng.choice(AVATAR_COLORS)

class TFAccountAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)

        if not user.username:
            user.username = user.email
        if not user.avatar_color or user.avatar_color == "#203F9A":
            user.avatar_color = _pick_color(user.email)
        if not user.role:
            user.role = "trainer"
        if commit:
            user.save()
        return user

class TFSocialAccountAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):

        user = super().populate_user(request, sociallogin, data)

        email = (data.get("email") or "").lower()
        if email and not user.email:
            user.email = email

        if not user.username:
            user.username = email or sociallogin.account.uid

        if not user.full_name:
            first = data.get("first_name") or ""
            last = data.get("last_name") or ""
            name = (first + " " + last).strip()
            if not name:

                name = data.get("name") or ""
            if not name and email:
                name = email.split("@")[0]
            user.full_name = name

        if not user.role:
            user.role = "trainer"

        if not user.avatar_color or user.avatar_color == "#203F9A":
            user.avatar_color = _pick_color(email or user.username)

        return user
