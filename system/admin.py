from django.contrib import admin

from .models import SystemJobLog


@admin.register(SystemJobLog)
class SystemJobLogAdmin(admin.ModelAdmin):
    list_display = ("job_name", "status", "started_at", "finished_at")
    list_filter = ("job_name", "status")
    search_fields = ("message",)
