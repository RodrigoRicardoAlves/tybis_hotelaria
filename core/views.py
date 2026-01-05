# core/views.py
import json
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.db.models.functions import Cast
from django.db.models import IntegerField
from django.views.decorators.http import require_http_methods

# Imports locais
from .models import Room, Bed, Reservation, Guest, Company
from .forms import GuestForm, CompanyForm, MealForm
from .printing import imprimir_ticket_refeicao


# ==============================================================================
# 1. HELPERS & UTILITÁRIOS
# Funções auxiliares que não são views diretas, mas suportam a lógica.
# ==============================================================================

def _get_room_item(room):
    """
    Constrói o dicionário do quarto.
    Adicionado 'status_code' para facilitar a filtragem na View.
    """
    beds_data = []
    has_active = False
    has_pre = False

    for bed in room.beds.all():
        res = bed.reservations.filter(status__in=['ACTIVE', 'PRE']).first()
        beds_data.append({'bed': bed, 'res': res})
        if res:
            if res.status == 'ACTIVE': has_active = True
            elif res.status == 'PRE': has_pre = True

    # Lógica de decisão do Status
    if room.is_maintenance:
        status_class = 'bg-danger-subtle text-danger-emphasis'
        status_icon = 'bi-cone-striped'
        status_code = 'MAINTENANCE'  # Código para filtro
    elif has_active:
        status_class = 'bg-primary-subtle text-primary-emphasis'
        status_icon = 'bi-door-open-fill'
        status_code = 'OCCUPIED'
    elif has_pre:
        status_class = 'bg-warning-subtle text-warning-emphasis'
        status_icon = 'bi-clock-history'
        status_code = 'PRE'
    else:
        status_class = 'bg-success-subtle text-success-emphasis'
        status_icon = 'bi-door-closed'
        status_code = 'FREE'

    return {
        'room': room,
        'beds': beds_data,
        'status_class': status_class,
        'status_icon': status_icon,
        'status_code': status_code # Novo campo
    }


def get_available_beds_query(company_id=None):
    """
    Regra de Negócio Crucial:
    Retorna camas disponíveis, respeitando a regra de que hóspedes de
    empresas diferentes não podem dividir o mesmo quarto.
    """
    # 1. Pega todas as camas em quartos sem manutenção e sem reserva ativa/pré
    available_beds = Bed.objects.filter(room__is_maintenance=False).exclude(
        reservations__status__in=['ACTIVE', 'PRE']
    )

    # Se não selecionou empresa, retorna tudo que está tecnicamente vazio
    if not company_id:
        return available_beds

    # 2. Se tem empresa selecionada, verifica quem são os vizinhos de quarto
    valid_bed_ids = []
    target_company_id = int(company_id)

    for bed in available_beds:
        # Pega reservas ativas nas OUTRAS camas do mesmo quarto
        roommates = Reservation.objects.filter(
            bed__room=bed.room,
            status__in=['ACTIVE', 'PRE']
        )

        can_enter = True
        for roommate in roommates:
            # Se houver alguém de outra empresa, bloqueia a entrada
            if roommate.guest.company.id != target_company_id:
                can_enter = False
                break

        if can_enter:
            valid_bed_ids.append(bed.id)

    return available_beds.filter(id__in=valid_bed_ids)


# ==============================================================================
# 2. DASHBOARD (VISÃO GERAL)
# ==============================================================================

@login_required
def dashboard(request):
    # 1. Pega todos os quartos
    rooms = Room.objects.annotate(
        numero_ordenado=Cast('number', IntegerField())
    ).order_by('numero_ordenado')

    # 2. Monta a lista completa com a lógica de cores
    full_data = [_get_room_item(room) for room in rooms]

    # 3. Aplica o Filtro (se houver na URL, ex: ?filter=FREE)
    filter_type = request.GET.get('filter')

    if filter_type and filter_type != 'ALL':
        # Filtra a lista Python mantendo apenas os que batem com o status_code
        dashboard_data = [item for item in full_data if item['status_code'] == filter_type]
    else:
        dashboard_data = full_data

    # 4. Resposta Inteligente (HTMX vs Normal)
    # Se for HTMX (clique no botão), retorna só a grade. Se for acesso normal, retorna a página toda.
    if request.htmx:
        return render(request, 'core/partials/dashboard_grid.html', {'dashboard_data': dashboard_data})

    return render(request, 'core/dashboard.html', {'dashboard_data': dashboard_data, 'current_filter': filter_type})


