from __future__ import annotations

from django.conf import settings
from django.db import models


class SystemJobLog(models.Model):
    class JobName(models.TextChoices):
        REMINDER = "reminder", "掛號提醒"
        OPEN_SLOTS = "open_slots", "開放未來掛號"
        DAILY_REPORT = "daily_report", "每日報表"
        BACKUP = "backup", "資料備份"

    class Status(models.TextChoices):
        PENDING = "pending", "執行中"
        SUCCESS = "success", "成功"
        FAILED = "failed", "失敗"

    job_name = models.CharField(max_length=50, choices=JobName.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_jobs",
    )

    class Meta:
        verbose_name = "系統作業紀錄"
        verbose_name_plural = "系統作業紀錄"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.get_job_name_display()} ({self.get_status_display()})"

    @property
    def duration_seconds(self) -> float | None:
        if not self.finished_at:
            return None
        return (self.finished_at - self.started_at).total_seconds()
