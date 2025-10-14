from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from clinics.models import Department
from patients.models import FamilyMember, Patient
from .models import Appointment, AppointmentEventLog, Doctor, DoctorSchedule


class ScheduleSearchForm(forms.Form):
    date = forms.DateField(label="看診日期", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    department = forms.ModelChoiceField(
        label="科別",
        required=False,
        queryset=Department.objects.filter(is_active=True).order_by("name"),
        empty_label="全部科別",
    )


class AppointmentBookingForm(forms.Form):
    family_member = forms.ModelChoiceField(label="就診對象", required=False, queryset=FamilyMember.objects.none())
    notes = forms.CharField(label="備註", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, patient: Patient, schedule: DoctorSchedule, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient
        self.schedule = schedule
        self.fields["family_member"].queryset = patient.family_members.all()
        self.fields["family_member"].empty_label = "本人"

    def clean(self):
        cleaned = super().clean()
        schedule = self.schedule
        if schedule.status not in {DoctorSchedule.Status.OPEN, DoctorSchedule.Status.CLOSED}:
            raise forms.ValidationError("該時段目前未開放掛號。")
        if schedule.capacity_used >= schedule.quota:
            raise forms.ValidationError("此時段額滿，請選擇其他時段。")
        # 不允許同日同時段重複預約
        if Appointment.objects.filter(schedule=schedule, patient=self.patient).exclude(
            status=Appointment.Status.CANCELLED
        ).exists():
            raise forms.ValidationError("您已經預約該時段，無需重複預約。")
        return cleaned

    def save(self) -> Appointment:
        family_member = self.cleaned_data.get("family_member")
        notes = self.cleaned_data.get("notes", "")
        with transaction.atomic():
            locked_schedule = (
                DoctorSchedule.objects.select_for_update()
                .select_related("doctor", "doctor__user")
                .get(pk=self.schedule.pk)
            )
            if locked_schedule.capacity_used >= locked_schedule.quota:
                raise forms.ValidationError("此時段額滿，請選擇其他時段。")
            next_number = locked_schedule.next_queue_number()
            appointment = Appointment.objects.create(
                schedule=locked_schedule,
                patient=self.patient,
                family_member=family_member,
                queue_number=next_number,
                notes=notes,
            )
            AppointmentEventLog.objects.create(
                appointment=appointment,
                event=AppointmentEventLog.Event.BOOKED,
                actor=self.patient.user,
                payload={"notes": notes},
            )
        return appointment


class PatientLookupForm(forms.Form):
    identifier = forms.CharField(label="病歷號或身分證號", max_length=20, required=False)

    def clean_identifier(self):
        identifier = self.cleaned_data.get("identifier", "").strip().upper()
        return identifier


class StaffPatientCreationForm(forms.Form):
    national_id = forms.CharField(label="身分證號", max_length=20)
    first_name = forms.CharField(label="名字", max_length=30)
    last_name = forms.CharField(label="姓氏", max_length=30)
    email = forms.EmailField(label="電子郵件", required=False)
    phone_number = forms.CharField(label="聯絡電話", max_length=20)
    birth_date = forms.DateField(label="生日", widget=forms.DateInput(attrs={"type": "date"}))
    address = forms.CharField(label="地址", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    emergency_contact = forms.CharField(label="緊急聯絡人", required=False, max_length=255)
    password1 = forms.CharField(label="初始密碼", widget=forms.PasswordInput)
    password2 = forms.CharField(label="確認密碼", widget=forms.PasswordInput)

    def clean_national_id(self):
        national_id = self.cleaned_data["national_id"].strip().upper()
        User = get_user_model()
        if User.objects.filter(username__iexact=national_id).exists():
            raise forms.ValidationError("此身分證號已建立帳號。")
        if Patient.objects.filter(national_id__iexact=national_id).exists():
            raise forms.ValidationError("此身分證號已存在病患資料。")
        return national_id

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("兩次輸入的密碼不一致。")
        return cleaned

    def save(self) -> Patient:
        User = get_user_model()
        national_id = self.cleaned_data["national_id"]
        first_name = self.cleaned_data["first_name"].strip()
        last_name = self.cleaned_data["last_name"].strip()
        email = self.cleaned_data.get("email", "")
        phone_number = self.cleaned_data["phone_number"].strip()
        birth_date = self.cleaned_data["birth_date"]
        address = self.cleaned_data.get("address", "")
        emergency_contact = self.cleaned_data.get("emergency_contact", "")
        password = self.cleaned_data["password1"]
        with transaction.atomic():
            role_value = getattr(getattr(User, "Role", None), "PATIENT", "patient")
            user = User.objects.create_user(
                username=national_id,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                role=role_value,
            )
            if hasattr(user, "role") and user.role != role_value:
                user.role = role_value
                user.save(update_fields=["role"])
            patient = Patient.objects.create(
                user=user,
                national_id=national_id,
                medical_record_number=Patient.generate_medical_record_number(),
                birth_date=birth_date,
                phone=phone_number,
                address=address,
                emergency_contact=emergency_contact,
            )
        return patient


class StaffPatientProfileForm(forms.Form):
    national_id = forms.CharField(label="身分證號", max_length=20)
    first_name = forms.CharField(label="名字", max_length=30)
    last_name = forms.CharField(label="姓氏", max_length=30)
    email = forms.EmailField(label="電子郵件", required=False)
    phone_number = forms.CharField(label="聯絡電話", max_length=20)
    birth_date = forms.DateField(label="生日", widget=forms.DateInput(attrs={"type": "date"}))
    address = forms.CharField(label="地址", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    emergency_contact = forms.CharField(label="緊急聯絡人", required=False, max_length=255)

    def __init__(self, *args, patient: Patient, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient
        user = patient.user
        self.initial.update(
            {
                "national_id": patient.national_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone_number": user.phone_number,
                "birth_date": patient.birth_date,
                "address": patient.address,
                "emergency_contact": patient.emergency_contact,
            }
        )

    def clean_national_id(self):
        national_id = self.cleaned_data["national_id"].strip().upper()
        if national_id != self.patient.national_id:
            if Patient.objects.filter(national_id__iexact=national_id).exclude(pk=self.patient.pk).exists():
                raise forms.ValidationError("此身分證號已與其他病患綁定。")
            User = get_user_model()
            if User.objects.filter(username__iexact=national_id).exclude(pk=self.patient.user.pk).exists():
                raise forms.ValidationError("此身分證號已被其他帳號使用。")
        return national_id

    def save(self):
        data = self.cleaned_data
        patient = self.patient
        user = patient.user
        user.username = data["national_id"]
        user.first_name = data["first_name"].strip()
        user.last_name = data["last_name"].strip()
        user.email = data.get("email", "")
        user.phone_number = data["phone_number"].strip()
        patient.national_id = data["national_id"]
        patient.birth_date = data["birth_date"]
        patient.phone = data["phone_number"].strip()
        patient.address = data.get("address", "")
        patient.emergency_contact = data.get("emergency_contact", "")
        with transaction.atomic():
            user.save(update_fields=["username", "first_name", "last_name", "email", "phone_number"])
            patient.save(update_fields=["national_id", "birth_date", "phone", "address", "emergency_contact", "updated_at"])
        return patient


class OnsiteAppointmentForm(forms.Form):
    schedule = forms.ModelChoiceField(label="門診時段", queryset=DoctorSchedule.objects.none())
    family_member = forms.ModelChoiceField(label="就診對象", required=False, queryset=FamilyMember.objects.none())
    notes = forms.CharField(label="備註", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, patient: Patient, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient
        self.actor = actor
        self.fields["family_member"].queryset = patient.family_members.all()
        self.fields["family_member"].empty_label = "本人"
        today = timezone.localdate()
        self.fields["schedule"].queryset = (
            DoctorSchedule.objects.filter(date__gte=today)
            .select_related("doctor", "doctor__user", "doctor__department")
            .order_by("date", "session", "doctor__department__name")
        )

    def clean_schedule(self):
        schedule: DoctorSchedule = self.cleaned_data["schedule"]
        if schedule.status not in {DoctorSchedule.Status.OPEN, DoctorSchedule.Status.CLOSED}:
            raise forms.ValidationError("該時段目前未開放掛號。")
        if schedule.capacity_used >= schedule.quota:
            raise forms.ValidationError("此時段額滿，請選擇其他時段。")
        return schedule

    def clean(self):
        cleaned = super().clean()
        schedule: DoctorSchedule | None = cleaned.get("schedule")
        if schedule and Appointment.objects.filter(schedule=schedule, patient=self.patient).exclude(
            status=Appointment.Status.CANCELLED
        ).exists():
            raise forms.ValidationError("此病患已經掛此時段。")
        return cleaned

    def save(self) -> Appointment:
        family_member = self.cleaned_data.get("family_member")
        notes = self.cleaned_data.get("notes", "")
        with transaction.atomic():
            locked_schedule = (
                DoctorSchedule.objects.select_for_update()
                .select_related("doctor", "doctor__user")
                .get(pk=self.cleaned_data["schedule"].pk)
            )
            if locked_schedule.capacity_used >= locked_schedule.quota:
                raise forms.ValidationError("此時段額滿，請選擇其他時段。")
            next_number = locked_schedule.next_queue_number()
            appointment = Appointment.objects.create(
                schedule=locked_schedule,
                patient=self.patient,
                family_member=family_member,
                queue_number=next_number,
                notes=notes,
            )
            AppointmentEventLog.objects.create(
                appointment=appointment,
                event=AppointmentEventLog.Event.BOOKED,
                actor=self.actor,
                payload={"notes": notes, "source": "staff"},
            )
        return appointment


class ClinicStatusFilterForm(forms.Form):
    date = forms.DateField(label="日期", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    department = forms.ModelChoiceField(
        label="科別",
        required=False,
        queryset=Department.objects.filter(is_active=True).order_by("name"),
        empty_label="全部科別",
    )
    doctor = forms.ModelChoiceField(
        label="醫師",
        required=False,
        queryset=Doctor.objects.filter(is_active=True).select_related("user", "department").order_by(
            "department__name", "user__last_name"
        ),
        empty_label="全部醫師",
    )

    def clean_doctor(self):
        doctor = self.cleaned_data.get("doctor")
        if doctor is not None and not doctor.is_active:
            raise forms.ValidationError("該醫師目前未開放門診。")
        return doctor
