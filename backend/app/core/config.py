from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""
    # O Pydantic Valida e Tipa automaticamente as variáveis de ambiente, garantindo que sejam do tipo correto e estejam presentes quando necessário.
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"  # Default to in-memory sqlite for local tests
    SECRET_KEY: str = "super-secret-key-padrao-caso-nao-exista-no-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_URL: str = "/api/auth/login"
    API_PORT: int = 8085
    # Base path used when mounting the API inside another system
    # Default kept as /lista-telefonica/api for integration with host systems
    API_BASE: str = "/lista-telefonica/api"

    # Configura o Pydantic para ler um arquivo chamado '.env' na raiz do backend
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instancia global para ser importada no resto do sistema
settings = Settings()