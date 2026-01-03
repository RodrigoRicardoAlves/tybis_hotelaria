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