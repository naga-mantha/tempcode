from django import forms

class DummyLaborForm(forms.Form):
    name = forms.CharField(label="Labor Name", help_text="Full name")
    shift = forms.ChoiceField(choices=[("morning", "Morning"), ("evening", "Evening")])
    rate = forms.DecimalField(label="Hourly Rate", max_digits=6, decimal_places=2)
