from __future__ import annotations

from django import forms

from .models import FamilyMember, Patient


class FamilyMemberForm(forms.ModelForm):
    birth_date = forms.DateField(
        label="生日",
        required=True,
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
        self.fields["national_id"].required = True
        self.fields["phone"].required = True
        self.fields["national_id"].help_text = "請輸入身分證或護照號碼。"
        self.fields["phone"].help_text = "請提供聯絡電話，供診間聯繫。"

    def clean_national_id(self):
        national_id = self.cleaned_data["national_id"].strip().upper()
        if not national_id:
            raise forms.ValidationError("請輸入家屬的身分證或護照號碼。")
        return national_id

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not phone:
            raise forms.ValidationError("請輸入家屬的聯絡電話。")
        return phone

    def save(self, commit: bool = True):
        member = super().save(commit=False)
        member.patient = self.patient
        if commit:
            member.save()
        return member
