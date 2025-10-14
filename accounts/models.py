from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom使用者模型，加入角色資訊以支援多種入口。"""

    class Role(models.TextChoices):
        PATIENT = "patient", "病患"
        STAFF = "staff", "櫃檯人員"
        DOCTOR = "doctor", "醫師"
        ADMIN = "admin", "系統管理員"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "使用者"
        verbose_name_plural = "使用者"

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username

    def is_patient(self) -> bool:  # pragma: no cover - 簡單取用邏輯
        return self.role == self.Role.PATIENT

    def is_staff_member(self) -> bool:
        return self.role == self.Role.STAFF

    def is_doctor(self) -> bool:
        return self.role == self.Role.DOCTOR

    def __str__(self) -> str:
        return f"{self.display_name} ({self.get_role_display()})"
