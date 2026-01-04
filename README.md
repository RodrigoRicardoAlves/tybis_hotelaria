# 🏨 Tybis Hotelaria - Gestão de Longa Estadia

Sistema de gestão hoteleira focado em **estadias de longa duração** (Long Stay), ideal para hotéis que trabalham com convênios corporativos e alojamento de funcionários.

> 🤖 **Desenvolvimento Assistido por IA:** Este projeto foi desenvolvido inteiramente através da colaboração entre **Rodrigo Ricardo Alves** (Operador e Arquiteto de Regras de Negócio) e a **IA Gemini do Google** (Codificação e Implementação).

---

## 🚀 Sobre o Projeto

O objetivo do Tybis Hotelaria é resolver a complexidade de alocar funcionários de diferentes empresas em quartos compartilhados, garantindo a segurança e a organização logística.

Diferente de hotéis turísticos tradicionais, este sistema foca em:
* **Controle por Leito (Cama):** Gestão individual de camas dentro de um mesmo quarto.
* **Regras de Convivência:** O sistema **impede automaticamente** que hóspedes de empresas diferentes sejam alocados no mesmo quarto.
* **Gestão de Refeições:** Emissão e controle de tickets de alimentação (Almoço/Janta) com integração para impressoras térmicas.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3 + Django
* **Frontend:** Bootstrap 5 (Responsivo) + **HTMX** (Para interações dinâmicas sem recarregar a página)
* **Banco de Dados:** SQLite (Padrão Django)
* **Impressão:** Integração Win32 (GDI) para Windows e Simulação Mock para Linux.

## ✨ Funcionalidades Principais

1.  **Mapa de Ocupação (Dashboard):**
    * Visualização rápida de todos os quartos e status (Livre, Ocupado, Pré-reserva, Manutenção).
    * Indicadores visuais de climatização (Ar Condicionado vs Ventilador).

2.  **Gestão de Reservas:**
    * Fluxo de Pré-reserva -> Check-in -> Checkout.
    * Histórico detalhado de ações (logs de quem fez o que e quando).
    * Controle de "Mala Guardada" para hóspedes ausentes temporariamente.

3.  **Controle de Empresas:**
    * Cadastro de empresas parceiras.
    * Validação automática de conflitos de alocação.

4.  **Refeitório:**
    * Módulo específico para controle de Almoço e Janta.
    * Impressão direta de tickets (compatível com impressoras térmicas como Bematech/Elgin em ambiente Windows).

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
    pip install django django-htmx widget-tweaks
    # Se estiver no Windows e quiser imprimir:
    pip install pywin32
    ```

4.  **Prepare o Banco de Dados:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Popule o Hotel (Comando Automático):**
    Este comando cria automaticamente 96 quartos com 2 camas cada e a empresa padrão "Particular".
    ```bash
    python manage.py popular_hotel
    ```

6.  **Crie um superusuário (para acessar o Admin):**
    ```bash
    python manage.py createsuperuser
    ```

7.  **Inicie o Servidor:**
    ```bash
    python manage.py runserver
    ```

Acesse em: `http://127.0.0.1:8000/`

## 🤝 Créditos e Autoria

* **Idealização e Supervisão:** Rodrigo Ricardo Alves
* **Desenvolvimento de Código:** Gemini (Google AI)

Este projeto demonstra como a Inteligência Artificial pode atuar como um parceiro técnico eficaz (Pair Programmer), transformando requisitos de negócio em código funcional e bem estruturado.

---
📝 *Licença MIT - Uso livre para fins educacionais e comerciais.*