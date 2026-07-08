# tests/test_contatos.py

import uuid

import pytest
from app.core.config import settings
from app.modules.contatos.repository import ContatoRepository
from app.modules.contatos.schemas import (
    ContatoCreate,
    ContatoSync,
    SyncPayload,
)
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

BASE_PATH = settings.API_BASE


# Helper to build JSON payload from Pydantic model (dict())
def contato_create_payload(user_id: str) -> dict:
    return ContatoCreate(
        id=uuid.uuid4(),
        nome="Teste Usuário",
        telefone="+55 (11) 91234-5678",
        email="teste@example.com",
        tipo_numero="publico",
    ).model_dump(mode="json")


@pytest.mark.anyio
async def test_get_contatos_empty(client: AsyncClient):
    response = await client.get(f"{BASE_PATH}/contatos/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_create_contato_success(
    client: AsyncClient, db_session: AsyncSession, create_user_permission
):
    gestor_id = "admin123"
    await create_user_permission(gestor_id, role="GESTOR")
    payload = contato_create_payload(gestor_id)
    response = await client.post(
        f"{BASE_PATH}/contatos/criar-editar",
        json=payload,
        headers={"x-user-id": gestor_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == payload["nome"]
    assert data["telefone"] == payload["telefone"]
    assert data["email"] == payload["email"]
    assert data["tipo_numero"] == payload["tipo_numero"]
    # Keep the created ID for later tests
    return data["id"]


@pytest.mark.anyio
async def test_create_contato_forbidden(
    client: AsyncClient, db_session: AsyncSession, create_user_permission
):
    consultor_id = "consultor-1"
    await create_user_permission(consultor_id, role="CONSULTOR")
    payload = contato_create_payload(consultor_id)
    response = await client.post(
        f"{BASE_PATH}/contatos/criar-editar",
        json=payload,
        headers={"x-user-id": consultor_id},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Operação permitida apenas para Gestores."


@pytest.mark.anyio
async def test_delete_contato_success(
    client: AsyncClient, db_session: AsyncSession, create_user_permission
):
    gestor_id = "gestor-del"
    await create_user_permission(gestor_id, role="GESTOR")
    # Primeiro cria um contato
    payload = contato_create_payload(gestor_id)
    create_resp = await client.post(
        f"{BASE_PATH}/contatos/criar-editar",
        json=payload,
        headers={"x-user-id": gestor_id},
    )
    contato_id = create_resp.json()["id"]
    # Depois tenta deletar
    del_resp = await client.post(
        f"{BASE_PATH}/contatos/deletar",
        json={"id": contato_id},
        headers={"x-user-id": gestor_id},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Contato marcado como excluído com sucesso."
    # Verify that the contact is now marked as excluded in DB
    repo = ContatoRepository(db_session)
    contato = await repo.buscar_por_id(contato_id)
    assert contato is not None
    assert contato.excluido is True


@pytest.mark.anyio
async def test_sync_contatos(
    client: AsyncClient, db_session: AsyncSession, create_user_permission
):
    gestor_id = "gestor-sync"
    await create_user_permission(gestor_id, role="GESTOR")
    # Cria um contato inicialmente
    payload = contato_create_payload(gestor_id)
    await client.post(
        f"{BASE_PATH}/contatos/criar-editar",
        json=payload,
        headers={"x-user-id": gestor_id},
    )
    # Simula sync payload (update same contact + new one)
    existing_id = payload["id"]
    sync_contacts = [
        ContatoSync(
            id=existing_id,
            nome="Teste Alterado",
            telefone="+55 11 99876-5432",
            email="alterado@example.com",
            tipo_numero="institucional",
            atualizado_em="2023-01-01T12:00:00Z",
            excluido=False,
        ),
        ContatoSync(
            id=uuid.uuid4(),
            nome="Novo Contato",
            telefone="+55 21 91234-0000",
            email=None,
            tipo_numero="publico",
            atualizado_em="2023-01-01T12:00:00Z",
            excluido=False,
        ),
    ]
    sync_payload = SyncPayload(contatos=sync_contacts)
    resp = await client.post(
        f"{BASE_PATH}/contatos/sync",
        json=sync_payload.model_dump(mode="json"),
        headers={"x-user-id": gestor_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sucesso"] is True
    # Both IDs should be returned
    returned_ids = set(data["contatos_atualizados"])
    expected_ids = {str(existing_id), str(sync_contacts[1].id)}
    assert returned_ids == expected_ids
