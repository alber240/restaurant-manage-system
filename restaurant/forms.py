from django import forms
from .models import Reservation

class ReservationForm(forms.ModelForm):
    """Handles reservation booking with built-in form validation."""

    class Meta:
        model = Reservation
        fields = ['name', 'email', 'phone', 'date', 'time', 'guests', 'table', 'special_requests']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'special_requests': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
        labels = {
            'email': 'Email Address (for confirmation)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
        # Make email required for non-logged-in users? (handled in view)
        self.fields['email'].required = False  # We'll enforce in view if needed