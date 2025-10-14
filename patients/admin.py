from django.contrib import admin

from .models import FamilyMember, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("medical_record_number", "user", "national_id", "phone", "created_at")
    search_fields = ("medical_record_number", "user__username", "user__last_name", "user__first_name")
    list_filter = ("created_at",)


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "relationship", "patient")
    search_fields = ("full_name", "patient__medical_record_number")
    list_filter = ("relationship",)
