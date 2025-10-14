from __future__ import annotations

from django.views.generic import ListView

from .models import Department


class DepartmentListView(ListView):
    template_name = "clinics/departments.html"
    context_object_name = "departments"

    def get_queryset(self):  # pragma: no cover
        return Department.objects.filter(is_active=True)
