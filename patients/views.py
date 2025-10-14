from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormView, View

from registrations.forms import AppointmentBookingForm, ScheduleSearchForm
from registrations.models import Appointment, AppointmentEventLog, Doctor, DoctorSchedule
from .forms import FamilyMemberForm
from .models import FamilyMember


class PatientDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "patients/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = getattr(self.request.user, "patient_profile", None)
        if patient:
            upcoming = (
                Appointment.objects.filter(patient=patient, status=Appointment.Status.RESERVED)
                .order_by("schedule__date")
                .select_related("schedule", "schedule__doctor", "schedule__doctor__department")[:3]
            )
            context["upcoming_appointments"] = upcoming
            context["patient"] = patient
            context["family_count"] = patient.family_members.count()
        return context


class FamilyMemberListView(LoginRequiredMixin, TemplateView):
    template_name = "patients/family_list.html"

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "patient_profile"):
            raise Http404("需要病患身份才能管理家屬")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.request.user.patient_profile
        context["family_members"] = patient.family_members.all().order_by("full_name")
        context["form"] = FamilyMemberForm(patient=patient)
        return context


class FamilyMemberCreateView(LoginRequiredMixin, FormView):
    form_class = FamilyMemberForm
    template_name = "patients/family_form.html"
    success_url = reverse_lazy("patients:family")

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "patient_profile"):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["patient"] = self.request.user.patient_profile
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "已新增家屬資料。")
        return super().form_valid(form)


class FamilyMemberUpdateView(LoginRequiredMixin, FormView):
    form_class = FamilyMemberForm
    template_name = "patients/family_form.html"
    success_url = reverse_lazy("patients:family")

    def dispatch(self, request, *args, **kwargs):
        self.member = get_object_or_404(
            FamilyMember,
            pk=kwargs["pk"],
            patient__user=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["patient"] = self.request.user.patient_profile
        kwargs["instance"] = self.member
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "已更新家屬資料。")
        return super().form_valid(form)


class FamilyMemberDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        member = get_object_or_404(
            FamilyMember,
            pk=pk,
            patient__user=request.user,
        )
        member.delete()
        messages.success(request, "已刪除家屬資料。")
        return redirect("patients:family")


class ScheduleSearchView(LoginRequiredMixin, TemplateView):
    template_name = "patients/schedule_search.html"

    def get_form(self):
        return ScheduleSearchForm(self.request.GET or None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()
        schedules = DoctorSchedule.objects.select_related(
            "doctor",
            "doctor__user",
            "doctor__department",
        ).filter(status__in=[DoctorSchedule.Status.OPEN, DoctorSchedule.Status.CLOSED])

        if form.is_valid():
            date = form.cleaned_data.get("date")
            department = form.cleaned_data.get("department")
            if date:
                schedules = schedules.filter(date=date)
            if department:
                schedules = schedules.filter(doctor__department=department)

        schedules = schedules.order_by("date", "session", "doctor__department__name")
        context.update({
            "form": form,
            "schedules": schedules,
        })
        return context


class DoctorDetailView(LoginRequiredMixin, DetailView):
    model = Doctor
    template_name = "patients/doctor_detail.html"
    context_object_name = "doctor"


class AppointmentListView(LoginRequiredMixin, ListView):
    template_name = "patients/appointments.html"
    context_object_name = "appointments"

    def get_queryset(self):  # pragma: no cover - Django QuerySet
        return (
            Appointment.objects.select_related(
                "schedule",
                "schedule__doctor",
                "schedule__doctor__department",
                "family_member",
            )
            .filter(patient__user=self.request.user)
            .order_by("-created_at")
        )


class AppointmentProgressView(LoginRequiredMixin, TemplateView):
    template_name = "patients/appointment_progress.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = get_object_or_404(
            Appointment.objects.select_related(
                "schedule",
                "schedule__doctor",
                "schedule__doctor__department",
            ),
            pk=self.kwargs["pk"],
            patient__user=self.request.user,
        )
        schedule = appointment.schedule
        current_number = (
            schedule.appointments.filter(
                status__in=[Appointment.Status.IN_PROGRESS, Appointment.Status.COMPLETED]
            ).aggregate(max_number=Max("queue_number"))["max_number"]
            or 0
        )
        checked_in = schedule.appointments.filter(status=Appointment.Status.CHECKED_IN).count()
        waiting = schedule.appointments.filter(status=Appointment.Status.RESERVED).count()
        completed = schedule.appointments.filter(status=Appointment.Status.COMPLETED).count()
        events = (
            AppointmentEventLog.objects.filter(appointment__schedule=schedule)
            .select_related("appointment", "actor")
            .order_by("-created_at")[:10]
        )
        context.update(
            {
                "appointment": appointment,
                "schedule": schedule,
                "current_number": current_number,
                "checked_in_count": checked_in,
                "waiting_count": waiting,
                "completed_count": completed,
                "remaining": schedule.remaining_quota,
                "events": events,
            }
        )
        return context


class AppointmentCreateView(LoginRequiredMixin, FormView):
    template_name = "patients/appointment_book.html"
    form_class = AppointmentBookingForm
    success_url = reverse_lazy("patients:appointments")

    def dispatch(self, request, *args, **kwargs):
        self.schedule = get_object_or_404(
            DoctorSchedule.objects.select_related("doctor", "doctor__department", "doctor__user"),
            pk=kwargs["pk"],
        )
        patient = getattr(request.user, "patient_profile", None)
        if patient is None:
            raise Http404("需要病患身份才能預約")
        self.patient = patient
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["patient"] = self.patient
        kwargs["schedule"] = self.schedule
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["schedule"] = self.schedule
        return context

    def form_valid(self, form):
        try:
            appointment = form.save()
        except forms.ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, f"預約成功！您的號碼為 {appointment.queue_number} 號。")
        return super().form_valid(form)


class AppointmentCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(
            Appointment.objects.select_related("patient", "patient__user"),
            pk=pk,
            patient__user=request.user,
        )
        if appointment.status == Appointment.Status.CANCELLED:
            messages.info(request, "此掛號已取消。")
            return redirect("patients:appointments")

        with transaction.atomic():
            appointment.status = Appointment.Status.CANCELLED
            appointment.cancelled_at = timezone.now()
            appointment.save(update_fields=["status", "cancelled_at", "updated_at"])
            from registrations.models import AppointmentEventLog

            AppointmentEventLog.objects.create(
                appointment=appointment,
                event=AppointmentEventLog.Event.CANCELLED,
                actor=request.user,
            )
        messages.success(request, "已成功取消掛號。")
        return redirect("patients:appointments")
