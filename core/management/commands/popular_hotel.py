from django.core.management.base import BaseCommand
from core.models import Room, Bed, Company


class Command(BaseCommand):
    help = 'Popula o banco de dados com 96 quartos (Ventilador) e 2 camas cada'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando processo de população...'))

        Company.objects.get_or_create(name="Particular")
        self.stdout.write('Empresa "Particular" garantida.')

        total_criados = 0
        total_existentes = 0

        # Loop de 1 até 96
        for i in range(1, 97):
            # Formata o número para string (ex: "1", "2"... "96")
            # Se quiser padronizar com zero à esquerda (ex: "01"), use: f"{i:02d}"
            numero_quarto = str(i)

            # Tenta pegar o quarto, se não existir, cria
            room, created = Room.objects.get_or_create(
                number=numero_quarto,
                defaults={
                    'climate': 'VENT',  # Todos com Ventilador
                    'is_maintenance': False
                }
            )

            if created:
                # Se o quarto acabou de ser criado, cria as duas camas
                Bed.objects.create(room=room, name='A')
                Bed.objects.create(room=room, name='B')
                total_criados += 1
                self.stdout.write(f'Quarto {numero_quarto} criado com camas A e B.')
            else:
                # Se já existe, verificamos se tem camas, se não tiver, cria
                if not room.beds.exists():
                    Bed.objects.create(room=room, name='A')
                    Bed.objects.create(room=room, name='B')
                    self.stdout.write(f'Quarto {numero_quarto} já existia, camas adicionadas.')

                total_existentes += 1

        self.stdout.write(self.style.SUCCESS('----------------------------------'))
        self.stdout.write(self.style.SUCCESS(f'Processo Finalizado!'))
        self.stdout.write(self.style.SUCCESS(f'Novos quartos criados: {total_criados}'))
        self.stdout.write(self.style.WARNING(f'Quartos já existentes: {total_existentes}'))