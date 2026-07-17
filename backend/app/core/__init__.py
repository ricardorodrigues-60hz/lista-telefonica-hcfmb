# Atalho: Expõe a instância 'settings' direto na raiz do módulo 'core', facilitando a importação em outras partes do sistema.
from .config import settings

__all__ = ["settings"]
