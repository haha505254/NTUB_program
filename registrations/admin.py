from django.contrib import admin

from .models import Appointment, AppointmentEventLog, Doctor, DoctorSchedule


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "license_number", "is_active")
    search_fields = ("user__username", "user__last_name", "license_number")
    list_filter = ("department", "is_active")


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ("doctor", "date", "session", "status", "quota", "capacity_used")
    list_filter = ("date", "session", "status", "doctor__department")
    search_fields = ("doctor__user__last_name", "doctor__department__name")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("schedule", "queue_number", "patient", "status", "created_at")
    list_filter = ("status", "schedule__date", "schedule__doctor__department")
    search_fields = ("patient__user__last_name", "patient__medical_record_number")


@admin.register(AppointmentEventLog)
class AppointmentEventLogAdmin(admin.ModelAdmin):
    list_display = ("appointment", "event", "actor", "created_at")
    list_filter = ("event", "created_at")
    search_fields = ("appointment__patient__user__last_name",)
