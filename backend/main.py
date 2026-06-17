import datetime
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import engine, get_db, Base
from models import Usuario, Contato, AuditTrail
from schemas import (
    LoginRequest, Token, ContatoResponse, ContatoCreate, ContatoSync, SyncPayload, UsuarioCreate
)
from auth import (
    get_password_hash, verify_password, create_access_token, create_refresh_token,
    get_current_user, require_gestor, SECRET_KEY, ALGORITHM
)
from jose import jwt, JWTError

# Inicializar tabelas do banco
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Aciono Você API", version="1.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite requisições de qualquer origem, ideal para dev local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_populate_db():
    db = next(get_db())
    # Criar usuários de teste padrão se não existirem
    gestor_email = "gestor@hcfmb.unesp.br"
    consultor_email = "consultor@hcfmb.unesp.br"
    
    if not db.query(Usuario).filter(Usuario.email == gestor_email).first():
        gestor = Usuario(
            email=gestor_email,
            nome="Gestor HCFMB",
            senha_hash=get_password_hash("gestor123"),
            papel="GESTOR"
        )
        db.add(gestor)
    
    if not db.query(Usuario).filter(Usuario.email == consultor_email).first():
        consultor = Usuario(
            email=consultor_email,
            nome="Consultor HCFMB",
            senha_hash=get_password_hash("consultor123"),
            papel="CONSULTOR"
        )
        db.add(consultor)
    
    # Criar alguns contatos padrão se a tabela estiver vazia
    if db.query(Contato).count() == 0:
        contatos_iniciais = [
            Contato(
                id="c1b50eb1-e283-4a11-8fa1-b65a440401b3",
                nome="Portaria Principal",
                telefone="(14) 3811-1500",
                email="portaria@hcfmb.unesp.br",
                tipo_numero="publico",
                atualizado_em=datetime.datetime.utcnow(),
                excluido=False
            ),
            Contato(
                id="f90d1f88-124b-4b13-8cfb-5a1e2f4cb1f4",
                nome="Pronto Socorro - Recepção",
                telefone="(14) 3811-1600",
                email="ps@hcfmb.unesp.br",
                tipo_numero="institucional",
                atualizado_em=datetime.datetime.utcnow(),
                excluido=False
            ),
            Contato(
                id="d56e7f88-234b-4c13-8dfb-6a2e3f4cb1f5",
                nome="Ambulatório de Especialidades",
                telefone="(14) 3811-1700",
                email="ambulatorio@hcfmb.unesp.br",
                tipo_numero="institucional",
                atualizado_em=datetime.datetime.utcnow(),
                excluido=False
            )
        ]
        db.bulk_save_objects(contatos_iniciais)
        
    db.commit()
    db.close()

# ── Rotas de Autenticação ──────────────────────────────────────────────────────

@app.post("/api/auth/login", response_model=Token)
def login(login_req: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == login_req.email).first()
    if not usuario or not verify_password(login_req.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos."
        )
    
    access_token = create_access_token(data={"sub": usuario.email, "papel": usuario.papel})
    refresh_token = create_refresh_token(data={"sub": usuario.email, "papel": usuario.papel})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "papel": usuario.papel,
        "nome": usuario.nome
    }

