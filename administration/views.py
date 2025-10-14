from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, TemplateView

from .models import Announcement


class AdminRoleRequiredMixin(UserPassesTestMixin):
    def test_func(self):  # pragma: no cover
        user = self.request.user
        return user.is_superuser or getattr(user, "role", "") == "admin"


class AdminDashboardView(AdminRoleRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "administration/dashboard.html"


class AnnouncementListView(AdminRoleRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "administration/announcements.html"
    model = Announcement
    context_object_name = "announcements"