# ==============================================================================
# 3. CICLO DE VIDA DA RESERVA (Criação, Check-in, Checkout, Cancelamento)
# ==============================================================================

@login_required
def new_reservation_modal(request):
    """
    Abre o modal de nova reserva.
    """
    form = GuestForm()
    # Inicialmente carrega camas disponíveis sem filtro de empresa
    beds = get_available_beds_query(None)
    return render(request, 'core/modals/new_reservation.html', {'form': form, 'beds': beds})


@login_required
def get_available_beds_htmx(request):
    """
    HTMX: Atualiza o <select> de camas quando o usuário troca a empresa no formulário.
    """
    company_id = request.GET.get('company')
    beds = get_available_beds_query(company_id)
    return render(request, 'core/partials/bed_options.html', {'beds': beds})


@login_required
def create_reservation(request):
    """
    Processa o formulário de criação de reserva.
    """
    if request.method == 'POST':
        form = GuestForm(request.POST)
        bed_id = request.POST.get('bed_id')
        is_pre = request.POST.get('is_pre') == 'on'

        # Validação manual da cama
        if not bed_id:
            form.add_error(None, "Selecione um quarto/cama.")

        if form.is_valid() and bed_id:
            guest_company = form.cleaned_data['company']
            allowed_beds = get_available_beds_query(guest_company.id)

            # Re-validação de segurança: verifica se a cama ainda é válida para essa empresa
            if not allowed_beds.filter(id=bed_id).exists():
                form.add_error(None, "Cama indisponível ou conflito de empresa (alguém reservou antes?).")
            else:
                # Salva Hóspede
                guest = form.save()

                # Cria Reserva
                bed = get_object_or_404(Bed, pk=bed_id)
                status = 'PRE' if is_pre else 'ACTIVE'
                res = Reservation.objects.create(guest=guest, bed=bed, status=status)

                # Log
                res.add_log(request.user, "Reserva Criada", f"Quarto {bed.room.number}")

                # Sucesso: Recarrega a página via HTMX
                response = HttpResponse(status=204)
                response['HX-Refresh'] = "true"
                return response

        # Erro: Devolve o modal com os erros
        company_id = request.POST.get('company')
        beds = get_available_beds_query(company_id) if company_id else []
        return render(request, 'core/modals/new_reservation.html', {
            'form': form,
            'beds': beds,
            'selected_bed_id': int(bed_id) if bed_id else None
        })

    return HttpResponse("Método não permitido", status=405)


@login_required
def edit_checkin_modal(request, pk):
    """
    Abre modal para confirmar check-in de uma pré-reserva.
    """
    res = get_object_or_404(Reservation, pk=pk)
    form = GuestForm(instance=res.guest)
    return render(request, 'core/modals/edit_checkin.html', {'form': form, 'res': res})


@login_required
@require_http_methods(["POST"])
def confirm_checkin(request, pk):
    """
    Efetiva o check-in: muda status PRE -> ACTIVE e define data de entrada.
    """
    res = get_object_or_404(Reservation, pk=pk)
    form = GuestForm(request.POST, instance=res.guest)

    if form.is_valid():
        form.save()  # Atualiza dados do hóspede se mudaram

        res.status = 'ACTIVE'
        res.start_date = timezone.now()
        res.add_log(request.user, "Check-in Confirmado")
        res.save()

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return render(request, 'core/modals/edit_checkin.html', {'form': form, 'res': res})


@login_required
def checkout(request, pk):
    """
    Realiza a saída do hóspede. Libera o quarto.
    """
    res = get_object_or_404(Reservation, pk=pk)
    res.status = 'FINISHED'
    res.end_date = timezone.now()
    res.add_log(request.user, "Checkout Realizado")
    res.save()

    # Atualiza visualmente o card do quarto inteiro
    item = _get_room_item(res.bed.room)
    return render(request, 'core/partials/room_card.html', {'item': item})


