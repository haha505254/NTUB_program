from __future__ import annotations

import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.utils import timezone
from django.utils.dateparse import parse_date

from clinics.models import Department
from registrations.models import Appointment, Doctor, DoctorSchedule

from .forms import (
    DepartmentForm,
    DoctorCreateForm,
    DoctorScheduleForm,
    DoctorUpdateForm,
    AppointmentReportFilterForm,
    AnnouncementForm,
)
from .models import Announcement


class AdminRoleRequiredMixin(UserPassesTestMixin):
    def test_func(self):  # pragma: no cover
        user = self.request.user
        return user.is_superuser or getattr(user, "role", "") == "admin"


class AdminDashboardView(AdminRoleRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "administration/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_section"] = "dashboard"
        return context


class AnnouncementListView(AdminRoleRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "administration/announcements.html"
    model = Announcement
    context_object_name = "announcements"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("created_by")
            .order_by("-publish_at", "-created_at")
        )
        search = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "all")
        now = timezone.now()

        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))

        if status == "active":
            queryset = queryset.filter(
                is_active=True,
                publish_at__lte=now,
            ).filter(Q(expire_at__gte=now) | Q(expire_at__isnull=True))
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        elif status == "upcoming":
            queryset = queryset.filter(publish_at__gt=now, is_active=True)
        elif status == "expired":
            queryset = queryset.filter(expire_at__lt=now, expire_at__isnull=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context.update(
            {
                "active_section": "announcements",
                "search_query": self.request.GET.get("q", "").strip(),
                "status_filter": self.request.GET.get("status", "all"),
                "query_string": query_params.urlencode(),
            }
        )
        return context


class AnnouncementCreateView(AdminRoleRequiredMixin, LoginRequiredMixin, CreateView):
    template_name = "administration/announcements/form.html"
    form_class = AnnouncementForm
    success_url = reverse_lazy("administration:announcements")

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("publish_at", timezone.now())
        initial.setdefault("is_active", True)
        return initial

    def form_valid(self, form):
        announcement = form.save(commit=False)
        if not announcement.publish_at:
            announcement.publish_at = timezone.now()
        announcement.created_by = self.request.user
        announcement.save()
        messages.success(self.request, f"已發布公告「{announcement.title}」。")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "announcements",
                "page_title": "新增公告",
                "is_edit": False,
            }
        )
        return context


class AnnouncementUpdateView(AdminRoleRequiredMixin, LoginRequiredMixin, UpdateView):
    template_name = "administration/announcements/form.html"
    form_class = AnnouncementForm
    model = Announcement
    success_url = reverse_lazy("administration:announcements")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"已更新公告「{self.object.title}」。")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "announcements",
                "page_title": "編輯公告",
                "is_edit": True,
            }
        )
        return context


class AnnouncementToggleActiveView(AdminRoleRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        announcement.is_active = not announcement.is_active
        announcement.save(update_fields=["is_active", "updated_at"])
        status = "啟用" if announcement.is_active else "停用"
        messages.success(request, f"已{status}公告「{announcement.title}」。")
        return redirect("administration:announcements")


class AnnouncementDeleteView(AdminRoleRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        announcement.delete()
        messages.success(request, f"已移除公告「{announcement.title}」。")
        return redirect("administration:announcements")


class DepartmentListView(AdminRoleRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "administration/departments/list.html"
    model = Department
    context_object_name = "departments"

    def get_queryset(self):
        queryset = super().get_queryset().order_by("name")
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "departments",
                "search_query": self.request.GET.get("q", "").strip(),
            }
        )
        return context


class DepartmentCreateView(AdminRoleRequiredMixin, LoginRequiredMixin, CreateView):
    template_name = "administration/departments/form.html"
    form_class = DepartmentForm
    success_url = reverse_lazy("administration:departments")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"已建立科別 {self.object.name}。")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "departments",
                "page_title": "新增科別",
                "is_edit": False,
            }
        )
        return context


