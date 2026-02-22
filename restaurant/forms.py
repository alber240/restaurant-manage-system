from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Reservation

# ========================
# RESERVATION FORM
# ========================

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
        # Email is required for anonymous users (enforced in view)
        self.fields['email'].required = False


# ========================
# CUSTOM USER REGISTRATION FORM
# ========================

class CustomUserCreationForm(UserCreationForm):
    """
    Extends the built-in UserCreationForm to include an email field.
    The email is required and will be used for payment and order confirmations.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if field_name == 'username':
                field.widget.attrs['placeholder'] = 'Username'
            elif field_name == 'password1':
                field.widget.attrs['placeholder'] = 'Password'
            elif field_name == 'password2':
                field.widget.attrs['placeholder'] = 'Confirm password'

    def clean_email(self):
        """Ensure the email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email