from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==========================================================================
    # AUTENTICAÇÃO
    # ==========================================================================
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # ==========================================================================
    # DASHBOARD & NAVEGAÇÃO PRINCIPAL
    # ==========================================================================
    path('', views.dashboard, name='dashboard'),

    # ==========================================================================
    # GESTÃO DE EMPRESAS
    # ==========================================================================
    path('empresas/', views.company_list, name='company_list'),
    path('empresas/nova/', views.company_create, name='company_create'),
    path('empresas/<int:pk>/editar/', views.company_update, name='company_update'),

    # ==========================================================================
    # OPERACIONAL - REFEIÇÕES
    # ==========================================================================
    path('refeicoes/', views.meal_control, name='meal_control'),

    # ==========================================================================
    # OPERACIONAL - RESERVAS (CRIAÇÃO)
    # ==========================================================================
    path('reserva/nova/', views.new_reservation_modal, name='new_reservation_modal'),
    path('reserva/criar/', views.create_reservation, name='create_reservation'),

    # ==========================================================================
    # RELATÓRIOS
    # ==========================================================================
    path('relatorios/ocupacao/', views.occupancy_report, name='occupancy_report'),
    path('relatorios/camas-livres/', views.free_beds_report, name='free_beds_report'),
    path('relatorios/refeicoes/', views.meal_report, name='meal_report'),
    path('relatorios/fechamento/', views.closing_report, name='closing_report'),

    # ==========================================================================
    # ENDPOINTS HTMX (AÇÕES DINÂMICAS)
    # URLs usadas internamente por botões e formulários (Ajax/HTMX)
    # ==========================================================================

    # Filtros e Buscas
    path('htmx/camas-disponiveis/', views.get_available_beds_htmx, name='htmx_available_beds'),

    # Ações na Reserva/Cama
    path('reserva/<int:pk>/mala/', views.toggle_luggage, name='toggle_luggage'),
    path('reserva/<int:pk>/checkout/', views.checkout, name='checkout'),
    path('reserva/<int:pk>/cancelar/', views.cancel_reservation, name='cancel_reservation'),

    # Edição de Hóspede
    path('hospede/<int:pk>/editar/', views.guest_edit_modal, name='guest_edit_modal'),

    # Troca de Quarto (Modal + Ação)
    path('reserva/<int:pk>/troca-modal/', views.change_room_modal, name='change_room_modal'),
    path('reserva/<int:pk>/trocar/', views.change_room, name='change_room'),

    # Confirmação de Check-in (Modal + Ação)
    path('reserva/<int:pk>/editar-checkin/', views.edit_checkin_modal, name='edit_checkin_modal'),
    path('reserva/<int:pk>/confirmar/', views.confirm_checkin, name='confirm_checkin'),

    # Manutenção de Quarto
    path('quarto/<int:pk>/manutencao/', views.toggle_maintenance, name='toggle_maintenance'),
]