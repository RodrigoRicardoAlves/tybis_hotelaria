# run_waitress.py
import logging
import sys
from waitress import serve
from setup.wsgi import application

# Configura o Logging para escrever no Terminal (Console)
logging.basicConfig(
    level=logging.DEBUG,  # Mostra tudo (Debug, Info, Erro)
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

if __name__ == "__main__":
    logger = logging.getLogger("waitress")
    logger.info("🚀 Servidor Waitress iniciando em http://0.0.0.0:8000")

    try:
        # threads=4 evita travar se a impressora demorar
        serve(application, host="0.0.0.0", port=8000, threads=4)
    except Exception as e:
        logger.error(f"Erro fatal no servidor: {e}")