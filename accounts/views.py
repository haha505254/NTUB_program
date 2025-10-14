from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView
from django.urls import reverse, reverse_lazy
from django.views.generic import RedirectView, TemplateView
from django.views.generic.edit import FormView

from .forms import PatientProfileForm, PatientRegistrationForm


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patient"] = getattr(self.request.user, "patient_profile", None)
        return context


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


class PatientRegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = PatientRegistrationForm
    success_url = reverse_lazy("patients:dashboard")

    def form_valid(self, form):  # type: ignore[override]
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class PatientProfileUpdateView(LoginRequiredMixin, FormView):
    template_name = "accounts/profile_edit.html"
    form_class = PatientProfileForm
    success_url = reverse_lazy("accounts:profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "已更新個人資料。")
        return super().form_valid(form)


class PatientPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password-change-done")


class PatientPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"
