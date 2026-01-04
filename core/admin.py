import json
from django.contrib import admin
from django.utils.html import format_html
from .models import Room, Bed, Guest, Reservation, Company, Meal


# ==============================================================================
# INLINES
# Permitem editar registros filhos dentro da tela do registro pai.
# ==============================================================================

class BedInline(admin.TabularInline):
    """
    Permite gerenciar as camas (A, B, etc.) diretamente dentro da tela do Quarto.
    """
    model = Bed
    extra = 0  # Começa sem exibir linhas extras vazias para manter o layout limpo.
    can_delete = True
    classes = ['collapse']  # Permite minimizar essa seção se houver muitas camas.


# ==============================================================================
# MODEL ADMINS
# Configurações das telas de listagem e edição de cada modelo.
# ==============================================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Administração de Empresas Parceiras.
    Fundamental para o filtro de 'search_fields' funcionar no autocomplete de Hóspedes.
    """
    list_display = ('name', 'cnpj', 'contact')
    search_fields = ('name', 'cnpj', 'contact')
    ordering = ('name',)
    list_per_page = 20


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """
    Gestão dos Quartos.
    Inclui a visualização das Camas (BedInline).
    """
    list_display = ('number', 'climate', 'get_beds_count', 'is_maintenance_badge')
    list_filter = ('climate', 'is_maintenance')
    search_fields = ('number',)
    inlines = [BedInline]
    ordering = ('number',)

    def get_beds_count(self, obj):
        return obj.beds.count()

    get_beds_count.short_description = 'Camas'

    def is_maintenance_badge(self, obj):
        # Cria um indicador visual (ícone) para status de manutenção
        if obj.is_maintenance:
            return format_html('<span style="color:red; font-weight:bold;">⚠️ Sim</span>')
        return format_html('<span style="color:green;">Não</span>')

    is_maintenance_badge.short_description = 'Manutenção'


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    """
    Gestão individual das Camas (caso seja necessário editar fora do quarto).
    """
    list_display = ('__str__', 'room', 'name')
    list_filter = ('room__climate',)
    search_fields = ('name', 'room__number')
    ordering = ('room', 'name')


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    """
    Cadastro de Hóspedes.
    Utiliza autocomplete_fields para selecionar a empresa, ideal se houver muitas cadastradas.
    """
    list_display = ('name', 'company', 'phone', 'cpf')
    list_filter = ('company',)
    search_fields = ('name', 'company__name', 'cpf', 'phone')
    autocomplete_fields = ['company']  # Requer que CompanyAdmin tenha search_fields configurado
    list_per_page = 25


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Controle Central de Reservas.
    Exibe status, datas e histórico de ações.
    """
    list_display = ('guest', 'get_company', 'get_room_bed', 'start_date', 'end_date', 'status_colored', 'has_luggage')
    list_filter = ('status', 'has_luggage', 'start_date', 'guest__company')
    search_fields = ('guest__name', 'guest__company__name', 'bed__room__number', 'bed__name')
    readonly_fields = ('history_formatted', 'start_date')  # Protege o histórico contra edição manual

    fieldsets = (
        ('Dados da Reserva', {
            'fields': ('guest', 'bed', 'status', 'has_luggage')
        }),
        ('Período', {
            'fields': ('start_date', 'end_date')
        }),
        ('Logs do Sistema', {
            'fields': ('history_formatted',),
            'classes': ('collapse',),  # Log vem minimizado por padrão
        }),
    )

    def get_room_bed(self, obj):
        return f"{obj.bed.room.number} - {obj.bed.name}"

    get_room_bed.short_description = 'Quarto/Cama'

    def get_company(self, obj):
        return obj.guest.company.name

    get_company.short_description = 'Empresa'
    get_company.admin_order_field = 'guest__company__name'

    def status_colored(self, obj):
        # Colore o status para fácil identificação visual
        colors = {
            'ACTIVE': 'green',
            'PRE': 'orange',
            'FINISHED': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<b style="color: {};">{}</b>', color, obj.get_status_display())

    status_colored.short_description = 'Status'

    def history_formatted(self, obj):
        # Formata o JSON para ser legível no painel administrativo
        return format_html('<pre>{}</pre>', json.dumps(obj.history, indent=4, ensure_ascii=False))

    history_formatted.short_description = 'Histórico de Atividades'


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    """
    Controle de Refeições (Almoço/Janta).
    Permite filtrar por data para gerar relatórios visuais rápidos.
    """
    list_display = ('name', 'meal_type_badge', 'company', 'created_at_formatted')
    list_filter = ('meal_type', 'created_at', 'company')
    search_fields = ('name', 'company__name', 'cpf')
    date_hierarchy = 'created_at'  # Cria uma navegação por data no topo da lista
    list_per_page = 50

    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')

    created_at_formatted.short_description = 'Data/Hora'

    def meal_type_badge(self, obj):
        icon = '☀️' if obj.meal_type == 'ALMOCO' else '🌙'
        return f"{icon} {obj.get_meal_type_display()}"

    meal_type_badge.short_description = 'Tipo'