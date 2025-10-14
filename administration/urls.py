from django.urls import path

from .views import AdminDashboardView, AnnouncementListView

app_name = "administration"

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="dashboard"),
    path("announcements/", AnnouncementListView.as_view(), name="announcements"),
]