@login_required
@require_http_methods(["POST"])
def cancel_reservation(request, pk):
    """
    Cancela uma PRÉ-reserva (apaga do banco).
    """
    res = get_object_or_404(Reservation, pk=pk)
    room = res.bed.room

    if res.status == 'PRE':
        res.delete()
        item = _get_room_item(room)
        return render(request, 'core/partials/room_card.html', {'item': item})

    return HttpResponse("Ação inválida para reservas ativas", status=400)


# ==============================================================================
# 4. AÇÕES OPERACIONAIS (Trocas, Malas, Manutenção)
# ==============================================================================

@login_required
def toggle_luggage(request, pk):
    """
    HTMX: Alterna o ícone de 'Mala Guardada'.
    """
    res = get_object_or_404(Reservation, pk=pk)
    res.has_luggage = not res.has_luggage
    res.add_log(request.user, "Guardou Mala" if res.has_luggage else "Retirou Mala")
    res.save()

    return render(request, 'core/partials/bed_card.html', {'bed': res.bed, 'res': res})


@login_required
def change_room_modal(request, pk):
    """
    Abre modal para troca de quarto.
    """
    res = get_object_or_404(Reservation, pk=pk)
    # Busca camas disponíveis para a empresa deste hóspede
    available_beds = get_available_beds_query(res.guest.company.id)
    return render(request, 'core/modals/change_room.html', {'res': res, 'beds': available_beds})


@login_required
def change_room(request, pk):
    """
    Processa a troca de quarto.
    """
    res = get_object_or_404(Reservation, pk=pk)
    new_bed_id = request.POST.get('new_bed_id')

    if new_bed_id:
        new_bed = get_object_or_404(Bed, pk=new_bed_id)

        # Loga a mudança
        res.add_log(request.user, "Mudança de Quarto", f"De {res.bed} para {new_bed}")

        res.bed = new_bed
        res.save()

        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response

    return HttpResponse("Cama inválida", status=400)


@login_required
def toggle_maintenance(request, pk):
    """
    Coloca ou tira um quarto de manutenção.
    Impede se houver hóspedes.
    """
    room = get_object_or_404(Room, pk=pk)

    if not room.is_maintenance:
        has_guests = Reservation.objects.filter(bed__room=room, status__in=['ACTIVE', 'PRE']).exists()
        if has_guests:
            # Retorna um evento HTMX para mostrar alerta no frontend
            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({"showAlert": "🚫 Quarto Ocupado! Não é possível iniciar manutenção."})
            return response

    room.is_maintenance = not room.is_maintenance
    room.save()

    response = HttpResponse(status=204)
    response['HX-Refresh'] = "true"
    return response


# ==============================================================================
# 5. GESTÃO DE EMPRESAS
# ==============================================================================

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


# ==============================================================================
# 6. CONTROLE DE REFEIÇÕES (Ticket)
# ==============================================================================

@login_required
def meal_control(request):
    """
    Registra Almoço ou Janta e dispara impressão (Física ou Simulada).
    """
    if request.method == 'POST':
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save()

            # Tenta imprimir (Printing.py detecta se é Linux/Dev ou Windows/Prod)
            imprimiu = imprimir_ticket_refeicao(meal)

            msg = f"Refeição de {meal.name} salva!"
            if imprimiu:
                msg += " Ticket enviado para impressão."
            else:
                msg += " (Erro na impressão)."

            # Retorna o form limpo e mensagem de sucesso via HTMX
            return render(request, 'core/partials/meal_form_content.html', {
                'form': MealForm(),
                'success_message': msg
            })
    else:
        form = MealForm()

    return render(request, 'core/meal_control.html', {'form': form})


# Adicione em core/views.py

@login_required
def guest_edit_modal(request, pk):
    """
    Abre um modal para editar os dados cadastrais do hóspede (Nome, CPF, etc).
    """
    guest = get_object_or_404(Guest, pk=pk)

    if request.method == 'POST':
        form = GuestForm(request.POST, instance=guest)
        if form.is_valid():
            form.save()
            # Retorna 204 para o HTMX atualizar a página (HX-Refresh)
            response = HttpResponse(status=204)
            response['HX-Refresh'] = "true"
            return response
    else:
        form = GuestForm(instance=guest)

    return render(request, 'core/modals/edit_guest.html', {'form': form, 'guest': guest})