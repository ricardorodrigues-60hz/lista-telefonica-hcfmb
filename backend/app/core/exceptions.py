"""Exceções de domínio da aplicação e seus handlers HTTP.

Services (ex.: ``AuthService``) devem preferir levantar essas exceções em vez
de ``HTTPException`` diretamente, mantendo a camada HTTP (routers) livre de
regras de negócio. Os handlers abaixo traduzem cada exceção para a resposta
HTTP apropriada e são registrados em ``app.main``.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base para todas as exceções de domínio da aplicação."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Erro inesperado."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


class CredenciaisInvalidasError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "E-mail ou senha inválidos."


class TokenInvalidoError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Refresh token inválido, revogado ou expirado."


class NaoAutenticadoError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Could not validate credentials"


class PermissaoNegadaError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Operação não permitida para o seu papel."


class RegistroNaoEncontradoError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Registro não encontrado."


class RegraDeNegocioError(AppError):
    """Violação de uma regra de negócio (ex.: e-mail duplicado)."""

    status_code = status.HTTP_400_BAD_REQUEST


def register_exception_handlers(app: FastAPI) -> None:
    """Registra os handlers que convertem ``AppError`` em respostas HTTP."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == status.HTTP_401_UNAUTHORIZED else None
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)
