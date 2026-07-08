'use client';

/**
 * ============================================================================
 * ACIONO VOCÊ - FRONTEND DO SUBMÓDULO DE RAMAIS (HCFMB)
 * ============================================================================
 * 
 * Este arquivo contém a interface principal e a lógica do cliente para o
 * submódulo de Lista Telefônica / Ramais.
 * 
 * Arquitetura e Fluxo Chave para Desenvolvedores Futuros:
 * 
 * 1. INTEGRAÇÃO INTRANET / SEM TELA DE LOGIN:
 *    - O sistema não gerencia login ou senhas localmente. Ele roda embutido como
 *      sub-app (ex: em um iframe ou widget) na intranet do hospital.
 *    - O ID do usuário ativo deve vir via query parameters na URL (ex: `?user_id=nomeUser`)
 *      ou ser persistido no `localStorage` como `x-user-id`.
 *    - O cabeçalho HTTP `x-user-id` é enviado em todas as requisições para o backend.
 * 
 * 2. CONTROLE DE ACESSO (UI GUARD):
 *    - `admin123` é mapeado no banco como 'GESTOR' (permissão de escrita/modificação).
 *    - Qualquer outro ID de usuário é tratado como 'CONSULTOR' (apenas leitura).
 *    - Botões de Adicionar, Editar e Excluir são renderizados condicionalmente
 *      com base no estado `userRole` (`userRole === 'GESTOR'`).
 * 
 * 3. OFFLINE-FIRST E ARMAZENAMENTO LOCAL (Dexie.js):
 *    - Todos os contatos ativos são cacheados e consultados localmente no IndexedDB
 *      usando o Dexie.js (`db.contatos`).
 *    - Alterações realizadas offline são marcadas como `sincronizado = false`
 *      e enviadas em lote na próxima sincronização ativa (função `triggerSync`).
 * 
 * 4. ESCOPO DO SERVICE WORKER (PWA):
 *    - O Service Worker (`sw.js`) é registrado manualmente especificando o escopo
 *      exclusivo do subdiretório: `/lista-telefonica/`.
 */

import React, { useState, useEffect } from 'react';
import { useLiveQuery } from 'dexie-react-hooks';
import {
  Phone, Mail, Search, Plus, Edit2, Trash2, Cloud, CloudOff,
  RefreshCw, Info, Wifi, WifiOff, X, User
} from 'lucide-react';
import { db, type LocalContato } from '../db/db';

// Prefixo base do sub-app para as rotas da API no monólito/proxy
const API_BASE = '/lista-telefonica';

