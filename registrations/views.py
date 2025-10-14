from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from patients.models import Patient

from .forms import (
    ClinicStatusFilterForm,
    OnsiteAppointmentForm,
    PatientLookupForm,
    StaffPatientCreationForm,
    StaffPatientProfileForm,
)
from .models import Appointment, AppointmentEventLog, DoctorSchedule


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):  # pragma: no cover - 簡單角色檢查
        user = self.request.user
        role = getattr(user, "role", "")
        return user.is_superuser or role in {"staff", "admin"}


class DoctorRequiredMixin(UserPassesTestMixin):
    def test_func(self):  # pragma: no cover - 簡單角色檢查
        user = self.request.user
        role = getattr(user, "role", "")
        return user.is_superuser or role in {"doctor", "admin"}


class StaffDashboardView(StaffRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "registrations/staff_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_form = PatientLookupForm(self.request.GET or None)
        context["search_form"] = search_form
        context["patient_create_form"] = StaffPatientCreationForm()
        patient = None
        if search_form.is_valid():
            identifier = search_form.cleaned_data.get("identifier")
            if identifier:
                patient = self._find_patient(identifier)
                if patient is None and self.request.GET.get("identifier"):
                    messages.info(self.request, f"找不到與 {identifier} 相符的病患。")
        if patient:
            context["selected_patient"] = patient
            context["patient_form"] = StaffPatientProfileForm(patient=patient)
            context["appointment_form"] = OnsiteAppointmentForm(patient=patient, actor=self.request.user)
            context["appointments"] = list(
                patient.appointments.select_related(
                    "schedule",
                    "schedule__doctor",
                    "schedule__doctor__department",
                ).order_by("schedule__date", "queue_number")
            )
        else:
            context["selected_patient"] = None
            context["appointments"] = []
        return context

    def _find_patient(self, identifier: str) -> Patient | None:
        return (
            Patient.objects.select_related("user")
            .filter(Q(medical_record_number__iexact=identifier) | Q(national_id__iexact=identifier))
            .first()
        )


class StaffPatientCreateView(StaffRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = StaffPatientCreationForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(
                request,
                f"已建立病患 {patient.user.display_name}，病歷號 {patient.medical_record_number}。",
            )
            redirect_url = f"{reverse('registrations:staff-dashboard')}?identifier={patient.medical_record_number}"
            return redirect(redirect_url)
        self._report_form_errors(request, form)
        return redirect(reverse("registrations:staff-dashboard"))

    @staticmethod
    def _report_form_errors(request, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":
                    messages.error(request, error)
                else:
                    messages.error(request, f"[{form.fields[field].label}] {error}")


class StaffPatientUpdateView(StaffRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        patient = get_object_or_404(Patient.objects.select_related("user"), pk=pk)
        form = StaffPatientProfileForm(request.POST, patient=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "已更新病患資料。")
        else:
            StaffPatientCreateView._report_form_errors(request, form)
        redirect_url = f"{reverse('registrations:staff-dashboard')}?identifier={patient.medical_record_number}"
        return redirect(redirect_url)


class StaffOnsiteAppointmentView(StaffRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, patient_id, *args, **kwargs):
        patient = get_object_or_404(Patient.objects.select_related("user"), pk=patient_id)
        form = OnsiteAppointmentForm(request.POST, patient=patient, actor=request.user)
        if form.is_valid():
            try:
                appointment = form.save()
            except forms.ValidationError as exc:  # pragma: no cover - 表單驗證
                messages.error(request, "; ".join(exc.messages))
            else:
                messages.success(
                    request,
                    f"已為 {appointment.patient.user.display_name} 掛號 {appointment.schedule} ，號碼 {appointment.queue_number}。",
                )
                redirect_url = f"{reverse('registrations:staff-dashboard')}?identifier={patient.medical_record_number}"
                return redirect(redirect_url)
        else:
            StaffPatientCreateView._report_form_errors(request, form)
        redirect_url = f"{reverse('registrations:staff-dashboard')}?identifier={patient.medical_record_number}"
        return redirect(redirect_url)


class StaffAppointmentCheckInView(StaffRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        appointment = get_object_or_404(
            Appointment.objects.select_related("patient__user", "schedule"),
            pk=pk,
        )
        if appointment.status == Appointment.Status.CANCELLED:
            messages.warning(request, "此掛號已取消，無法報到。")
        elif appointment.status == Appointment.Status.CHECKED_IN:
            messages.info(request, "此掛號已完成報到。")
        elif appointment.status in {Appointment.Status.IN_PROGRESS, Appointment.Status.COMPLETED}:
            messages.info(request, "此掛號已開始或完成看診。")
        else:
            with transaction.atomic():
                appointment.status = Appointment.Status.CHECKED_IN
                appointment.check_in_at = timezone.now()
                appointment.save(update_fields=["status", "check_in_at", "updated_at"])
                AppointmentEventLog.objects.create(
                    appointment=appointment,
                    event=AppointmentEventLog.Event.CHECKED_IN,
                    actor=request.user,
                )
            messages.success(request, "已完成報到。")
        redirect_url = f"{reverse('registrations:staff-dashboard')}?identifier={appointment.patient.medical_record_number}"
        return redirect(redirect_url)


class StaffAppointmentCancelView(StaffRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        appointment = get_object_or_404(
            Appointment.objects.select_related("patient__user", "schedule"),
            pk=pk,
        )
        if appointment.status == Appointment.Status.CANCELLED:
            messages.info(request, "此掛號已取消。")
        elif appointment.status == Appointment.Status.COMPLETED:
            messages.warning(request, "看診已完成，無法取消。")
        else:
            with transaction.atomic():
                appointment.status = Appointment.Status.CANCELLED
                appointment.cancelled_at = timezone.now()
                appointment.save(update_fields=["status", "cancelled_at", "updated_at"])
                AppointmentEventLog.objects.create(
                    appointment=appointment,
                    event=AppointmentEventLog.Event.CANCELLED,
                    actor=request.user,
                )
            messages.success(request, "已取消掛號。")
        redirect_url = f"{reverse('registrations:staff-dashboard')}?identifier={appointment.patient.medical_record_number}"
        return redirect(redirect_url)


class DoctorDashboardView(DoctorRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "registrations/doctor_dashboard.html"


class ClinicStatusView(StaffRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "registrations/clinic_status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ClinicStatusFilterForm(self.request.GET or None)
        context["filter_form"] = form

        schedules = (
            DoctorSchedule.objects.select_related("doctor", "doctor__user", "doctor__department")
            .prefetch_related("appointments", "appointments__patient__user", "appointments__family_member")
            .order_by("date", "session", "doctor__department__name", "doctor__user__last_name")
        )

        selected_date = timezone.localdate()
        if form.is_valid():
            date = form.cleaned_data.get("date")
            if date:
                selected_date = date
            department = form.cleaned_data.get("department")
            doctor = form.cleaned_data.get("doctor")
            if department:
                schedules = schedules.filter(doctor__department=department)
            if doctor:
                schedules = schedules.filter(doctor=doctor)
        schedules = schedules.filter(date=selected_date)

        schedule_data: list[dict] = []
        for schedule in schedules:
            appointments = sorted(schedule.appointments.all(), key=lambda a: a.queue_number)
            waiting = sum(1 for a in appointments if a.status == Appointment.Status.RESERVED)
            checked_in = sum(1 for a in appointments if a.status == Appointment.Status.CHECKED_IN)
            in_progress = sum(1 for a in appointments if a.status == Appointment.Status.IN_PROGRESS)
            completed = sum(1 for a in appointments if a.status == Appointment.Status.COMPLETED)
            cancelled = sum(1 for a in appointments if a.status == Appointment.Status.CANCELLED)
            current_number = max(
                (a.queue_number for a in appointments if a.status in {Appointment.Status.IN_PROGRESS, Appointment.Status.COMPLETED}),
                default=0,
            )
            schedule_data.append(
                {
                    "schedule": schedule,
                    "appointments": appointments,
                    "counts": {
                        "waiting": waiting,
                        "checked_in": checked_in,
                        "in_progress": in_progress,
                        "completed": completed,
                        "cancelled": cancelled,
                        "current_number": current_number,
                        "total_active": waiting + checked_in + in_progress + completed,
                    },
                }
            )

        context["selected_date"] = selected_date
        context["schedules"] = schedule_data
        return context
