from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import HospitalUserChangeForm, HospitalUserCreationForm
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = HospitalUserCreationForm
    form = HospitalUserChangeForm
    model = User

    fieldsets = UserAdmin.fieldsets + (
        ("角色資訊", {"fields": ("role", "phone_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "角色資訊",
            {
                "classes": ("wide",),
                "fields": ("role", "phone_number"),
            },
        ),
    )
    list_display = ("username", "display_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
