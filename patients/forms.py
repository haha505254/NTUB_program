from __future__ import annotations

from django import forms

from .models import FamilyMember, Patient


class FamilyMemberForm(forms.ModelForm):
    birth_date = forms.DateField(
        label="生日",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = FamilyMember
        fields = ["full_name", "relationship", "national_id", "birth_date", "phone", "notes"]
        labels = {
            "full_name": "姓名",
            "relationship": "關係",
            "national_id": "身分證/護照",
            "phone": "聯絡電話",
            "notes": "備註",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, patient: Patient, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = patient

    def save(self, commit: bool = True):
        member = super().save(commit=False)
        member.patient = self.patient
        if commit:
            member.save()
        return member
