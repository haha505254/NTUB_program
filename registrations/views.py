from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class StaffDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "registrations/staff_dashboard.html"


class DoctorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "registrations/doctor_dashboard.html"


class ClinicStatusView(LoginRequiredMixin, TemplateView):
    template_name = "registrations/clinic_status.html"
