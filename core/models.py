from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


class Company(models.Model):
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
    CLIMATE_CHOICES = [('AC', 'Ar Condicionado'), ('VENT', 'Ventilador')]
    number = models.CharField("Número", max_length=10, unique=True)
    climate = models.CharField("Climatização", max_length=10, choices=CLIMATE_CHOICES, default='VENT')
    is_maintenance = models.BooleanField("Em Manutenção", default=False)

    class Meta:
        ordering = ['number']  # Ordenação padrão (pode precisar do Cast na view ainda)

    def __str__(self):
        return f"Quarto {self.number}"


class Bed(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    name = models.CharField("Cama", max_length=10)

    def __str__(self):
        return f"{self.room.number} - {self.name}"


class Guest(models.Model):
    name = models.CharField("Nome Completo", max_length=200)
    # AQUI MUDOU: Agora é chave estrangeira para Company
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Empresa")
    phone = models.CharField("Telefone", max_length=20, blank=True)
    cpf = models.CharField("CPF", max_length=14, blank=True, null=True)
    address = models.TextField("Endereço", blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('PRE', 'Pré-reserva'),
        ('ACTIVE', 'Hospedado'),
        ('FINISHED', 'Finalizada'),
    ]

    guest = models.ForeignKey(Guest, on_delete=models.CASCADE)
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='reservations')
    start_date = models.DateTimeField("Check-in", auto_now_add=True)
    end_date = models.DateTimeField("Check-out", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    has_luggage = models.BooleanField("Mala Guardada", default=False)
    history = models.JSONField("Histórico", default=list, blank=True)

    def add_log(self, user, action, details=""):
        log_entry = {
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "usuario": user.username if user else "Sistema",
            "acao": action,
            "detalhes": details
        }
        if self.history is None: self.history = []
        self.history.append(log_entry)
        self.save()

    def __str__(self):
        return f"{self.guest.name} ({self.status})"


# No final de core/models.py
class Meal(models.Model):
    MEAL_CHOICES = [
        ('ALMOCO', 'Almoço'),
        ('JANTA', 'Janta'),
    ]

    name = models.CharField("Nome Completo", max_length=200)
    cpf = models.CharField("CPF", max_length=14, blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Empresa")
    meal_type = models.CharField("Tipo", max_length=10, choices=MEAL_CHOICES, default='ALMOCO')
    created_at = models.DateTimeField("Data/Hora", auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.meal_type}"