# core/views.py
import json
import csv
from datetime import datetime, date, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.utils import timezone
from django.db.models.functions import Cast
from django.db.models import IntegerField, Count, Q
from django.views.decorators.http import require_http_methods

# Imports locais
from .models import Room, Bed, Reservation, Guest, Company, Meal
from .forms import GuestForm, CompanyForm, MealForm
from .printing import imprimir_ticket_refeicao


# ==============================================================================
# 1. HELPERS & UTILITÁRIOS
# ==============================================================================

def _get_room_item(room):
    """
    Constrói o dicionário de dados de um quarto para exibição no Dashboard.
    """
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
        status_code = 'MAINTENANCE'
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
        'status_code': status_code
    }


def get_available_beds_query(company_id=None):
    """
    Retorna camas disponíveis, respeitando a regra de empresas diferentes.
    """
    available_beds = Bed.objects.filter(room__is_maintenance=False).exclude(
        reservations__status__in=['ACTIVE', 'PRE']
    )

    if not company_id:
        return available_beds

    valid_bed_ids = []
    target_company_id = int(company_id)

    for bed in available_beds:
        roommates = Reservation.objects.filter(
            bed__room=bed.room,
            status__in=['ACTIVE', 'PRE']
        )

        can_enter = True
        for roommate in roommates:
            if roommate.guest.company.id != target_company_id:
                can_enter = False
                break

        if can_enter:
            valid_bed_ids.append(bed.id)

    return available_beds.filter(id__in=valid_bed_ids)


# ==============================================================================
# 2. DASHBOARD
# ==============================================================================

@login_required
def dashboard(request):
    rooms = Room.objects.annotate(
        numero_ordenado=Cast('number', IntegerField())
    ).order_by('numero_ordenado')

    full_data = [_get_room_item(room) for room in rooms]

    # Contagem para os botões de filtro
    counts = {
        'total': len(full_data),
        'free': 0,
        'occupied': 0,
        'pre': 0,
        'maintenance': 0
    }

    for item in full_data:
        code = item['status_code']
        if code == 'FREE':
            counts['free'] += 1
        elif code == 'OCCUPIED':
            counts['occupied'] += 1
        elif code == 'PRE':
            counts['pre'] += 1
        elif code == 'MAINTENANCE':
            counts['maintenance'] += 1

    # Filtro
    filter_type = request.GET.get('filter')
    if filter_type and filter_type != 'ALL':
        dashboard_data = [item for item in full_data if item['status_code'] == filter_type]
    else:
        dashboard_data = full_data

    if request.htmx:
        return render(request, 'core/partials/dashboard_grid.html', {'dashboard_data': dashboard_data})

    return render(request, 'core/dashboard.html', {
        'dashboard_data': dashboard_data,
        'current_filter': filter_type,
        'counts': counts
    })


# ==============================================================================
# 3. RESERVAS E CHECK-IN
# ==============================================================================

@login_required
def new_reservation_modal(request):
    form = GuestForm()
    beds = get_available_beds_query(None)
    return render(request, 'core/modals/new_reservation.html', {'form': form, 'beds': beds})


@login_required
def get_available_beds_htmx(request):
    company_id = request.GET.get('company')
    beds = get_available_beds_query(company_id)
    return render(request, 'core/partials/bed_options.html', {'beds': beds})


