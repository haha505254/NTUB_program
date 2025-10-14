from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "publish_at", "expire_at", "is_active")
    list_filter = ("is_active", "publish_at")
    search_fields = ("title",)
