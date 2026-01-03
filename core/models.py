# core/models.py
from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


class Room(models.Model):
    CLIMATE_CHOICES = [('AC', 'Ar Condicionado'), ('VENT', 'Ventilador')]
    number = models.CharField("Número", max_length=10, unique=True)
    climate = models.CharField("Climatização", max_length=10, choices=CLIMATE_CHOICES, default='VENT')
    is_maintenance = models.BooleanField("Em Manutenção", default=False)

    def __str__(self):
        return f"Quarto {self.number} ({self.get_climate_display()})"


class Bed(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    name = models.CharField("Cama", max_length=10)  # Ex: A, B, 101-A

    def __str__(self):
        return f"{self.room.number} - {self.name}"


class Guest(models.Model):
    name = models.CharField("Nome Completo", max_length=200)
    company = models.CharField("Empresa", max_length=200)
    phone = models.CharField("Telefone", max_length=20, blank=True)
    cpf = models.CharField("CPF", max_length=14, blank=True, null=True)
    address = models.TextField("Endereço", blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.company}"


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

    # O tal do histórico JSON
    history = models.JSONField("Histórico", default=list, blank=True)

    def add_log(self, user, action, details=""):
        """Grava log no JSON sem apagar o anterior"""
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