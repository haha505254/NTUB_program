from __future__ import annotations

from django.conf import settings
from django.db import models

from clinics.models import Department
from patients.models import FamilyMember, Patient


class Doctor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="doctors")
    license_number = models.CharField("醫師證書號", max_length=30, unique=True)
    title = models.CharField("職稱", max_length=50, blank=True)
    specialties = models.CharField("專長", max_length=255, blank=True)
    bio = models.TextField("簡介", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "醫師"
        verbose_name_plural = "醫師"
        ordering = ["department__name", "user__last_name"]

    def __str__(self) -> str:
        return f"{self.user.display_name} / {self.department.name}"


class DoctorSchedule(models.Model):
    class Session(models.TextChoices):
        MORNING = "morning", "上午"
        AFTERNOON = "afternoon", "下午"
        EVENING = "evening", "夜間"

    class Status(models.TextChoices):
        OPEN = "open", "可掛號"
        CLOSED = "closed", "已額滿"
        PAUSED = "paused", "暫停掛號"
        ENDED = "ended", "看診結束"

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="schedules")
    date = models.DateField()
    session = models.CharField(max_length=20, choices=Session.choices)
    clinic_room = models.CharField("診間", max_length=20, blank=True)
    quota = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    open_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "班表"
        verbose_name_plural = "班表"
        unique_together = ("doctor", "date", "session")
        ordering = ["date", "session"]

    def __str__(self) -> str:
        return f"{self.doctor} {self.date} {self.get_session_display()}"

    @property
    def capacity_used(self) -> int:
        return self.appointments.exclude(status=Appointment.Status.CANCELLED).count()

    def next_queue_number(self) -> int:
        return self.appointments.count() + 1


class Appointment(models.Model):
    class Status(models.TextChoices):
        RESERVED = "reserved", "已預約"
        CHECKED_IN = "checked_in", "已報到"
        IN_PROGRESS = "in_progress", "看診中"
        COMPLETED = "completed", "已完成"
        CANCELLED = "cancelled", "已取消"

    schedule = models.ForeignKey(DoctorSchedule, on_delete=models.CASCADE, related_name="appointments")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    family_member = models.ForeignKey(
        FamilyMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    queue_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)
    check_in_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "掛號"
        verbose_name_plural = "掛號"
        unique_together = ("schedule", "queue_number")
        ordering = ["schedule", "queue_number"]

    def __str__(self) -> str:
        return f"{self.schedule} #{self.queue_number}"


class AppointmentEventLog(models.Model):
    class Event(models.TextChoices):
        BOOKED = "booked", "預約"
        CHECKED_IN = "checked_in", "報到"
        CALLED = "called", "叫號"
        COMPLETED = "completed", "完成"
        CANCELLED = "cancelled", "取消"
        SYSTEM = "system", "系統事件"

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="events")
    event = models.CharField(max_length=30, choices=Event.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_events",
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "掛號事件紀錄"
        verbose_name_plural = "掛號事件紀錄"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_event_display()} @ {self.created_at:%Y-%m-%d %H:%M}"