export default function Home() {
  // TODO: Capturar token JWT real do sistema hospitalar pai (localStorage, cookies ou contexto)
  const getAuthToken = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('jwt_token') || 'mock_jwt_token_temporario';
    }
    return 'mock_jwt_token_temporario';
  };

  // ==========================================
  // ESTADOS DA APLICAÇÃO
  // ==========================================

  // Identificação do usuário logado na intranet principal
  const [userId, setUserId] = useState<string>('admin123');

  // Nível de acesso do usuário corrente resolvido a partir do ID
  const [userRole, setUserRole] = useState<'GESTOR' | 'CONSULTOR'>('GESTOR');

  // Estados de conectividade de rede e sincronização em lote
  const [isOnline, setIsOnline] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'warning' | 'error', text: string } | null>(null);

  // Filtros de busca digitada e categorias (institucional/público)
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'todos' | 'institucional' | 'publico'>('todos');

  // Controle de estado e campos do formulário/modal (criação e edição de ramais)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingContactId, setEditingContactId] = useState<string | null>(null);
  const [formNome, setFormNome] = useState('');
  const [formTelefone, setFormTelefone] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formTipo, setFormTipo] = useState<'institucional' | 'publico'>('publico');

  // ==========================================
  // QUERIES DE BANCO LOCAL (Dexie.js / Live Queries)
  // ==========================================

  // Obtém todos os contatos ativos locais que não foram marcados para exclusão lógica
  const localContacts = useLiveQuery(
    () => db.contatos.filter(c => !c.excluido).toArray()
  ) || [];

  // Contador de registros modificados localmente que precisam de sincronização com o servidor
  const pendingSyncCount = useLiveQuery(
    () => db.contatos.filter(c => !c.sincronizado).count()
  ) || 0;

  // ==========================================
  // EFEITOS DE INICIALIZAÇÃO E EVENTOS
  // ==========================================

  useEffect(() => {
    if (typeof window !== 'undefined') {
      // 1. Registro Manual do Service Worker com escopo delimitado
      // Impede que o SW intermedeie rotas fora do subdiretório da lista telefônica
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/lista-telefonica/sw.js', { scope: '/lista-telefonica/' })
          .then(reg => console.log('Service Worker registrado com escopo:', reg.scope))
          .catch(err => console.error('Falha ao registrar Service Worker:', err));
      }

      // 2. Resolução da Identidade do Usuário
      // Lê o parâmetro de query '?user_id=' ou busca o cache existente no localStorage
      const params = new URLSearchParams(window.location.search);
      const queryUser = params.get('user_id');
      const activeUser = queryUser || localStorage.getItem('x-user-id') || 'admin123';

      setUserId(activeUser);
      localStorage.setItem('x-user-id', activeUser);

      // Regra de Permissão no Frontend:
      // O ID 'admin123' é mapeado como GESTOR de ramais. Demais IDs recebem visualização CONSULTOR (apenas leitura).
      const role = activeUser === 'admin123' ? 'GESTOR' : 'CONSULTOR';
      setUserRole(role);

      // 3. Gerenciamento do Status de Conexão (Online/Offline)
      setIsOnline(navigator.onLine);

      const handleOnline = () => {
        setIsOnline(true);
        triggerSync(); // Sincroniza dados locais assim que restabelecer conexão
      };
      const handleOffline = () => setIsOnline(false);

      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);

      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }
  }, []);

  // Recarrega lista do servidor central sempre que o usuário ativo mudar ou reconectar
  useEffect(() => {
    if (isOnline && userId) {
      loadContactsFromServer();
    }
  }, [userId, isOnline]);

  // ==========================================
  // COMUNICAÇÃO COM A API E SINCRONIZAÇÃO
  // ==========================================

  /**
   * Puxa os dados atualizados do banco central e atualiza o IndexedDB local.
   * Preserva alterações locais ainda não sincronizadas antes de recriar o cache local.
   */
  const loadContactsFromServer = async () => {
    try {
      const res = await fetch(`${API_BASE}/contatos`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'x-user-id': userId
        }
      });

      if (res.ok) {
        const data = await res.json();

        // Operação atômica em transação de escrita para evitar concorrência
        await db.transaction('rw', db.contatos, async () => {
          // Salva dados locais modificados offline para não sobresscrevê-los
          const unsynced = await db.contatos.filter(c => !c.sincronizado).toArray();
          await db.contatos.clear();

          // Reinsere alterações locais offline pendentes
          for (const c of unsynced) {
            await db.contatos.put(c);
          }

          // Insere registros válidos recebidos do servidor central
          for (const s of data) {
            const local = await db.contatos.get(s.id);
            if (!local) {
              await db.contatos.put({
                id: s.id,
                nome: s.nome,
                telefone: s.telefone,
                email: s.email || '',
                tipo_numero: s.tipo_numero,
                atualizado_em: s.atualizado_em,
                sincronizado: true,
                excluido: s.excluido
              });
            }
          }
        });
      }
    } catch (err) {
      console.error('Error fetching contacts from server:', err);
    }
  };

  /**
   * Sincronização Inteligente em Lote:
   * Reúne todas as alterações offline do IndexedDB e faz push em lote para o endpoint /sync.
   * Trata conflitos baseando-se no timestamp 'atualizado_em' (o mais novo vence).
   */
  const triggerSync = async () => {
    if (!navigator.onLine || !userId) return;

    setSyncing(true);
    setSyncMessage(null);

    try {
      // Coleta alterações não sincronizadas
      const unsynced = await db.contatos.filter(c => !c.sincronizado).toArray();

      if (unsynced.length === 0) {
        setSyncing(false);
        return;
      }

      const payload = {
        contatos: unsynced.map(c => ({
          id: c.id,
          nome: c.nome,
          telefone: c.telefone,
          email: c.email || null,
          tipo_numero: c.tipo_numero,
          atualizado_em: c.atualizado_em,
          excluido: c.excluido
        }))
      };

      const res = await fetch(`${API_BASE}/contatos/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`,
          'x-user-id': userId
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const result = await res.json();
        const syncedIds = result.contatos_atualizados || [];

        await db.transaction('rw', db.contatos, async () => {
          for (const id of syncedIds) {
            const contact = await db.contatos.get(id);
            if (contact) {
              if (contact.excluido) {
                // Se foi excluído offline e o servidor confirmou, removemos fisicamente do cache
                await db.contatos.delete(id);
              } else {
                // Marca como sincronizado no IndexedDB local
                await db.contatos.update(id, { sincronizado: true });
              }
            }
          }
        });

        setSyncMessage({ type: 'success', text: `Sincronizado ${syncedIds.length} contato(s) com sucesso.` });
        await loadContactsFromServer();
      } else {
        setSyncMessage({ type: 'error', text: 'Falha ao sincronizar dados com o servidor.' });
      }
    } catch (err) {
      setSyncMessage({ type: 'error', text: 'Conexão falhou ao tentar sincronizar.' });
      console.error(err);
    } finally {
      setSyncing(false);
    }
  };

  /**
   * Função auxiliar para ambiente de testes/demonstração.
   * Permite alternar rapidamente a identidade simulada no topo do widget.
   */
  const handleSwitchUser = (newId: string) => {
    setUserId(newId);
    localStorage.setItem('x-user-id', newId);
    const role = newId === 'admin123' ? 'GESTOR' : 'CONSULTOR';
    setUserRole(role);
  };

  // ==========================================
  // OPERAÇÕES CRUD (Escritas Locais e Instant Sync)
  // ==========================================

  const openCreateModal = () => {
    setEditingContactId(null);
    setFormNome('');
    setFormTelefone('');
    setFormEmail('');
    setFormTipo('publico');
    setIsModalOpen(true);
  };

  const openEditModal = (contact: LocalContato) => {
    setEditingContactId(contact.id);
    setFormNome(contact.nome);
    setFormTelefone(contact.telefone);
    setFormEmail(contact.email || '');
    setFormTipo(contact.tipo_numero);
    setIsModalOpen(true);
  };

  const handleSaveContact = async (e: React.FormEvent) => {
    e.preventDefault();

    // Generate a UUID with a fallback for environments where crypto.randomUUID is unavailable (e.g., jsdom in tests)
    const generateId = () => {
      if (typeof crypto !== 'undefined' && typeof (crypto as any).randomUUID === 'function') {
        return (crypto as any).randomUUID();
      }
      // UUID v4 fallback
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
      });
    };
    const id = editingContactId || generateId();
    const now = new Date().toISOString();

    const newContact: LocalContato = {
      id,
      nome: formNome,
      telefone: formTelefone,
      email: formEmail,
      tipo_numero: formTipo,
      atualizado_em: now,
      sincronizado: false,
      excluido: false
    };

    // 1. Escrita Local Instantânea (Optimistic UI)
    await db.contatos.put(newContact);
    setIsModalOpen(false);

    // 2. Envio Assíncrono ao Servidor Central (se online)
    if (isOnline) {
      try {
        const url = editingContactId ? `${API_BASE}/contatos/${editingContactId}` : `${API_BASE}/contatos/`;
        const method = editingContactId ? 'PUT' : 'POST';

        const requestBody = editingContactId ? {
          nome: formNome,
          telefone: formTelefone,
          email: formEmail || null,
          tipo_numero: formTipo
        } : {
          id,
          nome: formNome,
          telefone: formTelefone,
          email: formEmail || null,
          tipo_numero: formTipo
        };

        const res = await fetch(url, {
          method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getAuthToken()}`,
            'x-user-id': userId
          },
          body: JSON.stringify(requestBody)
        });


        if (res.ok) {
          await db.contatos.update(id, { sincronizado: true });
        }
      } catch (err) {
        console.warn("Direct online save failed, queued for background sync", err);
      }
    }
  };

  const handleDeleteContact = async (id: string, name: string) => {
    if (!confirm(`Deseja realmente excluir o contato ${name}?`)) return;

    const now = new Date().toISOString();

    // 1. Exclusão Lógica Local (Soft Delete)
    await db.contatos.update(id, { excluido: true, sincronizado: false, atualizado_em: now });

    // 2. Envio da exclusão ao Servidor Central (se online)
    if (isOnline) {
      try {
        const res = await fetch(`${API_BASE}/contatos/${id}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getAuthToken()}`,
            'x-user-id': userId
          }
        });

        if (res.ok) {
          // Se confirmado pelo servidor, limpa o registro fisicamente do IndexedDB local
          await db.contatos.delete(id);
        }
      } catch (err) {
        console.warn("Direct online delete failed, queued for background sync", err);
      }
    }
  };

  // ==========================================
  // FILTRAGEM E ORDENAÇÃO DE RAMAIS
  // ==========================================

  const filteredContacts = localContacts.filter(c => {
    const matchesSearch =
      c.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.telefone.includes(searchQuery) ||
      (c.email && c.email.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesType = filterType === 'todos' || c.tipo_numero === filterType;

    return matchesSearch && matchesType;
  }).sort((a, b) => a.nome.localeCompare(b.nome));

  // ==========================================
  // RENDERIZAÇÃO DA INTERFACE DO SUBMÓDULO
  // ==========================================

  return (
    <div className="subapp-container">
      {/* Header Compacto para Widget */}
      <header className="subapp-header">
        <div className="header-brand">
          <Phone size={20} className="brand-icon" />
          <div>
            <h1>Ramais HCFMB</h1>
            <p className="subtitle">Mapeamento integrado intranet</p>
          </div>
        </div>

        {/* Barra de Status e Ferramentas */}
        <div className="header-actions">
          {/* Badge Simulador de Identidade (Apenas Teste/Dev) */}
          <div className="role-badge" title="Identidade simulada para controle de acessos">
            <User size={14} />
            <span>ID: {userId} ({userRole})</span>
            <button
              type="button"
              className="switch-user-btn"
              onClick={() => handleSwitchUser(userId === 'admin123' ? 'colaborador456' : 'admin123')}
            >
              Alternar
            </button>
          </div>

          <div className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
            {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
            <span>{isOnline ? 'Online' : 'Offline'}</span>
          </div>

          {pendingSyncCount > 0 && (
            <button
              className="sync-action-btn"
              onClick={triggerSync}
              disabled={syncing || !isOnline}
              title={`${pendingSyncCount} pendentes de sincronização`}
            >
              <RefreshCw size={14} className={syncing ? 'spin-animation' : ''} />
              <span>{pendingSyncCount}</span>
            </button>
          )}

          {/* UI Guard: Exibe o botão de adição apenas para GESTOR */}
          {userRole === 'GESTOR' && (
            <button className="add-contact-btn" onClick={openCreateModal}>
              <Plus size={16} />
              Novo Ramal
            </button>
          )}
        </div>
      </header>

      {/* Alertas e Status */}
      {syncMessage && (
        <div className={`alert-toast toast-${syncMessage.type}`}>
          <Info size={16} />
          <span>{syncMessage.text}</span>
          <button onClick={() => setSyncMessage(null)} className="close-toast-btn">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Área Principal de Ramais */}
      <main className="subapp-main">
        {/* Barra de Busca e Filtros de Categorias */}
        <section className="search-filter-bar">
          <div className="search-box">
            <Search size={16} className="search-box-icon" />
            <input
              type="text"
              placeholder="Buscar ramal ou setor..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <button
              className={filterType === 'todos' ? 'active' : ''}
              onClick={() => setFilterType('todos')}
            >
              Todos
            </button>
            <button
              className={filterType === 'institucional' ? 'active' : ''}
              onClick={() => setFilterType('institucional')}
            >
              Institucionais
            </button>
            <button
              className={filterType === 'publico' ? 'active' : ''}
              onClick={() => setFilterType('publico')}
            >
              Públicos
            </button>
          </div>
        </section>

        {/* Listagem Dinâmica dos Ramais */}
        <section className="ramais-list">
          {filteredContacts.length === 0 ? (
            <div className="empty-state">
              Nenhum ramal cadastrado nesta busca.
            </div>
          ) : (
            filteredContacts.map(c => (
              <div className="ramal-card" key={c.id}>
                {!c.sincronizado && (
                  <div className="sync-pending-tag" title="Aguardando sincronização de rede">
                    <CloudOff size={12} />
                  </div>
                )}

                <div className="ramal-card-content">
                  <div className="ramal-badge" data-type={c.tipo_numero}>
                    {c.tipo_numero === 'institucional' ? 'INST' : 'PUBL'}
                  </div>

                  <div className="ramal-details">
                    <h3>{c.nome}</h3>
                    <p className="phone-number">{c.telefone}</p>
                    {c.email && (
                      <p className="email-addr">
                        <Mail size={12} />
                        {c.email}
                      </p>
                    )}
                  </div>
                </div>

                {/* UI Guard: Exibe ações de modificação (Editar/Excluir) apenas para GESTOR */}
                {userRole === 'GESTOR' && (
                  <div className="ramal-card-actions">
                    <button className="edit-btn" onClick={() => openEditModal(c)} title="Editar ramal">
                      <Edit2 size={13} />
                    </button>
                    <button className="delete-btn" onClick={() => handleDeleteContact(c.id, c.nome)} title="Excluir ramal">
                      <Trash2 size={13} />
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </section>
      </main>

      {/* Modal de Criação / Edição */}
      {isModalOpen && (
        <div className="modal-overlay">
          <form className="modal-form" onSubmit={handleSaveContact}>
            <div className="modal-header">
              <h3>{editingContactId ? 'Editar Ramal' : 'Cadastrar Novo Ramal'}</h3>
              <button type="button" onClick={() => setIsModalOpen(false)} className="close-modal-btn">
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <div className="form-field">
                <label htmlFor="formNome">Setor / Identificação</label>
                <input
                  id="formNome"
                  type="text"
                  required
                  placeholder="Ex: Recepção PS"
                  value={formNome}
                  onChange={(e) => setFormNome(e.target.value)}
                />
              </div>

              <div className="form-field">
                <label htmlFor="formTelefone">Número / Ramal</label>
                <input
                  id="formTelefone"
                  type="text"
                  required
                  placeholder="Ex: (14) 3811-1234 ou 1234"
                  value={formTelefone}
                  onChange={(e) => setFormTelefone(e.target.value)}
                />
              </div>

              <div className="form-field">
                <label htmlFor="formEmail">Email Corporativo (Opcional)</label>
                <input
                  id="formEmail"
                  type="email"
                  placeholder="Ex: contato@hcfmb.unesp.br"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                />
              </div>

              <div className="form-field">
                <label htmlFor="formTipo">Categoria de Ramal</label>
                <select
                  id="formTipo"
                  value={formTipo}
                  onChange={(e) => setFormTipo(e.target.value as 'institucional' | 'publico')}
                >
                  <option value="publico">Público</option>
                  <option value="institucional">Institucional (Restrito)</option>
                </select>
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="cancel-btn" onClick={() => setIsModalOpen(false)}>
                Cancelar
              </button>
              <button type="submit" className="save-btn">
                Salvar Ramal
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Estilos CSS do Submódulo Embutido (Aesthetics) */}
      <style jsx global>{`
        .subapp-container {
          width: 100%;
          max-width: 100%;
          min-height: 100vh;
          background: #fafafa;
          color: #262626;
          font-family: inherit;
          display: flex;
          flex-direction: column;
        }

        .subapp-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          background: #ffffff;
          border-bottom: 1px solid #eaeaea;
          flex-wrap: wrap;
          gap: 12px;
        }

        .header-brand {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .brand-icon {
          color: #008B95;
        }

        .header-brand h1 {
          font-size: 16px;
          font-weight: 700;
          margin: 0;
          color: #1a1a1a;
          line-height: 1.2;
        }

        .header-brand .subtitle {
          font-size: 11px;
          color: #8c8c8c;
          margin: 0;
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .role-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          background: #f0f0f0;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          color: #555;
          font-weight: 500;
        }

        .switch-user-btn {
          background: #e2e2e2;
          border: none;
          color: #333;
          padding: 2px 6px;
          border-radius: 3px;
          cursor: pointer;
          font-size: 10px;
          margin-left: 4px;
        }

        .switch-user-btn:hover {
          background: #d4d4d4;
        }

        .status-badge {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }

        .status-badge.online {
          background: #e6f7ed;
          color: #14804a;
        }

        .status-badge.offline {
          background: #feecef;
          color: #c92a3e;
        }

        .sync-action-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          background: #fff8eb;
          border: 1px solid #ffe8cc;
          color: #c96e00;
          padding: 4px 8px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 11px;
          font-weight: 600;
        }

        .add-contact-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          background: #008B95;
          color: #ffffff;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s;
        }

        .add-contact-btn:hover {
          background: #00737a;
        }

        .subapp-main {
          flex: 1;
          padding: 20px;
          max-width: 900px;
          margin: 0 auto;
          width: 100%;
        }

        .search-filter-bar {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 20px;
        }

        .search-box {
          display: flex;
          align-items: center;
          background: #ffffff;
          border: 1px solid #eaeaea;
          border-radius: 6px;
          padding: 8px 12px;
          width: 100%;
        }

        .search-box-icon {
          color: #8c8c8c;
          margin-right: 8px;
        }

        .search-box input {
          border: none;
          background: none;
          outline: none;
          font-size: 14px;
          width: 100%;
          color: #262626;
        }

        .filter-group {
          display: flex;
          gap: 6px;
        }

        .filter-group button {
          background: #ffffff;
          border: 1px solid #eaeaea;
          padding: 6px 12px;
          font-size: 12px;
          font-weight: 500;
          border-radius: 4px;
          cursor: pointer;
          color: #595959;
          transition: all 0.2s;
        }

        .filter-group button.active {
          background: #008B95;
          color: #ffffff;
          border-color: #008B95;
        }

        .ramais-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .ramal-card {
          position: relative;
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: #ffffff;
          border: 1px solid #eaeaea;
          border-radius: 6px;
          padding: 12px 16px;
          transition: box-shadow 0.2s;
        }

        .ramal-card:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        .ramal-card-content {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .ramal-badge {
          display: flex;
          justify-content: center;
          align-items: center;
          width: 44px;
          height: 44px;
          border-radius: 6px;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.5px;
        }

        .ramal-badge[data-type="publico"] {
          background: #e6f4f8;
          color: #006080;
        }

        .ramal-badge[data-type="institucional"] {
          background: #fff3e6;
          color: #994d00;
        }

        .ramal-details h3 {
          font-size: 14px;
          font-weight: 600;
          margin: 0 0 2px 0;
          color: #1a1a1a;
        }

        .ramal-details .phone-number {
          font-size: 15px;
          font-weight: 700;
          color: #008B95;
          margin: 0;
        }

        .ramal-details .email-addr {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 11px;
          color: #8c8c8c;
          margin: 2px 0 0 0;
        }

        .ramal-card-actions {
          display: flex;
          gap: 6px;
        }

        .ramal-card-actions button {
          display: flex;
          justify-content: center;
          align-items: center;
          width: 28px;
          height: 28px;
          border-radius: 4px;
          border: 1px solid #eaeaea;
          cursor: pointer;
          background: #ffffff;
          color: #595959;
          transition: all 0.2s;
        }

        .ramal-card-actions button.edit-btn:hover {
          background: #f0f7f4;
          color: #008B95;
          border-color: #a3d9dc;
        }

        .ramal-card-actions button.delete-btn:hover {
          background: #feecef;
          color: #c92a3e;
          border-color: #fca5ad;
        }

        .sync-pending-tag {
          position: absolute;
          top: 4px;
          right: 4px;
          color: #c96e00;
        }

        .empty-state {
          text-align: center;
          padding: 40px;
          color: #8c8c8c;
          background: #ffffff;
          border: 1px solid #eaeaea;
          border-radius: 6px;
        }

        /* Modal Overlay */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.4);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
          padding: 16px;
        }

        .modal-form {
          background: #ffffff;
          width: 100%;
          max-width: 440px;
          border-radius: 8px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.1);
          overflow: hidden;
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid #eaeaea;
        }

        .modal-header h3 {
          margin: 0;
          font-size: 15px;
          font-weight: 700;
          color: #1a1a1a;
        }

        .close-modal-btn {
          background: none;
          border: none;
          color: #8c8c8c;
          cursor: pointer;
        }

        .modal-body {
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .form-field {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .form-field label {
          font-size: 12px;
          font-weight: 600;
          color: #555;
        }

        .form-field input, .form-field select {
          border: 1px solid #eaeaea;
          border-radius: 4px;
          padding: 8px 12px;
          font-size: 14px;
          color: #262626;
          outline: none;
          transition: border-color 0.2s;
        }

        .form-field input:focus, .form-field select:focus {
          border-color: #008B95;
        }

        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          padding: 12px 20px;
          background: #fafafa;
          border-top: 1px solid #eaeaea;
        }

        .modal-footer button {
          padding: 8px 16px;
          font-size: 13px;
          font-weight: 600;
          border-radius: 4px;
          cursor: pointer;
        }

        .cancel-btn {
          background: #ffffff;
          border: 1px solid #eaeaea;
          color: #595959;
        }

        .save-btn {
          background: #008B95;
          border: none;
          color: #ffffff;
        }

        .save-btn:hover {
          background: #00737a;
        }

        /* Alert Toast */
        .alert-toast {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 16px 20px 0 20px;
          padding: 10px 14px;
          border-radius: 4px;
          font-size: 13px;
          line-height: 1.4;
        }

        .toast-success {
          background: #e6f7ed;
          color: #14804a;
        }

        .toast-error {
          background: #feecef;
          color: #c92a3e;
        }

        .close-toast-btn {
          background: none;
          border: none;
          color: inherit;
          cursor: pointer;
          margin-left: auto;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .spin-animation {
          animation: spin 1.2s linear infinite;
        }

        @media (max-width: 600px) {
          .subapp-header {
            flex-direction: column;
            align-items: flex-start;
          }
          .header-actions {
            width: 100%;
            justify-content: space-between;
          }
        }
      `}</style>
    </div>
  );
}
