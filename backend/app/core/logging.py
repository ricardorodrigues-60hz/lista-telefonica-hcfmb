"""Configuração centralizada de logging da aplicação."""

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configura o logging raiz da aplicação (idempotente)."""
    root = logging.getLogger()
    if root.handlers:
        # Já configurado (ex.: recarregado pelo --reload do uvicorn); evita handlers duplicados.
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)
