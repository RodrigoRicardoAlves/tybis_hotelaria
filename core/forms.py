from django import forms
from .models import Guest, Reservation, Company

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'cnpj', 'contact']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
        }

class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = ['name', 'company', 'phone', 'cpf', 'address']
        # Company agora será um <select> automático do Django

class ReservationForm(forms.ModelForm):
    is_pre_reservation = forms.BooleanField(required=False, label="É Pré-reserva?")
    class Meta:
        model = Reservation
        fields = ['bed']


# Em core/forms.py
from .models import Meal # Importe o Meal

class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = ['meal_type', 'name', 'cpf', 'company']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Hóspede/Funcionário', 'autofocus': True}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'meal_type': forms.RadioSelect(attrs={'class': 'btn-check'}),
        }