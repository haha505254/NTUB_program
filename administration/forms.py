from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from clinics.models import Department
from registrations.models import Doctor, DoctorSchedule

from .models import Announcement


User = get_user_model()


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["code", "name", "description", "is_active"]
        labels = {
            "code": "科別代碼",
            "name": "科別名稱",
            "description": "介紹",
            "is_active": "啟用",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        return code

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        return name


class DoctorCreateForm(forms.Form):
    username = forms.CharField(label="登入帳號", max_length=150)
    password1 = forms.CharField(label="初始密碼", widget=forms.PasswordInput)
    password2 = forms.CharField(label="確認密碼", widget=forms.PasswordInput)
    first_name = forms.CharField(label="名字", max_length=30)
    last_name = forms.CharField(label="姓氏", max_length=30)
    email = forms.EmailField(label="電子郵件", required=False)
    phone_number = forms.CharField(label="聯絡電話", max_length=20, required=False)
    department = forms.ModelChoiceField(
        label="科別",
        queryset=Department.objects.filter(is_active=True).order_by("name"),
    )
    license_number = forms.CharField(label="醫師證書號", max_length=30)
    title = forms.CharField(label="職稱", max_length=50, required=False)
    specialties = forms.CharField(label="專長", max_length=255, required=False)
    bio = forms.CharField(label="簡介", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    is_active = forms.BooleanField(label="啟用", required=False, initial=True)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("此登入帳號已被使用。")
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("兩次輸入的密碼不一致。")
        return password2

    def clean_license_number(self):
        license_number = self.cleaned_data["license_number"].strip().upper()
        if Doctor.objects.filter(license_number__iexact=license_number).exists():
            raise forms.ValidationError("此醫師證書號已存在。")
        return license_number

    def save(self) -> Doctor:
        cleaned = self.cleaned_data
        with transaction.atomic():
            role_value = getattr(getattr(User, "Role", None), "DOCTOR", "doctor")
            user = User.objects.create_user(
                username=cleaned["username"],
                password=cleaned["password1"],
                first_name=cleaned["first_name"].strip(),
                last_name=cleaned["last_name"].strip(),
                email=cleaned.get("email", ""),
            )
            update_fields = ["first_name", "last_name", "email"]
            if hasattr(user, "role"):
                user.role = role_value
                update_fields.append("role")
            if hasattr(user, "phone_number"):
                user.phone_number = cleaned.get("phone_number", "").strip()
                update_fields.append("phone_number")
            user.is_active = cleaned.get("is_active") or False
            update_fields.append("is_active")
            user.save(update_fields=update_fields)

            doctor = Doctor.objects.create(
                user=user,
                department=cleaned["department"],
                license_number=cleaned["license_number"],
                title=cleaned.get("title", "").strip(),
                specialties=cleaned.get("specialties", "").strip(),
                bio=cleaned.get("bio", "").strip(),
                is_active=cleaned.get("is_active") or False,
            )
        return doctor


class DoctorUpdateForm(forms.ModelForm):
    username = forms.CharField(label="登入帳號", max_length=150, disabled=True, required=False)
    first_name = forms.CharField(label="名字", max_length=30)
    last_name = forms.CharField(label="姓氏", max_length=30)
    email = forms.EmailField(label="電子郵件", required=False)
    phone_number = forms.CharField(label="聯絡電話", max_length=20, required=False)

    class Meta:
        model = Doctor
        fields = ["department", "license_number", "title", "specialties", "bio", "is_active"]
        labels = {
            "department": "科別",
            "license_number": "醫師證書號",
            "title": "職稱",
            "specialties": "專長",
            "bio": "簡介",
            "is_active": "啟用",
        }
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["department"].queryset = Department.objects.order_by("name")
        self.initial.update(
            {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone_number": getattr(user, "phone_number", ""),
            }
        )

    def clean_license_number(self):
        license_number = self.cleaned_data["license_number"].strip().upper()
        if (
            Doctor.objects.filter(license_number__iexact=license_number)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("此醫師證書號已存在。")
        return license_number

    def save(self, commit: bool = True) -> Doctor:
        doctor = super().save(commit=False)
        user = doctor.user
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data.get("email", "")
        if hasattr(user, "phone_number"):
            user.phone_number = self.cleaned_data.get("phone_number", "").strip()
        user.is_active = doctor.is_active

        if commit:
            with transaction.atomic():
                update_fields = ["first_name", "last_name", "email", "is_active"]
                if hasattr(user, "phone_number"):
                    update_fields.append("phone_number")
                user.save(update_fields=update_fields)
                doctor.save()
        return doctor


class DoctorScheduleForm(forms.ModelForm):
    class Meta:
        model = DoctorSchedule
        fields = ["doctor", "date", "session", "clinic_room", "quota", "status"]
        labels = {
            "doctor": "醫師",
            "date": "日期",
            "session": "時段",
            "clinic_room": "診間",
            "quota": "名額",
            "status": "狀態",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_queryset = Doctor.objects.select_related("user", "department").order_by(
            "department__name", "user__last_name"
        )
        if self.instance.pk:
            base_queryset = base_queryset.filter(Q(is_active=True) | Q(pk=self.instance.doctor_id))
        else:
            base_queryset = base_queryset.filter(is_active=True)
        self.fields["doctor"].queryset = base_queryset
        self.fields["quota"].widget.attrs.setdefault("min", 1)

    def _ensure_unique_schedule(self, doctor, date, session):
        qs = DoctorSchedule.objects.filter(doctor=doctor, date=date, session=session)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("該醫師在此日期與時段已有班表設定。")

    def clean(self):
        cleaned = super().clean()
        doctor = cleaned.get("doctor")
        date = cleaned.get("date")
        session = cleaned.get("session")
        if doctor and date and session:
            self._ensure_unique_schedule(doctor, date, session)
        return cleaned

    def clean_quota(self):
        quota = self.cleaned_data["quota"]
        if quota < 1:
            raise forms.ValidationError("名額至少需為 1。")
        return quota


class AppointmentReportFilterForm(forms.Form):
    start_date = forms.DateField(
        label="開始日期",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        label="結束日期",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    department = forms.ModelChoiceField(
        label="科別",
        required=False,
        queryset=Department.objects.order_by("name"),
    )
    doctor = forms.ModelChoiceField(
        label="醫師",
        required=False,
        queryset=Doctor.objects.select_related("user", "department").order_by(
            "department__name", "user__last_name"
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        department_value = None
        if self.is_bound:
            department_value = self.data.get("department")
        else:
            department_value = self.initial.get("department")
        doctor_queryset = Doctor.objects.select_related("user", "department").order_by(
            "department__name", "user__last_name"
        )
        if department_value:
            doctor_queryset = doctor_queryset.filter(department_id=department_value)
        self.fields["doctor"].queryset = doctor_queryset

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and start > end:
            raise forms.ValidationError("結束日期需晚於開始日期。")
        return cleaned


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "content", "publish_at", "expire_at", "is_active"]
        labels = {
            "title": "標題",
            "content": "內容",
            "publish_at": "發布時間",
            "expire_at": "結束時間",
            "is_active": "啟用",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 6}),
            "publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "expire_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tz = timezone.get_current_timezone()
        for field_name in ("publish_at", "expire_at"):
            value = self.initial.get(field_name)
            if value:
                localized = timezone.localtime(value, tz)
                self.initial[field_name] = localized.strftime("%Y-%m-%dT%H:%M")

    def _make_aware(self, dt):
        if dt and timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def clean_publish_at(self):
        publish_at = self.cleaned_data.get("publish_at")
        return self._make_aware(publish_at)

    def clean_expire_at(self):
        expire_at = self.cleaned_data.get("expire_at")
        return self._make_aware(expire_at)

    def clean(self):
        cleaned = super().clean()
        publish_at = cleaned.get("publish_at")
        expire_at = cleaned.get("expire_at")
        if publish_at and expire_at and expire_at <= publish_at:
            raise forms.ValidationError("結束時間需晚於發布時間。")
        return cleaned
