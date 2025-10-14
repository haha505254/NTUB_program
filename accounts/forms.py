from __future__ import annotations

from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class HospitalUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("role", "phone_number")


class HospitalUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
