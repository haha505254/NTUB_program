from django.urls import path

from .views import DepartmentListView

app_name = "clinics"

urlpatterns = [
    path("departments/", DepartmentListView.as_view(), name="departments"),
]
