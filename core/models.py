from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


# ==============================================================================
# CADASTROS BÁSICOS (Empresa, Quarto, Cama)
# ==============================================================================

class Company(models.Model):
    """
    Representa as empresas parceiras ou 'Particular'.
    Usado para agrupar hóspedes e validar regras de negócio (uma empresa por quarto).
    """
    name = models.CharField("Nome da Empresa", max_length=200, unique=True)
    cnpj = models.CharField("CNPJ", max_length=20, blank=True, null=True)
    contact = models.CharField("Contato/Responsável", max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['name']

    def __str__(self):
        return self.name


class Room(models.Model):
    """
    Representa o quarto físico.
    Possui status de climatização e manutenção.
    """
    CLIMATE_CHOICES = [('AC', 'Ar Condicionado'), ('VENT', 'Ventilador')]

    number = models.CharField("Número", max_length=10, unique=True)
    climate = models.CharField("Climatização", max_length=10, choices=CLIMATE_CHOICES, default='VENT')
    is_maintenance = models.BooleanField("Em Manutenção", default=False)

    class Meta:
        verbose_name = "Quarto"
        verbose_name_plural = "Quartos"
        ordering = ['number']

    def __str__(self):
        return f"Quarto {self.number}"


class Bed(models.Model):
    """
    Representa uma cama dentro de um quarto (A, B, C...).
    É a unidade indivisível de reserva.
    """
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    name = models.CharField("Identificação da Cama", max_length=10, help_text="Ex: A, B, C")

    class Meta:
        verbose_name = "Cama"
        verbose_name_plural = "Camas"

    def __str__(self):
        return f"{self.room.number} - {self.name}"


# ==============================================================================
# HÓSPEDES E RESERVAS
# ==============================================================================

class Guest(models.Model):
    """
    Dados pessoais do hóspede.
    Vinculado a uma empresa para validação de regras de convivência.
    """
    name = models.CharField("Nome Completo", max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Empresa")
    phone = models.CharField("Telefone", max_length=20, blank=True)
    cpf = models.CharField("CPF", max_length=14, blank=True, null=True)
    address = models.TextField("Endereço", blank=True, null=True)

    class Meta:
        verbose_name = "Hóspede"
        verbose_name_plural = "Hóspedes"

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Reservation(models.Model):
    """
    Core do sistema. Liga um Hóspede a uma Cama por um período.
    Gerencia o status (Pré-reserva vs Hospedado) e o histórico de ações.
    """
    STATUS_CHOICES = [
        ('PRE', 'Pré-reserva'),  # Apenas intenção, não confirmou check-in
        ('ACTIVE', 'Hospedado'),  # Check-in realizado
        ('FINISHED', 'Finalizada'),  # Checkout realizado
    ]

    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, verbose_name="Hóspede")
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='reservations', verbose_name="Cama")

    start_date = models.DateTimeField("Check-in", auto_now_add=True)
    end_date = models.DateTimeField("Check-out", null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    has_luggage = models.BooleanField("Mala Guardada", default=False)

    # Armazena logs como: [{"data": "...", "acao": "Troca de Quarto", "usuario": "admin"}]
    history = models.JSONField("Histórico de Ações", default=list, blank=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"

    def add_log(self, user, action, details=""):
        """
        Adiciona uma entrada ao histórico JSON da reserva.
        """
        log_entry = {
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "usuario": user.username if user else "Sistema",
            "acao": action,
            "detalhes": details
        }
        if self.history is None: self.history = []
        self.history.append(log_entry)
        # Nota: O save() deve ser chamado externamente se necessário, ou incluído aqui.
        # Por segurança em transações, deixamos o save para a view na maioria dos casos.

    def __str__(self):
        return f"{self.guest.name} - {self.get_status_display()}"


# ==============================================================================
# REFEIÇÕES (Ticket)
# ==============================================================================

class Meal(models.Model):
    """
    Registro de tickets de alimentação (Almoço/Janta) para controle e impressão.
    """
    MEAL_CHOICES = [
        ('ALMOCO', 'Almoço'),
        ('JANTA', 'Janta'),
    ]

    name = models.CharField("Nome Completo", max_length=200)
    cpf = models.CharField("CPF", max_length=14, blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Empresa")
    meal_type = models.CharField("Tipo", max_length=10, choices=MEAL_CHOICES, default='ALMOCO')
    created_at = models.DateTimeField("Data/Hora", auto_now_add=True)

    class Meta:
        verbose_name = "Refeição"
        verbose_name_plural = "Refeições"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_meal_type_display()}"