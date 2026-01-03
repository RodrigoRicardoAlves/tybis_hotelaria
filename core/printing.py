import os
from datetime import datetime

# Tenta importar bibliotecas do Windows. Se der erro (Linux), vai para o 'except'
try:
    if os.name != 'nt':  # Verifica se o sistema operacional NÃO é Windows
        raise ImportError("Linux/Mac detectado")

    import win32ui
    import win32con


    # --- VERSÃO WINDOWS (REAL) ---
    def inicializar_impressora():
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(win32ui.GetProfileString("Windows", "device").split(",")[0])
        hDC.StartDoc('Ticket Refeicao')
        hDC.StartPage()
        return hDC


    def configurar_fonte(hDC, tamanho):
        font = win32ui.CreateFont({
            "name": "Arial",
            "height": tamanho,
            "weight": 400,
        })
        hDC.SelectObject(font)


    def finalizar_impressora(hDC):
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()


    def imprimir_ticket_refeicao(meal):
        try:
            tipo_refeicao = meal.get_meal_type_display().upper()
            hDC = inicializar_impressora()

            configurar_fonte(hDC, 80)
            hDC.TextOut(145, -10, tipo_refeicao)

            configurar_fonte(hDC, 40)
            hDC.TextOut(80, 90, f'{meal.name}')

            hDC.TextOut(80, 155, f"Data: {meal.created_at.strftime('%d/%m/%Y %H:%M')}")

            configurar_fonte(hDC, 40)
            hDC.TextOut(145, 235, 'Hotel Sol Nascente')

            line = "-" * 80
            configurar_fonte(hDC, 80)
            hDC.TextOut(0, 275, line)

            finalizar_impressora(hDC)
            return True
        except Exception as e:
            print(f"Erro na impressão Windows: {e}")
            return False

except ImportError:
    # --- VERSÃO LINUX/DEV (SIMULADA) ---
    def imprimir_ticket_refeicao(meal):
        print("\n" + "=" * 40)
        print("🖨️  [SIMULAÇÃO DE IMPRESSÃO - MODO DEV]")
        print(f"🎫 TICKET: {meal.get_meal_type_display()}")
        print(f"👤 NOME:   {meal.name}")
        print(f"🏢 EMPRESA:{meal.company.name}")
        print(f"📅 DATA:   {meal.created_at.strftime('%d/%m/%Y %H:%M')}")
        print("=" * 40 + "\n")
        return True