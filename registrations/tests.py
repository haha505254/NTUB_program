from __future__ import annotations

import datetime

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clinics.models import Department
from patients.models import Patient
from registrations.models import Appointment, AppointmentEventLog, Doctor, DoctorSchedule


class DoctorWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(code="CARD", name="心臟內科")

        cls.doctor_user = User.objects.create_user(
            username="doc001",
            password="strong-pass",
            role=User.Role.DOCTOR,
            first_name="Dr",
            last_name="House",
        )
        cls.doctor = Doctor.objects.create(
            user=cls.doctor_user,
            department=cls.department,
            license_number="LIC001",
        )

        cls.schedule = DoctorSchedule.objects.create(
            doctor=cls.doctor,
            date=timezone.localdate(),
            session=DoctorSchedule.Session.MORNING,
            clinic_room="101",
            quota=10,
            status=DoctorSchedule.Status.OPEN,
        )

        cls.patient_user = User.objects.create_user(
            username="patient001",
            password="patient-pass",
            role=User.Role.PATIENT,
            first_name="John",
            last_name="Doe",
        )
        cls.patient = Patient.objects.create(
            user=cls.patient_user,
            national_id="A123456789",
            medical_record_number="MRN0001",
            birth_date=datetime.date(1990, 1, 1),
            phone="0912345678",
        )

        cls.patient2_user = User.objects.create_user(
            username="patient002",
            password="patient-pass",
            role=User.Role.PATIENT,
            first_name="Jane",
            last_name="Doe",
        )
        cls.patient2 = Patient.objects.create(
            user=cls.patient2_user,
            national_id="B123456789",
            medical_record_number="MRN0002",
            birth_date=datetime.date(1992, 2, 2),
            phone="0922333444",
        )

        cls.checked_in_appt = Appointment.objects.create(
            schedule=cls.schedule,
            patient=cls.patient,
            queue_number=1,
            status=Appointment.Status.CHECKED_IN,
            check_in_at=timezone.now(),
        )
        cls.reserved_appt = Appointment.objects.create(
            schedule=cls.schedule,
            patient=cls.patient2,
            queue_number=2,
            status=Appointment.Status.RESERVED,
        )

    def setUp(self):
        self.client.force_login(self.doctor_user)

    def test_dashboard_lists_schedule(self):
        url = reverse("registrations:doctor-dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("schedule_blocks", response.context)
        self.assertTrue(response.context["schedule_blocks"])
        self.assertEqual(response.context["selected_schedule"].pk, self.schedule.pk)

    def test_call_next_updates_status(self):
        url = reverse("registrations:doctor-call-next")
        response = self.client.post(url, {"schedule_id": self.schedule.pk})
        expected_redirect = f"{reverse('registrations:doctor-dashboard')}?date={self.schedule.date.isoformat()}&schedule={self.schedule.pk}"
        self.assertRedirects(response, expected_redirect, fetch_redirect_response=False)

        self.checked_in_appt.refresh_from_db()
        self.assertEqual(self.checked_in_appt.status, Appointment.Status.IN_PROGRESS)
        self.assertTrue(
            AppointmentEventLog.objects.filter(
                appointment=self.checked_in_appt,
                event=AppointmentEventLog.Event.CALLED,
            ).exists()
        )

    def test_call_next_requires_checked_in_patient(self):
        # 標記為未報到狀態
        Appointment.objects.filter(pk=self.checked_in_appt.pk).update(
            status=Appointment.Status.RESERVED,
            check_in_at=None,
        )

        url = reverse("registrations:doctor-call-next")
        response = self.client.post(url, {"schedule_id": self.schedule.pk}, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("沒有已報到" in str(message) for message in messages))

        self.checked_in_appt.refresh_from_db()
        self.assertEqual(self.checked_in_appt.status, Appointment.Status.RESERVED)
        self.assertFalse(AppointmentEventLog.objects.filter(event=AppointmentEventLog.Event.CALLED).exists())

    def test_complete_appointment_marks_done(self):
        Appointment.objects.filter(pk=self.checked_in_appt.pk).update(status=Appointment.Status.IN_PROGRESS)
        url = reverse("registrations:doctor-complete-appointment")
        response = self.client.post(url, {"appointment_id": self.checked_in_appt.pk})
        expected_redirect = f"{reverse('registrations:doctor-dashboard')}?date={self.schedule.date.isoformat()}&schedule={self.schedule.pk}"
        self.assertRedirects(response, expected_redirect, fetch_redirect_response=False)

        self.checked_in_appt.refresh_from_db()
        self.assertEqual(self.checked_in_appt.status, Appointment.Status.COMPLETED)
        self.assertTrue(
            AppointmentEventLog.objects.filter(
                appointment=self.checked_in_appt,
                event=AppointmentEventLog.Event.COMPLETED,
            ).exists()
        )

    def test_end_schedule_updates_remaining(self):
        Appointment.objects.filter(pk=self.checked_in_appt.pk).update(status=Appointment.Status.IN_PROGRESS)
        url = reverse("registrations:doctor-schedule-action")
        response = self.client.post(url, {"schedule_id": self.schedule.pk, "action": "end"})
        expected_redirect = f"{reverse('registrations:doctor-dashboard')}?date={self.schedule.date.isoformat()}&schedule={self.schedule.pk}"
        self.assertRedirects(response, expected_redirect, fetch_redirect_response=False)

        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.status, DoctorSchedule.Status.ENDED)

        self.checked_in_appt.refresh_from_db()
        self.reserved_appt.refresh_from_db()
        self.assertEqual(self.checked_in_appt.status, Appointment.Status.COMPLETED)
        self.assertEqual(self.reserved_appt.status, Appointment.Status.CANCELLED)

        events = AppointmentEventLog.objects.order_by("event")
        self.assertEqual(events.count(), 2)
        self.assertEqual({event.event for event in events}, {AppointmentEventLog.Event.COMPLETED, AppointmentEventLog.Event.CANCELLED})
