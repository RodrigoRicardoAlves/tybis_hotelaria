import os
import traceback
from django.utils import timezone

# Tenta importar bibliotecas do Windows. Se der erro (Linux), vai para o 'except'
try:
    if os.name != 'nt':
        raise ImportError("Linux/Mac detectado")

    import win32ui
    import win32con
    import win32print  # Necessário para achar a impressora no Windows 10/11


    # --- VERSÃO WINDOWS (REAL) ---
    def inicializar_impressora():
        # Usa win32print para pegar a impressora padrão corretamente
        printer_name = win32print.GetDefaultPrinter()
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        hDC.StartDoc('Ticket Refeicao')
        hDC.StartPage()
        return hDC


    def finalizar_impressora(hDC):
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()


    def criar_fonte(nome="Arial", tamanho=40, peso=400):
        return win32ui.CreateFont({"name": nome, "height": tamanho, "weight": peso})


    def centralizar_texto(hDC, texto, y, page_width):
        size = hDC.GetTextExtent(texto)
        x = (page_width - size[0]) // 2
        hDC.TextOut(x, y, texto)
        return size[1]


    def imprimir_ticket_refeicao(meal):
        try:
            hDC = inicializar_impressora()

            # Layout Ajustado
            PAGE_WIDTH = 550
            MARGIN_LEFT = 20
            Y_CURSOR = 20

            # Cabeçalho
            font_header = criar_fonte("Arial", 75, 700)
            hDC.SelectObject(font_header)
            tipo_refeicao = meal.get_meal_type_display().upper()
            altura = centralizar_texto(hDC, tipo_refeicao, Y_CURSOR, PAGE_WIDTH)
            Y_CURSOR += altura + 20

            # Linha
            hDC.MoveTo(0, Y_CURSOR)
            hDC.LineTo(PAGE_WIDTH, Y_CURSOR)
            Y_CURSOR += 20

            # Dados
            font_label = criar_fonte("Arial", 30, 700)
            font_data = criar_fonte("Arial", 35, 400)

            hDC.SelectObject(font_label)
            hDC.TextOut(MARGIN_LEFT, Y_CURSOR, "HÓSPEDE:")
            Y_CURSOR += 35
            hDC.SelectObject(font_data)
            hDC.TextOut(MARGIN_LEFT + 10, Y_CURSOR, meal.name[:35])
            Y_CURSOR += 50

            hDC.SelectObject(font_label)
            hDC.TextOut(MARGIN_LEFT, Y_CURSOR, "EMPRESA:")
            Y_CURSOR += 35
            hDC.SelectObject(font_data)
            hDC.TextOut(MARGIN_LEFT + 10, Y_CURSOR, meal.company.name[:35])
            Y_CURSOR += 50

            hDC.SelectObject(font_label)
            hDC.TextOut(MARGIN_LEFT, Y_CURSOR, "DATA/HORA:")
            Y_CURSOR += 35
            hDC.SelectObject(font_data)

            # Converte UTC para o fuso horário configurado no settings.py (America/Sao_Paulo)
            data_local = timezone.localtime(meal.created_at)
            hDC.TextOut(MARGIN_LEFT + 10, Y_CURSOR, data_local.strftime('%d/%m/%Y   %H:%M'))
            Y_CURSOR += 60
            # -----------------------------

            # Rodapé
            hDC.MoveTo(0, Y_CURSOR)
            hDC.LineTo(PAGE_WIDTH, Y_CURSOR)
            Y_CURSOR += 15

            font_footer = criar_fonte("Arial", 30, 700)
            hDC.SelectObject(font_footer)
            centralizar_texto(hDC, "HOTEL SOL NASCENTE", Y_CURSOR, PAGE_WIDTH)

            finalizar_impressora(hDC)
            return True
        except Exception as e:
            print("\n" + "=" * 50)
            print("❌ ERRO CRÍTICO NA IMPRESSÃO")
            print(f"Erro resumido: {e}")
            print("-" * 20)
            print("Detalhes técnicos (Traceback):")
            traceback.print_exc()  # Isso imprime o log detalhado no console do Waitress
            print("=" * 50 + "\n")
            return False

except ImportError:
    # --- VERSÃO LINUX/DEV (SIMULADA) ---
    def imprimir_ticket_refeicao(meal):
        print("\n" + "=" * 40)
        print("🖨️  [SIMULAÇÃO DE IMPRESSÃO - MODO DEV]")
        print(f"🎫 TICKET: {meal.get_meal_type_display()}")
        print(f"👤 NOME:   {meal.name}")
        print("=" * 40 + "\n")
        return True