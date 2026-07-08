import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.auth import UsuarioAutenticado, get_current_user
from app.modules.contatos.router import router as contatos_router
from fastapi import APIRouter, FastAPI, Depends, Header
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import init_db

    try:
        await init_db.inicializar_banco()
    except Exception:
        logging.exception(
            "init_db.inicializar_banco() failed during startup; continuing without initializing database"
        )

    yield  # Continua com a execução da aplicação


app = FastAPI(title="Aciono Você API", version="1.0.0", lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Em produção, você deve especificar os domínios permitidos para maior segurança
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the contatos router under the RESTful base path
app.include_router(contatos_router, prefix=f"{settings.API_BASE}/contatos", tags=["Contatos"])

# Root endpoint showing API base information
@app.get("/")
async def read_root():
    return {
        "message": "Aciono Você API",
        "api_base": "/lista-telefonica",
        "docs": "/lista-telefonica/docs",
        "usuarios_teste": [
            {"id": "admin123", "papel": "GESTOR", "descricao": "Usuário com acesso total (criar, editar, deletar)"},
            {"id": "consultor456", "papel": "CONSULTOR", "descricao": "Usuário com acesso apenas leitura"}
        ]
    }

# Endpoint de teste de autenticação
@app.get("/teste-usuario", tags=["Teste"])
async def test_usuario(
    usuario: UsuarioAutenticado = Depends(get_current_user)
):
    """
    Endpoint de teste para verificar autenticação e obter informações do usuário.
    
    **Como usar no Swagger:**
    
    1. Clique no botão "Authorize" (ícone de cadeado) no topo da página Swagger
    2. Adicione o header `x-user-id` com um dos valores:
       - `admin123` (GESTOR - acesso total)
       - `consultor456` (CONSULTOR - apenas leitura)
    3. Clique em "Authorize" para salvar
    4. Agora você pode chamar este endpoint e outros que requerem autenticação
    """
    return {
        "usuario_id_externo": usuario.usuario_id_externo,
        "papel": usuario.papel,
        "mensagem": "✅ Autenticação bem-sucedida! Este usuário pode acessar os endpoints protegidos."
    }

# Endpoint informativo (sem autenticação necessária)
@app.get("/usuarios-teste", tags=["Teste"])
async def usuarios_teste():
    """
    Lista os usuários mock disponíveis para testes.
    
    Use um desses IDs no header `x-user-id` para testar os endpoints.
    """
    return {
        "usuarios_disponíveis": [
            {
                "id": "admin123",
                "papel": "GESTOR",
                "descricao": "Usuário com acesso total (criar, editar, deletar contatos)",
                "permissoes": ["GET", "POST", "PUT", "DELETE", "SYNC"]
            },
            {
                "id": "consultor456",
                "papel": "CONSULTOR",
                "descricao": "Usuário com acesso apenas leitura",
                "permissoes": ["GET", "SYNC"]
            },
            {
                "id": "outro_usuario",
                "papel": "CONSULTOR",
                "descricao": "Qualquer outro ID é tratado como CONSULTOR",
                "permissoes": ["GET", "SYNC"]
            }
        ],
        "instrucoes": "Copie um dos IDs acima e use como valor do header 'x-user-id' nas suas requisições"
    }
