from django.urls import path

from .views import (
    AppointmentCancelView,
    AppointmentCreateView,
    AppointmentListView,
    AppointmentProgressView,
    DoctorDetailView,
    FamilyMemberCreateView,
    FamilyMemberDeleteView,
    FamilyMemberListView,
    FamilyMemberUpdateView,
    PatientDashboardView,
    ScheduleSearchView,
)

app_name = "patients"

urlpatterns = [
    path("dashboard/", PatientDashboardView.as_view(), name="dashboard"),
    path("appointments/", AppointmentListView.as_view(), name="appointments"),
    path("appointments/<int:pk>/cancel/", AppointmentCancelView.as_view(), name="appointment-cancel"),
    path("appointments/<int:pk>/progress/", AppointmentProgressView.as_view(), name="appointment-progress"),
    path("schedules/", ScheduleSearchView.as_view(), name="schedule-search"),
    path("schedules/<int:pk>/book/", AppointmentCreateView.as_view(), name="appointment-book"),
    path("doctors/<int:pk>/", DoctorDetailView.as_view(), name="doctor-detail"),
    path("family/", FamilyMemberListView.as_view(), name="family"),
    path("family/add/", FamilyMemberCreateView.as_view(), name="family-add"),
    path("family/<int:pk>/edit/", FamilyMemberUpdateView.as_view(), name="family-edit"),
    path("family/<int:pk>/delete/", FamilyMemberDeleteView.as_view(), name="family-delete"),
]
