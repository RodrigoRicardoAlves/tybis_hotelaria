from django.contrib import admin
from .models import Room, Bed, Guest, Reservation, Company


# Configuração para editar camas DENTRO da tela do quarto
class BedInline(admin.TabularInline):
    model = Bed
    extra = 1  # Deixa 1 espaço em branco para adicionar nova cama


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('number', 'climate', 'get_beds_count', 'is_maintenance')
    list_filter = ('climate', 'is_maintenance')
    search_fields = ('number',)
    inlines = [BedInline]

    def get_beds_count(self, obj):
        return obj.beds.count()

    get_beds_count.short_description = 'Qtd. Camas'


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('name', 'room')
    list_filter = ('room__climate',)
    search_fields = ('name', 'room__number')
    ordering = ('room', 'name')


# --- NOVO: ADMIN DE EMPRESAS ---
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'cnpj', 'contact')
    search_fields = ('name', 'cnpj', 'contact')
    ordering = ('name',)


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'phone', 'cpf')
    list_filter = ('company',)
    # Agora busca também pelo nome da empresa
    search_fields = ('name', 'company__name', 'cpf', 'phone')
    # Adiciona um campo de busca para selecionar a empresa (útil se tiver muitas)
    autocomplete_fields = ['company']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    # Adicionei 'get_company' na lista
    list_display = ('guest', 'get_company', 'get_room_bed', 'start_date', 'end_date', 'status', 'has_luggage')
    list_filter = ('status', 'has_luggage', 'start_date', 'guest__company')
    search_fields = ('guest__name', 'guest__company__name', 'bed__room__number', 'bed__name')
    readonly_fields = ('history_formatted', 'start_date')

    def history_formatted(self, obj):
        import json
        return json.dumps(obj.history, indent=4, ensure_ascii=False)

    history_formatted.short_description = 'Histórico de Atividades'

    def get_room_bed(self, obj):
        return f"{obj.bed.room.number} - {obj.bed.name}"

    get_room_bed.short_description = 'Quarto/Cama'

    # Nova função para mostrar a empresa na tabela de reservas
    def get_company(self, obj):
        return obj.guest.company.name

    get_company.short_description = 'Empresa'
    get_company.admin_order_field = 'guest__company__name'  # Permite ordenar pela coluna