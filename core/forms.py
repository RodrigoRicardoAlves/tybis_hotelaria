# core/forms.py
from django import forms
from .models import Guest, Reservation

class GuestForm(forms.ModelForm):
    class Meta:
        model = Guest
        fields = ['name', 'company', 'phone', 'cpf', 'address']

class ReservationForm(forms.ModelForm):
    # Campo extra para definir se é pré-reserva ou não
    is_pre_reservation = forms.BooleanField(required=False, label="É Pré-reserva?")

    class Meta:
        model = Reservation
        fields = ['bed'] # O hóspede a gente trata na view