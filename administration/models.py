from __future__ import annotations

from django.conf import settings
from django.db import models


class Announcement(models.Model):
    title = models.CharField("標題", max_length=200)
    content = models.TextField("內容")
    publish_at = models.DateTimeField("發布時間")
    expire_at = models.DateTimeField("結束時間", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="announcements",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "系統公告"
        verbose_name_plural = "系統公告"
        ordering = ["-publish_at"]

    def __str__(self) -> str:
        return self.title
