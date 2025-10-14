from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from patients.models import Patient

from .models import User


class HospitalUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("role", "phone_number")


class HospitalUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


class PatientRegistrationForm(UserCreationForm):
    first_name = forms.CharField(label="名字", max_length=30)
    last_name = forms.CharField(label="姓氏", max_length=30)
    birth_date = forms.DateField(label="生日", widget=forms.DateInput(attrs={"type": "date"}))
    phone_number = forms.CharField(label="聯絡電話", max_length=20)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "身分證號"
        self.fields["username"].help_text = "此欄位將作為登入帳號使用。"
        self.fields["email"].required = False

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.phone_number = self.cleaned_data["phone_number"]
        user.role = User.Role.PATIENT
        if commit:
            user.save()
            Patient.objects.create(
                user=user,
                national_id=self.cleaned_data["username"],
                medical_record_number=Patient.generate_medical_record_number(),
                birth_date=self.cleaned_data["birth_date"],
                phone=self.cleaned_data["phone_number"],
            )
        return user


class PatientProfileForm(forms.Form):
    first_name = forms.CharField(label="名字", max_length=30)
    last_name = forms.CharField(label="姓氏", max_length=30)
    email = forms.EmailField(label="電子郵件", required=False)
    phone_number = forms.CharField(label="聯絡電話", max_length=20, required=False)
    birth_date = forms.DateField(label="生日", widget=forms.DateInput(attrs={"type": "date"}))
    address = forms.CharField(label="地址", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    emergency_contact = forms.CharField(label="緊急聯絡人", required=False)

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.patient = getattr(user, "patient_profile", None)
        if self.patient is None:
            raise ValueError("PatientProfileForm requires user with patient_profile")
        self.initial.update(
            {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone_number": user.phone_number,
                "birth_date": self.patient.birth_date,
                "address": self.patient.address,
                "emergency_contact": self.patient.emergency_contact,
            }
        )

    def save(self):
        data = self.cleaned_data
        user = self.user
        patient = self.patient
        user.first_name = data["first_name"]
        user.last_name = data["last_name"]
        user.email = data["email"]
        user.phone_number = data["phone_number"]
        patient.birth_date = data["birth_date"]
        patient.address = data["address"]
        patient.emergency_contact = data["emergency_contact"]
        user.save(update_fields=["first_name", "last_name", "email", "phone_number"])
        patient.save(update_fields=["birth_date", "address", "emergency_contact"])
        return user
