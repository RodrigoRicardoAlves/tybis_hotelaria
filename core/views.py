# core/views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models.functions import Cast
from django.db.models import IntegerField
from django.views.decorators.http import require_http_methods

from .models import Room, Bed, Reservation, Guest, Company
from .forms import GuestForm, CompanyForm


# --- FUNÇÃO AUXILIAR (Calcula a cor do quarto) ---
def _get_room_item(room):
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


# --- AÇÕES QUE ATUALIZAM O QUARTO INTEIRO (Checkout e Cancelar) ---

@login_required
def checkout(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    res.status = 'FINISHED'
    res.end_date = timezone.now()
    res.add_log(request.user, "Checkout Realizado")
    res.save()

    # CORREÇÃO DO LAYOUT: Retorna o room_card inteiro, não só a cama!
    item = _get_room_item(res.bed.room)
    return render(request, 'core/partials/room_card.html', {'item': item})


@login_required
@require_http_methods(["POST"])
def cancel_reservation(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    room = res.bed.room

    if res.status == 'PRE':
        res.delete()
        item = _get_room_item(room)
        return render(request, 'core/partials/room_card.html', {'item': item})

    return HttpResponse("Erro", status=400)


# --- AÇÕES DA CAMA (Mala e Troca) ---

@login_required
def toggle_luggage(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    res.has_luggage = not res.has_luggage
    res.add_log(request.user, "Guardou Mala" if res.has_luggage else "Retirou Mala")
    return render(request, 'core/partials/bed_card.html', {'bed': res.bed, 'res': res})


@login_required
def change_room_modal(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    available_beds = get_available_beds_query(res.guest.company.id)
    return render(request, 'core/modals/change_room.html', {'res': res, 'beds': available_beds})


@login_required
def change_room(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    new_bed_id = request.POST.get('new_bed_id')
    if new_bed_id:
        new_bed = get_object_or_404(Bed, pk=new_bed_id)
        res.bed = new_bed
        res.add_log(request.user, "Mudança de Quarto")
        res.save()
        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response
    return HttpResponse("Erro", status=400)


@login_required
def toggle_maintenance(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if not room.is_maintenance:
        has_guests = Reservation.objects.filter(bed__room=room, status__in=['ACTIVE', 'PRE']).exists()
        if has_guests:
            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({"showAlert": "🚫 Quarto Ocupado!"})
            return response
    room.is_maintenance = not room.is_maintenance
    room.save()
    response = HttpResponse(status=204)
    response['HX-Refresh'] = "true"
    return response


# --- CRIAÇÃO DE RESERVA (COM CORREÇÃO DE ERROS) ---

def get_available_beds_query(company_id=None):
    available_beds = Bed.objects.filter(room__is_maintenance=False).exclude(reservations__status__in=['ACTIVE', 'PRE'])
    if not company_id: return available_beds

    valid_bed_ids = []
    for bed in available_beds:
        roommates = Reservation.objects.filter(bed__room=bed.room, status__in=['ACTIVE', 'PRE'])
        can_enter = True
        for roommate in roommates:
            if roommate.guest.company.id != int(company_id):
                can_enter = False
                break
        if can_enter: valid_bed_ids.append(bed.id)
    return available_beds.filter(id__in=valid_bed_ids)


@login_required
def get_available_beds_htmx(request):
    company_id = request.GET.get('company')
    beds = get_available_beds_query(company_id)
    return render(request, 'core/partials/bed_options.html', {'beds': beds})


@login_required
def new_reservation_modal(request):
    form = GuestForm()
    beds = get_available_beds_query(None)
    return render(request, 'core/modals/new_reservation.html', {'form': form, 'beds': beds})


@login_required
def create_reservation(request):
    if request.method == 'POST':
        form = GuestForm(request.POST)
        bed_id = request.POST.get('bed_id')
        is_pre = request.POST.get('is_pre') == 'on'

        # 1. Valida se escolheu cama
        if not bed_id:
            form.add_error(None, "Selecione um quarto/cama.")

        if form.is_valid() and bed_id:
            guest_company = form.cleaned_data['company']
            allowed_beds = get_available_beds_query(guest_company.id)

            # 2. Valida conflito de empresa
            if not allowed_beds.filter(id=bed_id).exists():
                form.add_error(None, "Cama indisponível ou conflito de empresa.")
            else:
                # SUCESSO
                guest = form.save()
                bed = get_object_or_404(Bed, pk=bed_id)
                status = 'PRE' if is_pre else 'ACTIVE'
                res = Reservation.objects.create(guest=guest, bed=bed, status=status)
                res.add_log(request.user, "Reserva Criada", f"Quarto {bed.room.number}")

                response = HttpResponse(status=204)
                response['HX-Refresh'] = "true"
                return response

        # ERRO: Redesenha o modal com mensagens
        company_id = request.POST.get('company')
        beds = get_available_beds_query(company_id) if company_id else []
        return render(request, 'core/modals/new_reservation.html', {
            'form': form, 'beds': beds, 'selected_bed_id': int(bed_id) if bed_id else None
        })

    return HttpResponse("Erro", status=400)


# --- EMPRESAS E CHECK-IN ---

@login_required
def company_list(request):
    companies = Company.objects.all()
    return render(request, 'core/company_list.html', {'companies': companies})


@login_required
def company_create(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid(): form.save(); return redirect('company_list')
    else:
        form = CompanyForm()
    return render(request, 'core/company_form.html', {'form': form, 'title': 'Nova Empresa'})


@login_required
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid(): form.save(); return redirect('company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'core/company_form.html', {'form': form, 'title': 'Editar Empresa'})


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