class DepartmentUpdateView(AdminRoleRequiredMixin, LoginRequiredMixin, UpdateView):
    template_name = "administration/departments/form.html"
    form_class = DepartmentForm
    model = Department
    success_url = reverse_lazy("administration:departments")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"已更新科別 {self.object.name}。")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "departments",
                "page_title": "編輯科別",
                "is_edit": True,
            }
        )
        return context


class DepartmentToggleActiveView(AdminRoleRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        department = get_object_or_404(Department, pk=pk)
        department.is_active = not department.is_active
        department.save(update_fields=["is_active", "updated_at"])
        status = "啟用" if department.is_active else "停用"
        messages.success(request, f"已{status}科別 {department.name}。")
        return redirect("administration:departments")


class DoctorListView(AdminRoleRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "administration/doctors/list.html"
    model = Doctor
    context_object_name = "doctors"

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("user", "department")
            .order_by("department__name", "user__last_name", "user__first_name")
        )
        search = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "all")
        department_id = self.request.GET.get("department")

        if search:
            queryset = queryset.filter(
                Q(user__last_name__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__username__icontains=search)
                | Q(license_number__icontains=search)
            )
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "doctors",
                "search_query": self.request.GET.get("q", "").strip(),
                "status_filter": self.request.GET.get("status", "all"),
                "department_filter": self.request.GET.get("department", ""),
                "departments": Department.objects.order_by("name"),
            }
        )
        return context


class DoctorCreateView(AdminRoleRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "administration/doctors/form.html"
    form_class = DoctorCreateForm
    success_url = reverse_lazy("administration:doctors")

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f"已建立醫師 {doctor.user.display_name}。")
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "doctors",
                "page_title": "新增醫師",
                "is_edit": False,
            }
        )
        return context


class DoctorUpdateView(AdminRoleRequiredMixin, LoginRequiredMixin, UpdateView):
    template_name = "administration/doctors/form.html"
    form_class = DoctorUpdateForm
    model = Doctor
    success_url = reverse_lazy("administration:doctors")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "doctors",
                "page_title": "編輯醫師資料",
                "is_edit": True,
            }
        )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"已更新醫師 {self.object.user.display_name}。")
        return response


class DoctorToggleActiveView(AdminRoleRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        doctor = get_object_or_404(Doctor.objects.select_related("user"), pk=pk)
        doctor.is_active = not doctor.is_active
        doctor.user.is_active = doctor.is_active
        with transaction.atomic():
            doctor.save(update_fields=["is_active", "updated_at"])
            doctor.user.save(update_fields=["is_active"])
        status = "啟用" if doctor.is_active else "停用"
        messages.success(request, f"已{status}醫師 {doctor.user.display_name}。")
        return redirect("administration:doctors")


class DoctorScheduleListView(AdminRoleRequiredMixin, LoginRequiredMixin, ListView):
    template_name = "administration/schedules/list.html"
    model = DoctorSchedule
    context_object_name = "schedules"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("doctor__user", "doctor__department")
            .annotate(
                active_appointments_count=Count(
                    "appointments",
                    filter=~Q(appointments__status=Appointment.Status.CANCELLED),
                )
            )
            .order_by("date", "session", "doctor__department__name", "doctor__user__last_name")
        )
        start_param = self.request.GET.get("start", "").strip()
        end_param = self.request.GET.get("end", "").strip()
        department_id = self.request.GET.get("department")
        doctor_id = self.request.GET.get("doctor")
        status_param = self.request.GET.get("status", "all")

        start_date = parse_date(start_param) if start_param else None
        end_date = parse_date(end_param) if end_param else None

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        else:
            queryset = queryset.filter(date__gte=timezone.localdate())
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if department_id:
            queryset = queryset.filter(doctor__department_id=department_id)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        if status_param in DoctorSchedule.Status.values:
            queryset = queryset.filter(status=status_param)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "schedules",
                "departments": Department.objects.order_by("name"),
                "doctors": Doctor.objects.select_related("user").order_by(
                    "department__name", "user__last_name"
                ),
                "status_filter": self.request.GET.get("status", "all"),
                "department_filter": self.request.GET.get("department", ""),
                "doctor_filter": self.request.GET.get("doctor", ""),
                "start_filter": self.request.GET.get("start", ""),
                "end_filter": self.request.GET.get("end", ""),
                "status_choices": DoctorSchedule.Status.choices,
            }
        )
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["query_string"] = query_params.urlencode()
        return context