@login_required
def create_reservation(request):
    if request.method == 'POST':
        form = GuestForm(request.POST)
        bed_id = request.POST.get('bed_id')
        is_pre = request.POST.get('is_pre') == 'on'

        if not bed_id:
            form.add_error(None, "Selecione um quarto/cama.")

        if form.is_valid() and bed_id:
            guest_company = form.cleaned_data['company']
            allowed_beds = get_available_beds_query(guest_company.id)

            if not allowed_beds.filter(id=bed_id).exists():
                form.add_error(None, "Cama indisponível ou conflito de empresa.")
            else:
                guest = form.save()
                bed = get_object_or_404(Bed, pk=bed_id)
                status = 'PRE' if is_pre else 'ACTIVE'
                res = Reservation.objects.create(guest=guest, bed=bed, status=status)
                res.add_log(request.user, "Reserva Criada", f"Quarto {bed.room.number}")

                response = HttpResponse(status=204)
                response['HX-Refresh'] = "true"
                return response

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
def checkout(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    res.status = 'FINISHED'
    res.end_date = timezone.now()
    res.add_log(request.user, "Checkout Realizado")
    res.save()
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


@login_required
def toggle_luggage(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    res.has_luggage = not res.has_luggage
    res.add_log(request.user, "Mala: " + str(res.has_luggage))
    res.save()
    return render(request, 'core/partials/bed_card.html', {'bed': res.bed, 'res': res})


@login_required
def change_room_modal(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    beds = get_available_beds_query(res.guest.company.id)
    return render(request, 'core/modals/change_room.html', {'res': res, 'beds': beds})


@login_required
def change_room(request, pk):
    res = get_object_or_404(Reservation, pk=pk)
    new_bed_id = request.POST.get('new_bed_id')
    if new_bed_id:
        new_bed = get_object_or_404(Bed, pk=new_bed_id)
        res.add_log(request.user, "Mudança de Quarto", f"Para {new_bed}")
        res.bed = new_bed
        res.save()
        response = HttpResponse(status=204)
        response['HX-Refresh'] = "true"
        return response
    return HttpResponse("Erro", status=400)


@login_required
def toggle_maintenance(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if not room.is_maintenance:
        if Reservation.objects.filter(bed__room=room, status__in=['ACTIVE', 'PRE']).exists():
            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({"showAlert": "Quarto Ocupado!"})
            return response
    room.is_maintenance = not room.is_maintenance
    room.save()
    response = HttpResponse(status=204)
    response['HX-Refresh'] = "true"
    return response


@login_required
def guest_edit_modal(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    if request.method == 'POST':
        form = GuestForm(request.POST, instance=guest)
        if form.is_valid():
            form.save()
            response = HttpResponse(status=204)
            response['HX-Refresh'] = "true"
            return response
    else:
        form = GuestForm(instance=guest)
    return render(request, 'core/modals/edit_guest.html', {'form': form, 'guest': guest})


# ==============================================================================
# 4. GESTÃO DE EMPRESAS
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
# 5. REFEIÇÕES
# ==============================================================================

@login_required
def meal_control(request):
    if request.method == 'POST':
        form = MealForm(request.POST)
        if form.is_valid():
            meal = form.save()
            imprimiu = imprimir_ticket_refeicao(meal)
            msg = f"Refeição de {meal.name} salva!" + (" (Impressão OK)" if imprimiu else " (Erro Impressão)")
            return render(request, 'core/partials/meal_form_content.html', {'form': MealForm(), 'success_message': msg})
    else:
        form = MealForm()
    return render(request, 'core/meal_control.html', {'form': form})


# ==============================================================================
# 6. RELATÓRIOS
# ==============================================================================

@login_required
def occupancy_report(request):
    """ Relatório 1: Ocupação por Empresa """
    reservations = Reservation.objects.filter(status='ACTIVE')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        reservations = reservations.filter(start_date__date__gte=start_date)
    if end_date:
        reservations = reservations.filter(start_date__date__lte=end_date)

    report_data = reservations.values('guest__company__name') \
        .annotate(total=Count('id')).order_by('-total')

    return render(request, 'core/reports/occupancy.html', {
        'report_data': report_data,
        'total_guests': reservations.count(),
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def free_beds_report(request):
    """ Relatório 2: Vagas em Quartos Ocupados (Otimização) """
    companies = Company.objects.all()
    report_data = []

    for company in companies:
        occupied_rooms = Room.objects.filter(
            beds__reservations__guest__company=company,
            beds__reservations__status='ACTIVE'
        ).distinct().prefetch_related('beds')

        available_slots = []
        for room in occupied_rooms:
            empty_beds = room.beds.exclude(reservations__status__in=['ACTIVE', 'PRE'])
            if empty_beds.exists():
                available_slots.append({'room': room, 'beds': list(empty_beds)})

        if available_slots:
            total_free = sum(len(item['beds']) for item in available_slots)
            report_data.append({
                'company': company,
                'slots': available_slots,
                'total_free': total_free
            })

    return render(request, 'core/reports/free_beds.html', {'report_data': report_data})


@login_required
def meal_report(request):
    """ Relatório 3: Histórico de Refeições com CSV """
    meals = Meal.objects.all().select_related('company').order_by('-created_at')
    companies = Company.objects.all()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    company_id = request.GET.get('company')

    if start_date: meals = meals.filter(created_at__date__gte=start_date)
    if end_date: meals = meals.filter(created_at__date__lte=end_date)
    if company_id: meals = meals.filter(company_id=company_id)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="refeicoes.csv"'
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Data', 'Hora', 'Tipo', 'Nome', 'Empresa', 'CPF'])
        for meal in meals:
            local_dt = timezone.localtime(meal.created_at)
            writer.writerow([
                local_dt.strftime('%d/%m/%Y'),
                local_dt.strftime('%H:%M'),
                meal.get_meal_type_display(),
                meal.name.upper(),
                meal.company.name.upper(),
                meal.cpf or ''
            ])
        return response

    return render(request, 'core/reports/meal_report.html', {
        'meals': meals, 'companies': companies,
        'start_date': start_date, 'end_date': end_date,
        'selected_company': int(company_id) if company_id else None,
        'total_meals': meals.count()
    })


@login_required
@user_passes_test(lambda u: u.is_staff)  # <--- SEGURANÇA: Só Admin
def closing_report(request):
    """ Relatório 4: Fechamento (Fatura) - Financeiro """
    companies = Company.objects.all()
    start_str = request.GET.get('start_date')
    end_str = request.GET.get('end_date')
    company_id = request.GET.get('company')
    is_export = request.GET.get('export') == 'csv'
    report_data = []

    if start_str and end_str:
        filter_start = datetime.strptime(start_str, '%Y-%m-%d').date()
        filter_end = datetime.strptime(end_str, '%Y-%m-%d').date()

        reservations = Reservation.objects.filter(
            start_date__date__lte=filter_end
        ).filter(
            Q(end_date__date__gte=filter_start) | Q(end_date__isnull=True)
        ).select_related('guest', 'guest__company')

        if company_id:
            reservations = reservations.filter(guest__company_id=company_id)

        for res in reservations:
            # Fuso Horário e Datas Efetivas
            local_start_dt = timezone.localtime(res.start_date)
            res_start = local_start_dt.date()
            res_end = timezone.localtime(res.end_date).date() if res.end_date else filter_end

            if res_start > filter_end or res_end < filter_start:
                continue

            effective_start = max(res_start, filter_start)
            effective_end = min(res_end, filter_end)

            days = (effective_end - effective_start).days + 1
            if days < 0: days = 0

            # Refeições
            lunch_count = 0
            dinner_count = 0
            if res.guest.cpf:
                all_meals = Meal.objects.filter(cpf=res.guest.cpf)
                for meal in all_meals:
                    meal_date = timezone.localtime(meal.created_at).date()
                    if effective_start <= meal_date <= effective_end:
                        if meal.meal_type == 'ALMOCO':
                            lunch_count += 1
                        elif meal.meal_type == 'JANTA':
                            dinner_count += 1

            if days > 0 or lunch_count > 0 or dinner_count > 0:
                report_data.append({
                    'cpf': res.guest.cpf,
                    'name': res.guest.name.upper(),
                    'company': res.guest.company.name.upper(),
                    'days': days,
                    'lunch': lunch_count,
                    'dinner': dinner_count,
                    'entry': effective_start,
                    'exit': effective_end,
                    'is_active': res.end_date is None
                })

    if is_export and report_data:
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="fatura.csv"'
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['CPF', 'NOME', 'EMPRESA', 'DIARIAS', 'ALMOCO', 'JANTAR', 'ENTRADA', 'SAIDA'])
        for item in report_data:
            writer.writerow([
                item['cpf'] or '',
                item['name'],
                item['company'],
                item['days'],
                item['lunch'],
                item['dinner'],
                item['entry'].strftime('%d/%m/%Y'),
                item['exit'].strftime('%d/%m/%Y')
            ])
        return response

    return render(request, 'core/reports/closing_report.html', {
        'companies': companies,
        'report_data': report_data,
        'start_date': start_str,
        'end_date': end_str,
        'selected_company': int(company_id) if company_id else None
    })