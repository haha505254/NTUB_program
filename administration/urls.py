from django.urls import path
from django.views.generic import TemplateView

from .views import (
    AdminDashboardView,
    AnnouncementListView,
    AppointmentReportView,
    AnnouncementCreateView,
    AnnouncementUpdateView,
    AnnouncementToggleActiveView,
    AnnouncementDeleteView,
    DepartmentCreateView,
    DepartmentListView,
    DepartmentToggleActiveView,
    DepartmentUpdateView,
    DoctorCreateView,
    DoctorListView,
    DoctorToggleActiveView,
    DoctorUpdateView,
    DoctorScheduleCreateView,
    DoctorScheduleDeleteView,
    DoctorScheduleListView,
    DoctorScheduleStatusUpdateView,
    DoctorScheduleUpdateView,
)

app_name = "administration"

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="dashboard"),
    path(
        "doctors/",
        DoctorListView.as_view(),
        name="doctors",
    ),
    path("doctors/add/", DoctorCreateView.as_view(), name="doctors-add"),
    path("doctors/<int:pk>/edit/", DoctorUpdateView.as_view(), name="doctors-edit"),
    path("doctors/<int:pk>/toggle/", DoctorToggleActiveView.as_view(), name="doctors-toggle"),
    path(
        "schedules/",
        DoctorScheduleListView.as_view(),
        name="schedules",
    ),
    path("schedules/add/", DoctorScheduleCreateView.as_view(), name="schedules-add"),
    path("schedules/<int:pk>/edit/", DoctorScheduleUpdateView.as_view(), name="schedules-edit"),
    path("schedules/<int:pk>/delete/", DoctorScheduleDeleteView.as_view(), name="schedules-delete"),
    path(
        "schedules/<int:pk>/status/",
        DoctorScheduleStatusUpdateView.as_view(),
        name="schedules-status",
    ),
    path(
        "departments/",
        DepartmentListView.as_view(),
        name="departments",
    ),
    path("departments/add/", DepartmentCreateView.as_view(), name="departments-add"),
    path("departments/<int:pk>/edit/", DepartmentUpdateView.as_view(), name="departments-edit"),
    path(
        "departments/<int:pk>/toggle/",
        DepartmentToggleActiveView.as_view(),
        name="departments-toggle",
    ),
    path(
        "reports/",
        AppointmentReportView.as_view(),
        name="reports",
    ),
    path("announcements/", AnnouncementListView.as_view(), name="announcements"),
    path("announcements/add/", AnnouncementCreateView.as_view(), name="announcements-add"),
    path(
        "announcements/<int:pk>/edit/",
        AnnouncementUpdateView.as_view(),
        name="announcements-edit",
    ),
    path(
        "announcements/<int:pk>/toggle/",
        AnnouncementToggleActiveView.as_view(),
        name="announcements-toggle",
    ),
    path(
        "announcements/<int:pk>/delete/",
        AnnouncementDeleteView.as_view(),
        name="announcements-delete",
    ),
]
