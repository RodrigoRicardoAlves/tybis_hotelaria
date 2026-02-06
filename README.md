# 🏨 Tybis Hotelaria - Gestão de Longa Estadia

Sistema de gestão hoteleira focado em **estadias de longa duração** (Long Stay), ideal para hotéis que trabalham com convênios corporativos e alojamento de funcionários.

> 🤖 **Desenvolvimento Assistido por IA:** Este projeto foi desenvolvido inteiramente através da colaboração entre **Rodrigo Ricardo Alves** (Operador e Arquiteto de Regras de Negócio) e a **IA Gemini do Google** (Codificação e Implementação).

---

## 🚀 Sobre o Projeto

O objetivo do Tybis Hotelaria é resolver a complexidade de alocar funcionários de diferentes empresas em quartos compartilhados, garantindo a segurança, organização logística e faturamento preciso.

Diferente de hotéis turísticos tradicionais, este sistema foca em:
* **Controle por Leito (Cama):** Gestão individual de camas dentro de um mesmo quarto.
* **Regras de Convivência:** O sistema **impede automaticamente** que hóspedes de empresas diferentes sejam alocados no mesmo quarto.
* **Otimização de Custos:** Relatórios inteligentes para preencher quartos parcialmente ocupados antes de abrir novos.
* **Gestão de Refeições:** Emissão e controle de tickets (Almoço/Janta) com impressão térmica.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3 + Django 6.0
* **Frontend:** Bootstrap 5 (Responsivo) + **HTMX** (Interatividade sem recarregar a página)
* **Banco de Dados:** SQLite (Padrão Django)
* **Servidor de Produção:** Waitress (WSGI)
* **Impressão:** Integração nativa Win32 (GDI) para Windows e Simulação Mock para Linux.

## ✨ Funcionalidades Principais

### 1. 🗺️ Dashboard Interativo
* **Mapa em Tempo Real:** Visualização de todos os quartos com indicadores de climatização (Ar/Ventilador).
* **Filtros Dinâmicos (HTMX):** Alterne instantaneamente entre quartos Livres, Ocupados, Pré-reserva e Manutenção com contadores atualizados.

### 2. 🛎️ Gestão de Reservas
* **Fluxo Completo:** Pré-reserva -> Check-in -> Checkout.
* **Edição Rápida:** Modais para editar dados do hóspede, trocar de quarto e confirmar check-in.
* **Controle de Malas:** Indicador visual para hóspedes que deixaram pertences no hotel (Mala Guardada).
* **Segurança:** Impede alocação de empresas diferentes no mesmo quarto.

### 3. 📊 Relatórios Gerenciais e Financeiros
* **Ocupação Atual:** Quem está no hotel agora, agrupado por empresa.
* **Camas Livres (Otimização):** Identifica vagas em quartos já ocupados para otimizar a alocação.
* **Histórico de Refeições:** Listagem completa de tickets emitidos com filtros por data e empresa.
* **Fechamento (Fatura):** Relatório financeiro avançado (Restrito a Admin) com:
    * Cálculo de diárias inclusivas (considerando entrada e saída).
    * Recorte preciso por período de faturamento.
    * **Exportação para Excel (CSV):** Dados formatados e prontos para contabilidade.

### 4. 🍽️ Refeitório
* Impressão direta de tickets de Almoço e Janta.
* Correção automática de fuso horário na impressão.
* Associação automática ao CPF do hóspede.

## ⚙️ Instalação e Configuração

Siga os passos abaixo para rodar o projeto localmente:

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/tybis-hotelaria.git](https://github.com/seu-usuario/tybis-hotelaria.git)
    cd tybis-hotelaria
    ```

2.  **Crie um ambiente virtual e ative:**
    ```bash
    python -m venv venv
    # No Windows:
    venv\Scripts\activate
    # No Linux/Mac:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepare o Banco de Dados:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Popule o Hotel (Comando Automático):**
    Este comando cria a estrutura inicial com 96 quartos (2 camas cada).
    ```bash
    python manage.py popular_hotel
    ```

6.  **Crie um Administrador:**
    Necessário para acessar o relatório financeiro e o painel admin.
    ```bash
    python manage.py createsuperuser
    ```

7.  **Inicie o Servidor:**
    * **Modo Desenvolvimento:**
        ```bash
        python manage.py runserver
        ```
    * **Modo Produção (Windows/Waitress):**
        ```bash
        python run_waitress.py
        ```

Acesse em: `http://127.0.0.1:8000/`

## 🤝 Créditos e Autoria

* **Idealização e Regras de Negócio:** Rodrigo Ricardo Alves
* **Desenvolvimento de Código:** Gemini (Google AI)

Este projeto demonstra o poder do desenvolvimento assistido por IA ("Pair Programming"), transformando requisitos complexos de negócio em um software funcional, seguro e escalável.

---
📝 *Licença MIT - Uso livre para fins educacionais e comerciais.*