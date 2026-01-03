# core/views.py
import json

from django.db.models.functions import Cast
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q, IntegerField
from .models import Room, Bed, Reservation, Guest
from .forms import GuestForm


@login_required
def dashboard(request):
    """Tela Principal: Monta a tabela de quartos com status calculado"""

    # --- ALTERE ESTA PARTE DA CONSULTA ---
    # Antes era: rooms = Room.objects.all().order_by('number')

    # Agora convertemos o texto '10' para o número 10 na hora de ordenar:
    rooms = Room.objects.annotate(
        numero_ordenado=Cast('number', IntegerField())
    ).order_by('numero_ordenado')
    # -------------------------------------

    dashboard_data = []
    for room in rooms:
        beds_data = []
        has_active = False
        has_pre = False

        for bed in room.beds.all():
            # Pega reserva ativa ou pré-reserva
            res = bed.reservations.filter(status__in=['ACTIVE', 'PRE']).first()
            beds_data.append({'bed': bed, 'res': res})

            if res:
                if res.status == 'ACTIVE':
                    has_active = True
                elif res.status == 'PRE':
                    has_pre = True

        # LÓGICA DE CORES DO CABEÇALHO (PRIORIDADES)
        if room.is_maintenance:
            status_class = 'bg-danger-subtle text-danger-emphasis'  # Manutenção (Vermelho)
            status_icon = 'bi-cone-striped'
        elif has_active:
            status_class = 'bg-primary-subtle text-primary-emphasis'  # Ocupado (Azul)
            status_icon = 'bi-door-open-fill'
        elif has_pre:
            status_class = 'bg-warning-subtle text-warning-emphasis'  # Pré-reserva (Amarelo)
            status_icon = 'bi-clock-history'
        else:
            status_class = 'bg-success-subtle text-success-emphasis'  # Livre (Verde)
            status_icon = 'bi-door-closed'

        dashboard_data.append({
            'room': room,
            'beds': beds_data,
            'status_class': status_class,
            'status_icon': status_icon
        })

    return render(request, 'core/dashboard.html', {'dashboard_data': dashboard_data})


@login_required
def toggle_luggage(request, pk):
    """Botão Mala: Muda ícone e salva histórico"""
    res = get_object_or_404(Reservation, pk=pk)
    res.has_luggage = not res.has_luggage

    acao = "Guardou Mala" if res.has_luggage else "Retirou Mala"
    res.add_log(request.user, acao)

    # Retorna só o pedacinho do HTML da cama
    return render(request, 'core/partials/bed_card.html', {'bed': res.bed, 'res': res})


@login_required
def checkout(request, pk):
    """Botão Checkout"""
    res = get_object_or_404(Reservation, pk=pk)
    res.status = 'FINISHED'
    res.end_date = timezone.now()
    res.add_log(request.user, "Checkout Realizado")

    # Retorna o card vazio (Livre)
    return render(request, 'core/partials/bed_card.html', {'bed': res.bed, 'res': None})


@login_required
def toggle_maintenance(request, pk):
    """Trava o quarto inteiro, mas só se estiver vazio"""
    room = get_object_or_404(Room, pk=pk)

    # Se o quarto NÃO está em manutenção (ou seja, queremos TRAVAR),
    # precisamos verificar se tem gente dentro.
    if not room.is_maintenance:
        has_guests = Reservation.objects.filter(
            bed__room=room,
            status__in=['ACTIVE', 'PRE']  # Verifica Ativos e Pré-reservas
        ).exists()

        if has_guests:
            # Retorna "Nada" (204) mas com um gatilho de erro no Header
            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({
                "showAlert": "🚫 Quarto Ocupado! Favor mudar os hóspedes antes de colocar em manutenção."
            })
            return response

    # Se estiver vazio ou se estivermos DESTRAVANDO, segue normal
    room.is_maintenance = not room.is_maintenance
    room.save()

    response = HttpResponse(status=204)
    response['HX-Refresh'] = "true"
    return response


# --- ÁREA DE NOVA RESERVA E TROCA (A Lógica da Empresa) ---

def get_available_beds_for_company(company_name=None):
    """
    Retorna camas livres.
    Se passar empresa, só retorna camas em quartos vazios
    OU quartos que já tenham alguém dessa mesma empresa.
    """
    all_beds = Bed.objects.filter(room__is_maintenance=False).exclude(reservations__status__in=['ACTIVE', 'PRE'])

    if not company_name:
        return all_beds

    valid_beds = []
    for bed in all_beds:
        # Quem está no quarto agora?
        roommates = Reservation.objects.filter(
            bed__room=bed.room,
            status__in=['ACTIVE', 'PRE']
        )

        # Se quarto vazio, ok. Se tem gente, verifica empresa.
        can_enter = True
        for roommate in roommates:
            if roommate.guest.company.lower() != company_name.lower():
                can_enter = False  # Empresa diferente, bloqueia
                break

        if can_enter:
            valid_beds.append(bed)

    return valid_beds


@login_required
def new_reservation_modal(request):
    form = GuestForm()
    # No inicio mostra todas as camas livres
    beds = get_available_beds_for_company(None)
    return render(request, 'core/modals/new_reservation.html', {'form': form, 'beds': beds})


@login_required
def create_reservation(request):
    if request.method == 'POST':
        form = GuestForm(request.POST)
        bed_id = request.POST.get('bed_id')
        is_pre = request.POST.get('is_pre') == 'on'

        if form.is_valid() and bed_id:
            guest = form.save()
            bed = get_object_or_404(Bed, pk=bed_id)

            # Validação Dupla de Empresa (Backend safety)
            # ... (código similar ao get_available_beds para garantir) ...

            status = 'PRE' if is_pre else 'ACTIVE'
            res = Reservation.objects.create(guest=guest, bed=bed, status=status)
            res.add_log(request.user, "Reserva Criada", f"Quarto {bed.room.number}")

            response = HttpResponse(status=204)
            response['HX-Refresh'] = "true"
            return response

    return HttpResponse("Erro ao criar", status=400)


@login_required
def change_room_modal(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    # Busca camas disponíveis para a empresa DELE
    available_beds = get_available_beds_for_company(res.guest.company)
    return render(request, 'core/modals/change_room.html', {'res': res, 'beds': available_beds})


@login_required
def change_room(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    new_bed_id = request.POST.get('new_bed_id')

    if new_bed_id:
        new_bed = get_object_or_404(Bed, pk=new_bed_id)
        old_info = f"{res.bed.room.number} - {res.bed.name}"

        res.bed = new_bed
        res.add_log(request.user, "Mudança de Quarto", f"De {old_info} para {new_bed.room.number}")

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return HttpResponse("Erro", status=400)