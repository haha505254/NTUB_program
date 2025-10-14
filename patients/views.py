from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView

from registrations.models import Appointment


class PatientDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "patients/dashboard.html"


class AppointmentListView(LoginRequiredMixin, ListView):
    template_name = "patients/appointments.html"
    context_object_name = "appointments"

    def get_queryset(self):  # pragma: no cover - Django QuerySet
        return (
            Appointment.objects.select_related("schedule", "schedule__doctor", "patient")
            .filter(patient__user=self.request.user)
            .order_by("-created_at")
        )
