from __future__ import annotations

import datetime
from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from patients.models import Patient

from .forms import (
    ClinicStatusFilterForm,
    DoctorCallNextForm,
    DoctorCompleteAppointmentForm,
    DoctorScheduleActionForm,
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        doctor = getattr(user, "doctor_profile", None)

        date_param = self.request.GET.get("date")
        selected_date = timezone.localdate()
        if date_param:
            try:
                selected_date = datetime.date.fromisoformat(date_param)
            except ValueError:
                messages.warning(self.request, "日期格式不正確，已改為今日。")

        schedules_qs = (
            DoctorSchedule.objects.select_related("doctor", "doctor__user", "doctor__department")
            .prefetch_related(
                Prefetch(
                    "appointments",
                    queryset=Appointment.objects.select_related(
                        "patient",
                        "patient__user",
                        "family_member",
                    ).order_by("queue_number"),
                )
            )
            .filter(date=selected_date)
            .order_by("session")
        )
        if doctor:
            schedules_qs = schedules_qs.filter(doctor=doctor)

        schedules = list(schedules_qs)

        schedule_id = self.request.GET.get("schedule")
        selected_schedule = None
        if schedule_id:
            for schedule in schedules:
                if str(schedule.pk) == schedule_id:
                    selected_schedule = schedule
                    break
        if selected_schedule is None and schedules:
            selected_schedule = schedules[0]

        schedule_blocks = []
        for schedule in schedules:
            appointments = list(schedule.appointments.all())
            counts = {
                "reserved": sum(1 for a in appointments if a.status == Appointment.Status.RESERVED),
                "checked_in": sum(1 for a in appointments if a.status == Appointment.Status.CHECKED_IN),
                "in_progress": sum(1 for a in appointments if a.status == Appointment.Status.IN_PROGRESS),
                "completed": sum(1 for a in appointments if a.status == Appointment.Status.COMPLETED),
                "cancelled": sum(1 for a in appointments if a.status == Appointment.Status.CANCELLED),
            }
            counts["total"] = len(appointments)
            schedule_blocks.append({"schedule": schedule, "counts": counts})

        context.update(
            {
                "selected_date": selected_date,
                "schedule_blocks": schedule_blocks,
                "selected_schedule": selected_schedule,
            }
        )

        if selected_schedule:
            appointments = list(selected_schedule.appointments.all())
            waiting_list = [a for a in appointments if a.status == Appointment.Status.RESERVED]
            checked_in_list = [a for a in appointments if a.status == Appointment.Status.CHECKED_IN]
            in_progress_list = [a for a in appointments if a.status == Appointment.Status.IN_PROGRESS]
            completed_list = [a for a in appointments if a.status == Appointment.Status.COMPLETED]

            recent_events = (
                AppointmentEventLog.objects.filter(appointment__schedule=selected_schedule)
                .select_related("appointment", "actor")
                .order_by("-created_at")[:10]
            )

            call_form = None
            if selected_schedule.status != DoctorSchedule.Status.ENDED:
                call_form = DoctorCallNextForm(user=user, initial={"schedule_id": selected_schedule.pk})

            current_appointment = in_progress_list[0] if in_progress_list else None
            complete_form = (
                DoctorCompleteAppointmentForm(user=user, initial={"appointment_id": current_appointment.pk})
                if current_appointment
                else None
            )

            schedule_action_form = None
            available_actions: list[tuple[str, str]] = []
            if selected_schedule.status in {DoctorSchedule.Status.OPEN, DoctorSchedule.Status.CLOSED}:
                available_actions.append(
                    (
                        DoctorScheduleActionForm.Action.PAUSE,
                        DoctorScheduleActionForm.Action.PAUSE.label,
                    )
                )
            if selected_schedule.status == DoctorSchedule.Status.PAUSED:
                available_actions.append(
                    (
                        DoctorScheduleActionForm.Action.RESUME,
                        DoctorScheduleActionForm.Action.RESUME.label,
                    )
                )
            if selected_schedule.status != DoctorSchedule.Status.ENDED:
                available_actions.append(
                    (
                        DoctorScheduleActionForm.Action.END,
                        DoctorScheduleActionForm.Action.END.label,
                    )
                )
            if available_actions:
                schedule_action_form = DoctorScheduleActionForm(
                    user=user,
                    initial={"schedule_id": selected_schedule.pk},
                )
                schedule_action_form.fields["action"].choices = available_actions

            context.update(
                {
                    "waiting_appointments": waiting_list,
                    "checked_in_appointments": checked_in_list,
                    "in_progress_appointments": in_progress_list,
                    "completed_appointments": completed_list,
                    "call_form": call_form,
                    "complete_form": complete_form,
                    "schedule_action_form": schedule_action_form,
                    "recent_events": recent_events,
                    "current_appointment": current_appointment,
                }
            )

        return context


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


class DoctorBaseActionView(DoctorRequiredMixin, LoginRequiredMixin, View):
    """共用醫師操作的錯誤處理與導轉。"""

    def _report_form_errors(self, request, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":
                    messages.error(request, error)
                else:
                    label = form.fields.get(field).label if field in form.fields else field
                    messages.error(request, f"[{label}] {error}")

    def _redirect_to_schedule(self, schedule: DoctorSchedule | None):
        base = reverse("registrations:doctor-dashboard")
        if not schedule:
            return redirect(base)
        query = urlencode({"date": schedule.date.isoformat(), "schedule": schedule.pk})
        return redirect(f"{base}?{query}")


class DoctorCallNextView(DoctorBaseActionView):
    def post(self, request, *args, **kwargs):
        form = DoctorCallNextForm(request.POST, user=request.user)
        if form.is_valid():
            schedule = form.schedule
            if schedule.status == DoctorSchedule.Status.PAUSED:
                messages.warning(request, "門診目前為暫停狀態，請先恢復看診。")
                return self._redirect_to_schedule(schedule)
            if schedule.status == DoctorSchedule.Status.ENDED:
                messages.info(request, "門診已結束。")
                return self._redirect_to_schedule(schedule)

            current_in_progress = (
                schedule.appointments.filter(status=Appointment.Status.IN_PROGRESS)
                .order_by("queue_number")
                .first()
            )
            if current_in_progress:
                messages.warning(
                    request,
                    f"{current_in_progress.patient.user.display_name} 正在看診中，請先標記完成。",
                )
                return self._redirect_to_schedule(schedule)

            next_appointment = (
                schedule.appointments.filter(status=Appointment.Status.CHECKED_IN)
                .order_by("queue_number")
                .select_related("patient", "patient__user")
                .first()
            )
            if not next_appointment:
                messages.info(request, "目前沒有已報到病患可叫號。")
                return self._redirect_to_schedule(schedule)

            with transaction.atomic():
                next_appointment.status = Appointment.Status.IN_PROGRESS
                if not next_appointment.check_in_at:
                    next_appointment.check_in_at = timezone.now()
                next_appointment.save(update_fields=["status", "check_in_at", "updated_at"])
                AppointmentEventLog.objects.create(
                    appointment=next_appointment,
                    event=AppointmentEventLog.Event.CALLED,
                    actor=request.user,
                )
            messages.success(
                request,
                f"已呼叫 {next_appointment.patient.user.display_name}（#{next_appointment.queue_number}）。",
            )
            return self._redirect_to_schedule(schedule)

        self._report_form_errors(request, form)
        return redirect("registrations:doctor-dashboard")


class DoctorCompleteAppointmentView(DoctorBaseActionView):
    def post(self, request, *args, **kwargs):
        form = DoctorCompleteAppointmentForm(request.POST, user=request.user)
        if form.is_valid():
            appointment = form.appointment
            now = timezone.now()
            with transaction.atomic():
                appointment.status = Appointment.Status.COMPLETED
                appointment.completed_at = now
                appointment.save(update_fields=["status", "completed_at", "updated_at"])
                AppointmentEventLog.objects.create(
                    appointment=appointment,
                    event=AppointmentEventLog.Event.COMPLETED,
                    actor=request.user,
                )
            messages.success(
                request,
                f"已標記 {appointment.patient.user.display_name} 完成看診。",
            )
            return self._redirect_to_schedule(appointment.schedule)

        self._report_form_errors(request, form)
        return redirect("registrations:doctor-dashboard")


class DoctorScheduleActionView(DoctorBaseActionView):
    def post(self, request, *args, **kwargs):
        form = DoctorScheduleActionForm(request.POST, user=request.user)
        if form.is_valid():
            schedule = form.schedule
            action = form.cleaned_data["action"]
            now = timezone.now()

            with transaction.atomic():
                if action == DoctorScheduleActionForm.Action.PAUSE:
                    schedule.status = DoctorSchedule.Status.PAUSED
                    schedule.save(update_fields=["status", "updated_at"])
                    messages.success(request, "已暫停門診。")
                elif action == DoctorScheduleActionForm.Action.RESUME:
                    schedule.status = DoctorSchedule.Status.OPEN
                    update_fields = ["status", "updated_at"]
                    if schedule.open_at is None:
                        schedule.open_at = now
                        update_fields.append("open_at")
                    schedule.save(update_fields=update_fields)
                    messages.success(request, "已恢復看診。")
                elif action == DoctorScheduleActionForm.Action.END:
                    schedule.status = DoctorSchedule.Status.ENDED
                    schedule.close_at = now
                    schedule.save(update_fields=["status", "close_at", "updated_at"])

                    in_progress = list(
                        schedule.appointments.filter(status=Appointment.Status.IN_PROGRESS)
                        .select_related("patient", "patient__user")
                    )
                    pending_cancel = list(
                        schedule.appointments.filter(
                            status__in=[Appointment.Status.RESERVED, Appointment.Status.CHECKED_IN]
                        )
                    )
                    for appointment in in_progress:
                        appointment.status = Appointment.Status.COMPLETED
                        appointment.completed_at = now
                        appointment.save(update_fields=["status", "completed_at", "updated_at"])
                        AppointmentEventLog.objects.create(
                            appointment=appointment,
                            event=AppointmentEventLog.Event.COMPLETED,
                            actor=request.user,
                            payload={"auto": True, "reason": "clinic_closed"},
                        )
                    for appointment in pending_cancel:
                        appointment.status = Appointment.Status.CANCELLED
                        appointment.cancelled_at = now
                        appointment.save(update_fields=["status", "cancelled_at", "updated_at"])
                        AppointmentEventLog.objects.create(
                            appointment=appointment,
                            event=AppointmentEventLog.Event.CANCELLED,
                            actor=request.user,
                            payload={"auto": True, "reason": "clinic_closed"},
                        )
                    messages.success(request, "已標記門診結束，未看診的掛號將自動取消。")

            return self._redirect_to_schedule(schedule)

        self._report_form_errors(request, form)
        return redirect("registrations:doctor-dashboard")
