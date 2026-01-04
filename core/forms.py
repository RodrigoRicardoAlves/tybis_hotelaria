from django import forms
from .models import Guest, Reservation, Company, Meal

# ==============================================================================
# FORMULÁRIOS ADMINISTRATIVOS
# ==============================================================================

class CompanyForm(forms.ModelForm):
    """
    Formulário para Criar/Editar Empresas.
    """
    class Meta:
        model = Company
        fields = ['name', 'cnpj', 'contact']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True, 'placeholder': 'Nome Fantasia ou Razão Social'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0001-00'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Responsável / Telefone'}),
        }


# ==============================================================================
# FORMULÁRIOS DE RESERVA
# ==============================================================================

class GuestForm(forms.ModelForm):
    """
    Formulário principal para Check-in e Pré-Reserva.
    Captura dados do hóspede. A Cama (Bed) é tratada separadamente na View/Template.
    """
    class Meta:
        model = Guest
        fields = ['name', 'company', 'phone', 'cpf', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Completo'}),
            'company': forms.Select(attrs={'class': 'form-select', 'id': 'company-select'}), # ID usado pelo HTMX
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Endereço (opcional)'}),
        }


# ==============================================================================
# FORMULÁRIOS DE REFEIÇÃO
# ==============================================================================

class MealForm(forms.ModelForm):
    """
    Formulário para emissão de Tickets de Refeição.
    """
    class Meta:
        model = Meal
        fields = ['meal_type', 'name', 'cpf', 'company']
        widgets = {
            'meal_type': forms.RadioSelect(attrs={'class': 'btn-check'}), # Renderizado como botões no template
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Hóspede/Funcionário', 'autofocus': True}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
        }