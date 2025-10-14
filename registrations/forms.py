from __future__ import annotations

from django import forms
from django.db import transaction

from clinics.models import Department
from patients.models import FamilyMember, Patient
from .models import Appointment, AppointmentEventLog, DoctorSchedule


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
