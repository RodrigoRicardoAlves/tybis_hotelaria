# core/views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models.functions import Cast
from django.db.models import IntegerField, Q
from django.views.decorators.http import require_http_methods

from .models import Room, Bed, Reservation, Guest, Company
from .forms import GuestForm, CompanyForm


def _get_room_item(room):
    """Calcula status e cores de um único quarto para renderizar o card"""
    beds_data = []
    has_active = False
    has_pre = False

    for bed in room.beds.all():
        res = bed.reservations.filter(status__in=['ACTIVE', 'PRE']).first()
        beds_data.append({'bed': bed, 'res': res})
        if res:
            if res.status == 'ACTIVE':
                has_active = True
            elif res.status == 'PRE':
                has_pre = True

    if room.is_maintenance:
        status_class = 'bg-danger-subtle text-danger-emphasis'
        status_icon = 'bi-cone-striped'
    elif has_active:
        status_class = 'bg-primary-subtle text-primary-emphasis'
        status_icon = 'bi-door-open-fill'
    elif has_pre:
        status_class = 'bg-warning-subtle text-warning-emphasis'
        status_icon = 'bi-clock-history'
    else:
        status_class = 'bg-success-subtle text-success-emphasis'
        status_icon = 'bi-door-closed'

    return {
        'room': room,
        'beds': beds_data,
        'status_class': status_class,
        'status_icon': status_icon
    }


@login_required
def dashboard(request):
    rooms = Room.objects.annotate(
        numero_ordenado=Cast('number', IntegerField())
    ).order_by('numero_ordenado')

    dashboard_data = [_get_room_item(room) for room in rooms]
    return render(request, 'core/dashboard.html', {'dashboard_data': dashboard_data})


# --- AÇÕES QUE AGORA ATUALIZAM O QUARTO INTEIRO ---

