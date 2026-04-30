from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Reservation

from .models import MenuItem, MenuCategory, Reservation, Table

# ========================
# RESERVATION FORM
# ========================

class ReservationForm(forms.ModelForm):
    """Form for creating reservations"""
    
    class Meta:
        model = Reservation
        fields = ['name', 'email', 'phone', 'date', 'time', 'guests', 'table', 'special_requests']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'guests': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'table': forms.Select(attrs={'class': 'form-control'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any special requests?'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show available tables (you can add logic here)
        self.fields['table'].queryset = Table.objects.all()
# ========================
# CUSTOM USER REGISTRATION FORM
# ========================

# In restaurant/forms.py, update CustomUserCreationForm:

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = False
        if commit:
            user.save()
            # Only create profile if it doesn't exist
            from restaurant.models import UserProfile
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'customer'})
        return user
    
    
    
class UserProfileForm(forms.Form):
    """Form for editing user profile"""
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    
class MenuCategoryForm(forms.ModelForm):
    """Form for creating and editing menu categories"""
    
    class Meta:
        model = MenuCategory
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'category-slug'}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if MenuCategory.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError('A category with this name already exists')
        return name
    
    
class MenuItemForm(forms.ModelForm):
    """Form for creating and editing menu items"""
    
    class Meta:
        model = MenuItem
        fields = ['name', 'description', 'price', 'category', 'stock', 'low_stock_threshold', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Item description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Quantity in stock'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Alert when stock below'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise forms.ValidationError('Price must be greater than 0')
        return price
    
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock and stock < 0:
            raise forms.ValidationError('Stock cannot be negative')
        return stock