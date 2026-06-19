# Atalho: Expõe a instância 'settings' direto na raiz do módulo 'core', facilitando a importação em outras partes do sistema.
from .config import settings
from app.core.auth import get_current_user, require_gestor