from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    PatientPasswordChangeDoneView,
    PatientPasswordChangeView,
    PatientProfileUpdateView,
    PatientRegisterView,
    ProfileView,
    RoleBasedDashboardRedirectView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", PatientProfileUpdateView.as_view(), name="profile-edit"),
    path("password-change/", PatientPasswordChangeView.as_view(), name="password-change"),
    path("password-change/done/", PatientPasswordChangeDoneView.as_view(), name="password-change-done"),
    path("switch-dashboard/", RoleBasedDashboardRedirectView.as_view(), name="switch"),
    path("register/", PatientRegisterView.as_view(), name="register"),
]
