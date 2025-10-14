from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import RedirectView, TemplateView


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"


class RoleBasedDashboardRedirectView(LoginRequiredMixin, RedirectView):
    """依使用者角色轉導至對應儀表板。"""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):  # type: ignore[override]
        user = self.request.user
        if hasattr(user, "is_doctor") and user.is_doctor():
            return reverse("registrations:doctor-dashboard")
        if hasattr(user, "is_staff_member") and user.is_staff_member():
            return reverse("registrations:staff-dashboard")
        if user.is_superuser or getattr(user, "role", "") == "admin":
            return reverse("administration:dashboard")
        return reverse("patients:dashboard")
