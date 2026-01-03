# core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from .models import Room, Bed, Reservation, Guest
from .forms import GuestForm


@login_required
def dashboard(request):
    """Tela Principal: Monta a tabela de quartos"""
    rooms = Room.objects.all().order_by('number')

    dashboard_data = []
    for room in rooms:
        beds_data = []
        for bed in room.beds.all():
            # Pega reserva ativa ou pré-reserva
            res = bed.reservations.filter(status__in=['ACTIVE', 'PRE']).first()
            beds_data.append({'bed': bed, 'res': res})

        dashboard_data.append({'room': room, 'beds': beds_data})

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
    """Trava o quarto inteiro"""
    room = get_object_or_404(Room, pk=pk)
    room.is_maintenance = not room.is_maintenance
    room.save()
    # O HTMX vai recarregar a página para atualizar o visual do quarto todo
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