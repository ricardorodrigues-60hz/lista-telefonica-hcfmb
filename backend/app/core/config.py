from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings."""
    # O Pydantic Valida e Tipa automaticamente as variáveis de ambiente, garantindo que sejam do tipo correto e estejam presentes quando necessário.
    DATABASE_URL: str  # A URL de conexão com o banco de dados, que deve ser fornecida via variável de ambiente
    SECRET_KEY: str = "super-secret-key-padrao-caso-nao-exista-no-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Configura o Pydantic para ler um arquivo chamado '.env' na raiz do backend
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instancia global para ser importada no resto do sistema
settings = Settings()