@login_required
def checkout(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    res.status = 'FINISHED'
    res.end_date = timezone.now()
    res.add_log(request.user, "Checkout Realizado")
    res.save()

    # Recalcula o status do quarto e devolve o CARD INTEIRO
    item = _get_room_item(res.bed.room)
    return render(request, 'core/partials/room_card.html', {'item': item})


@login_required
@require_http_methods(["POST"])
def cancel_reservation(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    room = res.bed.room  # Guarda a ref do quarto antes de apagar

    if res.status == 'PRE':
        res.delete()
        # Recalcula e devolve o CARD INTEIRO
        item = _get_room_item(room)
        return render(request, 'core/partials/room_card.html', {'item': item})

    return HttpResponse("Erro", status=400)


@login_required
@require_http_methods(["POST"])
def confirm_checkin(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    # ... (lógica de form save igual) ...
    form = GuestForm(request.POST, instance=res.guest)
    if form.is_valid():
        form.save()
        res.status = 'ACTIVE'
        res.start_date = timezone.now()
        res.add_log(request.user, "Check-in Confirmado")
        res.save()

        # AQUI: Retorna HTMX Refresh para garantir (ou room_card se preferir)
        # O refresh é mais seguro no check-in pois fecha o modal
        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return render(request, 'core/modals/edit_checkin.html', {'form': form, 'res': res})


# --- GESTÃO DE EMPRESAS ---

@login_required
def company_list(request):
    companies = Company.objects.all()
    return render(request, 'core/company_list.html', {'companies': companies})


@login_required
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('company_list')
    else:
        form = CompanyForm()
    return render(request, 'core/company_form.html', {'form': form, 'title': 'Nova Empresa'})


@login_required
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'core/company_form.html', {'form': form, 'title': 'Editar Empresa'})


# --- LÓGICA DE FILTRAGEM (O CORAÇÃO DO SISTEMA) ---

def get_available_beds_query(company_id=None):
    """
    Retorna camas livres.
    Se company_id for passado: O quarto deve estar VAZIO ou ter gente DA MESMA EMPRESA.
    """
    # 1. Pega todas as camas livres de manutenção e sem reserva ativa
    available_beds = Bed.objects.filter(room__is_maintenance=False).exclude(
        reservations__status__in=['ACTIVE', 'PRE']
    )

    # Se não tem empresa selecionada, retorna tudo que está livre
    if not company_id:
        return available_beds

    valid_bed_ids = []

    # 2. Filtra baseado na regra da empresa
    for bed in available_beds:
        # Quem já está neste quarto?
        roommates = Reservation.objects.filter(
            bed__room=bed.room,
            status__in=['ACTIVE', 'PRE']
        )

        can_enter = True
        for roommate in roommates:
            # Se tem alguém de OUTRA empresa, bloqueia
            # Compara o ID da empresa do hóspede com o ID solicitado
            if roommate.guest.company.id != int(company_id):
                can_enter = False
                break

        if can_enter:
            valid_bed_ids.append(bed.id)

    return available_beds.filter(id__in=valid_bed_ids)


# --- VIEWS DE RESERVA E HTMX ---

@login_required
def get_available_beds_htmx(request):
    """Atualiza o <select> de camas quando troca a empresa no modal"""
    company_id = request.GET.get('company')
    beds = get_available_beds_query(company_id)
    return render(request, 'core/partials/bed_options.html', {'beds': beds})


@login_required
def new_reservation_modal(request):
    form = GuestForm()
    # Inicialmente carrega todas as camas livres
    beds = get_available_beds_query(None)
    return render(request, 'core/modals/new_reservation.html', {'form': form, 'beds': beds})


@login_required
def create_reservation(request):
    if request.method == 'POST':
        form = GuestForm(request.POST)
        bed_id = request.POST.get('bed_id')
        is_pre = request.POST.get('is_pre') == 'on'

        if form.is_valid() and bed_id:
            # Validação extra de segurança no backend
            guest_company = form.cleaned_data['company']
            allowed_beds = get_available_beds_query(guest_company.id)

            # Se a cama escolhida não estiver na lista permitida, barra
            if not allowed_beds.filter(id=bed_id).exists():
                return HttpResponse("Erro: Conflito de empresa neste quarto.", status=400)

            guest = form.save()
            bed = get_object_or_404(Bed, pk=bed_id)

            status = 'PRE' if is_pre else 'ACTIVE'
            res = Reservation.objects.create(guest=guest, bed=bed, status=status)
            res.add_log(request.user, "Reserva Criada", f"Quarto {bed.room.number}")

            response = HttpResponse(status=204)
            response['HX-Refresh'] = "true"
            return response

    return HttpResponse("Erro ao criar reserva.", status=400)


@login_required
def change_room_modal(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    # Busca camas disponíveis para a empresa DESTE hóspede
    # Correção: Passamos o ID da empresa
    available_beds = get_available_beds_query(res.guest.company.id)
    return render(request, 'core/modals/change_room.html', {'res': res, 'beds': available_beds})


@login_required
def change_room(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    new_bed_id = request.POST.get('new_bed_id')

    if new_bed_id:
        new_bed = get_object_or_404(Bed, pk=new_bed_id)
        old_info = f"{res.bed.room.number} - {res.bed.name}"

        # Opcional: Adicionar validação de empresa aqui também para segurança extra

        res.bed = new_bed
        res.add_log(request.user, "Mudança de Quarto", f"De {old_info} para {new_bed.room.number}")
        res.save()

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return HttpResponse("Erro na troca.", status=400)


# --- AÇÕES DA RESERVA (MALA, CHECKOUT, MANUTENÇÃO) ---

@login_required
def toggle_luggage(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    res.has_luggage = not res.has_luggage

    acao = "Guardou Mala" if res.has_luggage else "Retirou Mala"
    res.add_log(request.user, acao)

    return render(request, 'core/partials/bed_card.html', {'bed': res.bed, 'res': res})


@login_required
def checkout(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    res.status = 'FINISHED'
    res.end_date = timezone.now()
    res.add_log(request.user, "Checkout Realizado")
    res.save()

    return render(request, 'core/partials/bed_card.html', {'bed': res.bed, 'res': None})


@login_required
def toggle_maintenance(request, pk):
    room = get_object_or_404(Room, pk=pk)

    if not room.is_maintenance:
        # Só trava se estiver vazio
        has_guests = Reservation.objects.filter(
            bed__room=room,
            status__in=['ACTIVE', 'PRE']
        ).exists()

        if has_guests:
            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({
                "showAlert": "🚫 Quarto Ocupado! Mude os hóspedes antes de travar."
            })
            return response

    room.is_maintenance = not room.is_maintenance
    room.save()

    response = HttpResponse(status=204)
    response['HX-Refresh'] = "true"
    return response


# --- FLUXO DE PRÉ-RESERVA (CHECK-IN / CANCELAR) ---

@login_required
def edit_checkin_modal(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    form = GuestForm(instance=res.guest)
    return render(request, 'core/modals/edit_checkin.html', {'form': form, 'res': res})


@login_required
@require_http_methods(["POST"])
def confirm_checkin(request, pk):
    res = get_object_or_404(Reservation, pk=pk)

    form = GuestForm(request.POST, instance=res.guest)
    if form.is_valid():
        form.save()

        res.status = 'ACTIVE'
        res.start_date = timezone.now()
        res.add_log(request.user, "Check-in Confirmado")
        res.save()

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return render(request, 'core/modals/edit_checkin.html', {'form': form, 'res': res})


@login_required
@require_http_methods(["POST"])
def cancel_reservation(request, pk):
    res = get_object_or_404(Reservation, pk=pk)

    if res.status == 'PRE':
        res.delete()  # Remove do banco pois era só prévia

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return HttpResponse("Apenas pré-reservas podem ser canceladas aqui.", status=400)