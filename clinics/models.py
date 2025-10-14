from __future__ import annotations

from django.db import models


class Department(models.Model):
    code = models.CharField("科別代碼", max_length=10, unique=True)
    name = models.CharField("科別名稱", max_length=100, unique=True)
    description = models.TextField("介紹", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "科別"
        verbose_name_plural = "科別"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
