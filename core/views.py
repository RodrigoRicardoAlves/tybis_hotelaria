# core/views.py
import json

from django.db.models.functions import Cast
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q, IntegerField
from django.views.decorators.http import require_http_methods

from .models import Room, Bed, Reservation, Guest
from .forms import GuestForm

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models.functions import Cast
from django.db.models import IntegerField, Q
from django.views.decorators.http import require_http_methods
import json

from .models import Room, Bed, Reservation, Guest, Company
from .forms import GuestForm, CompanyForm


@login_required
def dashboard(request):
    # Ordenação numérica correta
    rooms = Room.objects.annotate(
        numero_ordenado=Cast('number', IntegerField())
    ).order_by('numero_ordenado')

    dashboard_data = []
    for room in rooms:
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

        dashboard_data.append({
            'room': room, 'beds': beds_data,
            'status_class': status_class, 'status_icon': status_icon
        })

    return render(request, 'core/dashboard.html', {'dashboard_data': dashboard_data})


# --- EMPRESAS ---

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


# --- RESERVAS E LÓGICA DE FILTRO ---

def get_available_beds_query(company_id=None):
    """
    Lógica Central:
    1. Camas em quartos sem manutenção.
    2. Camas que NÃO estão ocupadas.
    3. Se company_id for passado: O quarto deve estar VAZIO ou ter gente DA MESMA EMPRESA.
    """
    # Camas livres (não ocupadas e quarto ok)
    available_beds = Bed.objects.filter(room__is_maintenance=False).exclude(
        reservations__status__in=['ACTIVE', 'PRE']
    )

    if not company_id:
        # Se não escolheu empresa, mostra tudo (ou poderia mostrar nada, depende da regra)
        # Vamos mostrar tudo por enquanto, mas ao selecionar, filtraremos.
        return available_beds

    valid_bed_ids = []

    # Precisamos iterar para verificar os "vizinhos" de quarto
    # Isso pode ser otimizado com queries complexas, mas o loop é mais legível para agora.
    for bed in available_beds:
        # Pega reservas ativas NO MESMO QUARTO desta cama
        roommates = Reservation.objects.filter(
            bed__room=bed.room,
            status__in=['ACTIVE', 'PRE']
        )

        can_enter = True
        for roommate in roommates:
            # Se tem alguém de OUTRA empresa, bloqueia
            if roommate.guest.company.id != int(company_id):
                can_enter = False
                break

        if can_enter:
            valid_bed_ids.append(bed.id)

    return available_beds.filter(id__in=valid_bed_ids)


@login_required
def get_available_beds_htmx(request):
    """Retorna apenas as <options> do select baseado na empresa selecionada"""
    company_id = request.GET.get('company')
    beds = get_available_beds_query(company_id)
    return render(request, 'core/partials/bed_options.html', {'beds': beds})


@login_required
def new_reservation_modal(request):
    form = GuestForm()  # O form agora tem o select de company
    # Inicialmente carrega todas ou nenhuma cama. Vamos carregar todas livres.
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

            if not allowed_beds.filter(id=bed_id).exists():
                return HttpResponse("Erro: Cama não permitida para esta empresa (conflito de quarto).", status=400)

            guest = form.save()
            bed = get_object_or_404(Bed, pk=bed_id)

            status = 'PRE' if is_pre else 'ACTIVE'
            res = Reservation.objects.create(guest=guest, bed=bed, status=status)
            res.add_log(request.user, "Reserva Criada", f"Quarto {bed.room.number}")

            response = HttpResponse(status=204)
            response['HX-Refresh'] = "true"
            return response

    return HttpResponse("Erro ao criar", status=400)


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


# core/views.py (Adicione no final)

@login_required
def edit_checkin_modal(request, pk):
    """Abre modal para editar dados antes de confirmar o Check-in"""
    res = get_object_or_404(Reservation, pk=pk)
    form = GuestForm(instance=res.guest)  # Traz os dados já preenchidos
    return render(request, 'core/modals/edit_checkin.html', {'form': form, 'res': res})


@login_required
@require_http_methods(["POST"])
def confirm_checkin(request, pk):
    """Salva os dados editados e muda status para ACTIVE"""
    res = get_object_or_404(Reservation, pk=pk)

    # Atualiza os dados do Hóspede
    form = GuestForm(request.POST, instance=res.guest)
    if form.is_valid():
        form.save()

        # Efetiva o Check-in
        res.status = 'ACTIVE'
        res.start_date = timezone.now()  # Atualiza a data de entrada para agora
        res.add_log(request.user, "Check-in Realizado", "Confirmado via Pré-reserva")
        res.save()

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    # Se der erro no form, retorna o modal com erros
    return render(request, 'core/modals/edit_checkin.html', {'form': form, 'res': res})


@login_required
@require_http_methods(["POST"])
def cancel_reservation(request, pk):
    """Exclui a pré-reserva liberando o quarto"""
    res = get_object_or_404(Reservation, pk=pk)

    # Só permite cancelar se for PRE (segurança)
    if res.status == 'PRE':
        # Loga antes de apagar (opcional, se tivesse model de log separado)
        # Como o log fica na reserva, ele sumirá junto, mas o quarto fica livre.
        res.delete()

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return HttpResponse("Apenas pré-reservas podem ser canceladas aqui.", status=400)