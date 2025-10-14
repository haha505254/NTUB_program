from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string


class Patient(models.Model):
    """病患基本資料，對應帳號與病歷號。"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    national_id = models.CharField("身分證號", max_length=10, unique=True)
    medical_record_number = models.CharField("病歷號", max_length=20, unique=True)
    birth_date = models.DateField("生日")
    phone = models.CharField("聯絡電話", max_length=20)
    address = models.CharField("地址", max_length=255, blank=True)
    emergency_contact = models.CharField("緊急聯絡人", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "病患"
        verbose_name_plural = "病患"
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self) -> str:
        return f"{self.user.display_name} ({self.medical_record_number})"

    @classmethod
    def generate_medical_record_number(cls) -> str:
        """產生唯一的病歷號。"""

        while True:
            candidate = f"MRN{get_random_string(6, allowed_chars='0123456789')}"
            if not cls.objects.filter(medical_record_number=candidate).exists():
                return candidate


class FamilyMember(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="family_members",
    )
    full_name = models.CharField("姓名", max_length=100)
    relationship = models.CharField("關係", max_length=50)
    national_id = models.CharField("身分證/護照", max_length=20, blank=True)
    birth_date = models.DateField("生日", null=True, blank=True)
    phone = models.CharField("聯絡電話", max_length=20, blank=True)
    notes = models.TextField("備註", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "家屬"
        verbose_name_plural = "家屬"
        unique_together = ("patient", "full_name", "relationship")

    def __str__(self) -> str:
        return f"{self.full_name} - {self.relationship}"