@app.post("/api/auth/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        is_refresh = payload.get("refresh")
        if email is None or not is_refresh:
            raise HTTPException(status_code=401, detail="Token de refresh inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token de refresh inválido ou expirado")
        
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
    new_access_token = create_access_token(data={"sub": usuario.email, "papel": usuario.papel})
    return {"access_token": new_access_token, "token_type": "bearer"}

# ── Rotas de Contatos ─────────────────────────────────────────────────────────

@app.get("/api/contatos", response_model=List[ContatoResponse])
def get_contatos(db: Session = Depends(get_db)):
    # Retorna apenas os não excluídos
    return db.query(Contato).filter(Contato.excluido == False).all()

@app.post("/api/contatos/criar-editar", response_model=ContatoResponse)
def criar_editar_contato(
    contato_in: ContatoCreate,
    usuario: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db)
):
    contato = db.query(Contato).filter(Contato.id == contato_in.id).first()
    acao = "EDITAR" if contato else "CRIAR"
    
    now = datetime.datetime.utcnow()
    
    if contato:
        contato.nome = contato_in.nome
        contato.telefone = contato_in.telefone
        contato.email = contato_in.email
        contato.tipo_numero = contato_in.tipo_numero
        contato.atualizado_em = now
        contato.excluido = False
    else:
        contato = Contato(
            id=contato_in.id,
            nome=contato_in.nome,
            telefone=contato_in.telefone,
            email=contato_in.email,
            tipo_numero=contato_in.tipo_numero,
            atualizado_em=now,
            excluido=False
        )
        db.add(contato)
        
    audit = AuditTrail(
        usuario_nome=usuario.nome,
        acao=acao,
        contato_id=contato.id,
        detalhes=f"Contato {contato.nome} ({contato.telefone}) {acao.lower()}do via painel online."
    )
    db.add(audit)
    db.commit()
    db.refresh(contato)
    return contato

@app.post("/api/contatos/deletar")
def deletar_contato(
    payload: dict,
    usuario: Usuario = Depends(require_gestor),
    db: Session = Depends(get_db)
):
    contato_id = payload.get("id")
    if not contato_id:
        raise HTTPException(status_code=400, detail="ID do contato é obrigatório.")
        
    contato = db.query(Contato).filter(Contato.id == contato_id).first()
    if not contato:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
        
    contato.excluido = True
    contato.atualizado_em = datetime.datetime.utcnow()
    
    audit = AuditTrail(
        usuario_nome=usuario.nome,
        acao="EXCLUIR",
        contato_id=contato.id,
        detalhes=f"Contato {contato.nome} excluído soft-delete."
    )
    db.add(audit)
    db.commit()
    return {"message": "Contato marcado como excluído com sucesso."}

@app.post("/api/sync")
def sync_contatos(
    payload: SyncPayload,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Endpoint inteligente de sincronização bidirecional/offline
    ids_confirmados = []
    
    for c in payload.contatos:
        # Tenta parsear data de atualização
        try:
            client_updated_at = datetime.datetime.fromisoformat(c.atualizado_em.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            client_updated_at = datetime.datetime.utcnow()
            
        contato_db = db.query(Contato).filter(Contato.id == c.id).first()
        
        if contato_db:
            # Conflito de versão: atualiza se o timestamp do cliente for mais novo
            if client_updated_at > contato_db.atualizado_em:
                contato_db.nome = c.nome
                contato_db.telefone = c.telefone
                contato_db.email = c.email
                contato_db.tipo_numero = c.tipo_numero
                contato_db.excluido = c.excluido
                contato_db.atualizado_em = client_updated_at
                
                acao = "EXCLUIR" if c.excluido else "EDITAR"
                audit = AuditTrail(
                    usuario_nome=usuario.nome,
                    acao=acao + "_SYNC",
                    contato_id=c.id,
                    detalhes=f"Sincronização offline: Contato {c.nome} atualizado (ação: {acao.lower()})."
                )
                db.add(audit)
        else:
            # Registro novo
            novo_contato = Contato(
                id=c.id,
                nome=c.nome,
                telefone=c.telefone,
                email=c.email,
                tipo_numero=c.tipo_numero,
                excluido=c.excluido,
                atualizado_em=client_updated_at
            )
            db.add(novo_contato)
            
            audit = AuditTrail(
                usuario_nome=usuario.nome,
                acao="CRIAR_SYNC",
                contato_id=c.id,
                detalhes=f"Sincronização offline: Novo contato {c.nome} inserido."
            )
            db.add(audit)
            
        ids_confirmados.append(c.id)
        
    db.commit()
    return {"sincronizados": ids_confirmados}
