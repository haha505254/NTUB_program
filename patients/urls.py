from django.urls import path

from .views import AppointmentListView, PatientDashboardView

app_name = "patients"

urlpatterns = [
    path("dashboard/", PatientDashboardView.as_view(), name="dashboard"),
    path("appointments/", AppointmentListView.as_view(), name="appointments"),
]
