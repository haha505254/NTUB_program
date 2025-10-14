from django.contrib.auth import views as auth_views
from django.urls import path

from .views import ProfileView, RoleBasedDashboardRedirectView

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("switch-dashboard/", RoleBasedDashboardRedirectView.as_view(), name="switch"),
]
