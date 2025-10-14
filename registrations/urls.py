from django.urls import path

from .views import (
    ClinicStatusView,
    DoctorDashboardView,
    StaffAppointmentCancelView,
    StaffAppointmentCheckInView,
    StaffDashboardView,
    StaffOnsiteAppointmentView,
    StaffPatientCreateView,
    StaffPatientUpdateView,
)

app_name = "registrations"

urlpatterns = [
    path("staff/dashboard/", StaffDashboardView.as_view(), name="staff-dashboard"),
    path("staff/patients/create/", StaffPatientCreateView.as_view(), name="staff-patient-create"),
    path("staff/patients/<int:pk>/update/", StaffPatientUpdateView.as_view(), name="staff-patient-update"),
    path(
        "staff/patients/<int:patient_id>/appointments/create/",
        StaffOnsiteAppointmentView.as_view(),
        name="staff-appointment-create",
    ),
    path(
        "staff/appointments/<int:pk>/check-in/",
        StaffAppointmentCheckInView.as_view(),
        name="staff-appointment-check-in",
    ),
    path(
        "staff/appointments/<int:pk>/cancel/",
        StaffAppointmentCancelView.as_view(),
        name="staff-appointment-cancel",
    ),
    path("doctor/dashboard/", DoctorDashboardView.as_view(), name="doctor-dashboard"),
    path("clinic-status/", ClinicStatusView.as_view(), name="clinic-status"),
]