class DoctorScheduleCreateView(AdminRoleRequiredMixin, LoginRequiredMixin, CreateView):
    template_name = "administration/schedules/form.html"
    form_class = DoctorScheduleForm
    success_url = reverse_lazy("administration:schedules")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "已建立新的門診班表。")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "schedules",
                "page_title": "建立門診班表",
                "is_edit": False,
            }
        )
        return context


class DoctorScheduleUpdateView(AdminRoleRequiredMixin, LoginRequiredMixin, UpdateView):
    template_name = "administration/schedules/form.html"
    form_class = DoctorScheduleForm
    model = DoctorSchedule
    success_url = reverse_lazy("administration:schedules")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "已更新門診班表設定。")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "active_section": "schedules",
                "page_title": "編輯門診班表",
                "is_edit": True,
            }
        )
        return context


class DoctorScheduleDeleteView(AdminRoleRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        schedule = get_object_or_404(
            DoctorSchedule.objects.prefetch_related("appointments"), pk=pk
        )
        if schedule.appointments.exists():
            messages.error(request, "已有掛號資料，無法刪除此班表。")
        else:
            schedule.delete()
            messages.success(request, "已刪除班表。")
        return redirect("administration:schedules")


class DoctorScheduleStatusUpdateView(AdminRoleRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        schedule = get_object_or_404(DoctorSchedule, pk=pk)
        new_status = request.POST.get("status")
        valid_status = {choice[0] for choice in DoctorSchedule.Status.choices}
        if new_status not in valid_status:
            messages.error(request, "無效的狀態值。")
            return redirect("administration:schedules")

        update_fields = ["status", "updated_at"]
        now = timezone.now()
        if new_status == DoctorSchedule.Status.OPEN:
            if schedule.open_at is None:
                schedule.open_at = now
                update_fields.append("open_at")
            if schedule.close_at is not None:
                schedule.close_at = None
                update_fields.append("close_at")
        elif new_status == DoctorSchedule.Status.ENDED:
            schedule.close_at = now
            update_fields.append("close_at")
        else:
            if new_status != DoctorSchedule.Status.ENDED and schedule.close_at is not None:
                schedule.close_at = None
                update_fields.append("close_at")

        schedule.status = new_status
        schedule.save(update_fields=update_fields)
        messages.success(request, f"已更新班表狀態為「{schedule.get_status_display()}」。")
        return redirect("administration:schedules")


class AppointmentReportView(AdminRoleRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "administration/reports/appointments.html"
    form_class = AppointmentReportFilterForm

    def get(self, request, *args, **kwargs):
        self.filter_form = self.form_class(request.GET or None)
        if request.GET.get("download") == "csv" and self.filter_form.is_valid():
            queryset = self._build_queryset(self.filter_form.cleaned_data)
            totals, daily_rows, doctor_rows = self._compute_statistics(queryset)
            return self._export_csv(totals, daily_rows, doctor_rows)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = getattr(self, "filter_form", None)
        if form is None:
            form = self.form_class(self.request.GET or None)
        context["form"] = form
        context["active_section"] = "reports"
        context["has_result"] = False

        if form.is_valid():
            queryset = self._build_queryset(form.cleaned_data)
            totals, daily_rows, doctor_rows = self._compute_statistics(queryset)
            context.update(
                {
                    "has_result": True,
                    "totals": totals,
                    "daily_rows": daily_rows,
                    "doctor_rows": doctor_rows,
                }
            )

        query_params = self.request.GET.copy()
        query_params.pop("download", None)
        context["query_string"] = query_params.urlencode()
        return context

    def _build_queryset(self, filters):
        queryset = Appointment.objects.select_related(
            "schedule__doctor__user",
            "schedule__doctor__department",
        )
        start = filters.get("start_date")
        end = filters.get("end_date")
        department = filters.get("department")
        doctor = filters.get("doctor")

        if start:
            queryset = queryset.filter(schedule__date__gte=start)
        if end:
            queryset = queryset.filter(schedule__date__lte=end)
        if department:
            queryset = queryset.filter(schedule__doctor__department=department)
        if doctor:
            queryset = queryset.filter(schedule__doctor=doctor)

        return queryset

    def _compute_statistics(self, queryset):
        totals = queryset.aggregate(
            total=Count("id"),
            reserved=Count("id", filter=Q(status=Appointment.Status.RESERVED)),
            checked_in=Count("id", filter=Q(status=Appointment.Status.CHECKED_IN)),
            in_progress=Count("id", filter=Q(status=Appointment.Status.IN_PROGRESS)),
            completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
            cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
        )
        totals = {key: value or 0 for key, value in totals.items()}

        daily_rows = list(
            queryset.values("schedule__date")
            .annotate(
                total=Count("id"),
                reserved=Count("id", filter=Q(status=Appointment.Status.RESERVED)),
                checked_in=Count("id", filter=Q(status=Appointment.Status.CHECKED_IN)),
                in_progress=Count("id", filter=Q(status=Appointment.Status.IN_PROGRESS)),
                completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
                cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
            )
            .order_by("schedule__date")
        )

        doctor_rows = list(
            queryset.values(
                "schedule__doctor__id",
                "schedule__doctor__department__name",
                "schedule__doctor__user__last_name",
                "schedule__doctor__user__first_name",
            )
            .annotate(
                total=Count("id"),
                reserved=Count("id", filter=Q(status=Appointment.Status.RESERVED)),
                checked_in=Count("id", filter=Q(status=Appointment.Status.CHECKED_IN)),
                in_progress=Count("id", filter=Q(status=Appointment.Status.IN_PROGRESS)),
                completed=Count("id", filter=Q(status=Appointment.Status.COMPLETED)),
                cancelled=Count("id", filter=Q(status=Appointment.Status.CANCELLED)),
            )
            .order_by("schedule__doctor__department__name", "schedule__doctor__user__last_name")
        )

        return totals, daily_rows, doctor_rows

    def _export_csv(self, totals, daily_rows, doctor_rows):
        filename = timezone.now().strftime("appointment_report_%Y%m%d%H%M.csv")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)

        writer.writerow(["掛號統計總覽"])
        writer.writerow(["指標", "數量"])
        writer.writerow(["總計", totals["total"]])
        writer.writerow(["已預約", totals["reserved"]])
        writer.writerow(["已報到", totals["checked_in"]])
        writer.writerow(["看診中", totals["in_progress"]])
        writer.writerow(["已完成", totals["completed"]])
        writer.writerow(["已取消", totals["cancelled"]])
        writer.writerow([])

        writer.writerow(["依科別與醫師統計"])
        writer.writerow(["科別", "醫師", "總計", "已預約", "已報到", "看診中", "已完成", "已取消"])
        for row in doctor_rows:
            doctor_name = f"{row['schedule__doctor__user__last_name']}{row['schedule__doctor__user__first_name']}"
            writer.writerow(
                [
                    row["schedule__doctor__department__name"],
                    doctor_name,
                    row["total"],
                    row["reserved"],
                    row["checked_in"],
                    row["in_progress"],
                    row["completed"],
                    row["cancelled"],
                ]
            )
        writer.writerow([])

        writer.writerow(["每日統計"])
        writer.writerow(["日期", "總計", "已預約", "已報到", "看診中", "已完成", "已取消"])
        for row in daily_rows:
            writer.writerow(
                [
                    row["schedule__date"],
                    row["total"],
                    row["reserved"],
                    row["checked_in"],
                    row["in_progress"],
                    row["completed"],
                    row["cancelled"],
                ]
            )

        return response
