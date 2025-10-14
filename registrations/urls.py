from django.urls import path

from .views import ClinicStatusView, DoctorDashboardView, StaffDashboardView

app_name = "registrations"

urlpatterns = [
    path("staff/dashboard/", StaffDashboardView.as_view(), name="staff-dashboard"),
    path("doctor/dashboard/", DoctorDashboardView.as_view(), name="doctor-dashboard"),
    path("clinic-status/", ClinicStatusView.as_view(), name="clinic-status"),
]
