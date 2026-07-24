'use client';

import React, { useState, useEffect } from 'react';
import { useLiveQuery } from 'dexie-react-hooks';
import { 
  Phone, Mail, Search, Plus, Edit2, Trash2, Cloud, CloudOff, 
  RefreshCw, LogIn, LogOut, Shield, Info, Wifi, WifiOff, X, Users, User, UserPlus
} from 'lucide-react';
import { db, type LocalContato } from '../db/db';

const API_BASE = 'http://localhost:8085/api';

interface Usuario {
  id: string;
  nome: string;
  email: string;
  papel: 'GESTOR' | 'CONSULTOR';
  criado_em: string;
  atualizado_em: string;
  excluido: boolean;
}

export default function Home() {
  // Utility: read from localStorage safely (SSR-safe)
  function getStoredValue(key: string): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(key);
  }

  // Navigation tab state
  const [activeTab, setActiveTab] = useState<'contatos' | 'usuarios'>('contatos');

  // Authentication states (lazy init from localStorage)
  const [token, setToken] = useState<string | null>(() => getStoredValue('access_token'));
  const [refreshToken, setRefreshToken] = useState<string | null>(() => getStoredValue('refresh_token'));
  const [userRole, setUserRole] = useState<'GESTOR' | 'CONSULTOR' | null>(
    () => getStoredValue('user_role') as 'GESTOR' | 'CONSULTOR' | null
  );
  const [userName, setUserName] = useState<string>(() => getStoredValue('user_name') || '');
  
  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  
  // Sync and connection state
  const [isOnline, setIsOnline] = useState(() => typeof window !== 'undefined' ? navigator.onLine : true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'warning' | 'error', text: string } | null>(null);
  
  // Search and Filter states (Contatos)
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'todos' | 'institucional' | 'publico'>('todos');
  
  // Form modal state (for contact creation/edition)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingContactId, setEditingContactId] = useState<string | null>(null);
  const [formNome, setFormNome] = useState('');
  const [formTelefone, setFormTelefone] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formTipo, setFormTipo] = useState<'institucional' | 'publico'>('publico');

  // Users Management state
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loadingUsuarios, setLoadingUsuarios] = useState(false);
  const [usuariosError, setUsuariosError] = useState<string | null>(null);
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [userFilterRole, setUserFilterRole] = useState<'todos' | 'GESTOR' | 'CONSULTOR'>('todos');

  // User Modal state
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [userFormNome, setUserFormNome] = useState('');
  const [userFormEmail, setUserFormEmail] = useState('');
  const [userFormSenha, setUserFormSenha] = useState('');
  const [userFormPapel, setUserFormPapel] = useState<'GESTOR' | 'CONSULTOR'>('CONSULTOR');
  const [userModalError, setUserModalError] = useState<string | null>(null);
  
  // Fetch current contacts from local IndexedDB using Dexie
  const localContacts = useLiveQuery(
    () => db.contatos.filter(c => !c.excluido).toArray()
  ) || [];

  const pendingSyncCount = useLiveQuery(
    () => db.contatos.filter(c => !c.sincronizado).count()
  ) || 0;

  // Setup connection listeners
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const handleOnline = () => {
        setIsOnline(true);
        triggerSync();
      };
      const handleOffline = () => setIsOnline(false);
      
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
      
      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch contacts from server when online & authenticated
  useEffect(() => {
    if (token && isOnline) {
      loadContactsFromServer();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isOnline]);

  // Fetch users from server when activeTab === 'usuarios' and role is GESTOR
  useEffect(() => {
    if (token && isOnline && userRole === 'GESTOR' && activeTab === 'usuarios') {
      loadUsuariosFromServer();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isOnline, userRole, activeTab]);

  async function handleLogout() {
    if (refreshToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
      } catch {
        // Sem conexão ou servidor indisponível: a sessão local é encerrada mesmo assim.
      }
    }

    setToken(null);
    setRefreshToken(null);
    setUserRole(null);
    setUserName('');
    setActiveTab('contatos');
    localStorage.clear();
    db.contatos.clear();
  }

  async function loadContactsFromServer() {
    try {
      const res = await fetch(`${API_BASE}/contatos`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.status === 401) {
        handleLogout();
        return;
      }
      
      if (res.ok) {
        const data = await res.json();
        await db.transaction('rw', db.contatos, async () => {
          const unsynced = await db.contatos.filter(c => !c.sincronizado).toArray();
          await db.contatos.clear();
          
          for (const c of unsynced) {
            await db.contatos.put(c);
          }
          
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
  }

  async function loadUsuariosFromServer() {
    if (!token || userRole !== 'GESTOR') return;
    setLoadingUsuarios(true);
    setUsuariosError(null);
    try {
      const res = await fetch(`${API_BASE}/usuarios`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.status === 401) {
        handleLogout();
        return;
      }

      if (res.ok) {
        const data = await res.json();
        setUsuarios(data);
      } else {
        const errData = await res.json().catch(() => ({}));
        setUsuariosError(errData.detail || 'Falha ao carregar a lista de usuários.');
      }
    } catch (err) {
      console.error('Error fetching usuarios:', err);
      setUsuariosError('Não foi possível conectar ao servidor backend.');
    } finally {
      setLoadingUsuarios(false);
    }
  }

  // Sync IndexedDB with remote SQLite
  async function triggerSync() {
    if (!navigator.onLine || !token) return;
    
    setSyncing(true);
    setSyncMessage(null);
    
    try {
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
          email: c.email || '',
          tipo_numero: c.tipo_numero,
          atualizado_em: c.atualizado_em,
          excluido: c.excluido
        }))
      };
      
      const res = await fetch(`${API_BASE}/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
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
                await db.contatos.delete(id);
              } else {
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
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginError('');
    
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login: loginEmail, senha: loginPassword })
      });
      
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        setRefreshToken(data.refresh_token);
        setUserRole(data.papel);
        setUserName(data.nome);
        
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user_role', data.papel);
        localStorage.setItem('user_name', data.nome);
      } else {
        const errData = await res.json();
        const errorMsg = typeof errData.detail === 'string' 
          ? errData.detail 
          : (Array.isArray(errData.detail) && errData.detail.length > 0 && errData.detail[0].msg
              ? errData.detail[0].msg
              : 'Falha na autenticação.');
        setLoginError(errorMsg);
      }
    } catch {
      setLoginError('Não foi possível conectar ao servidor backend.');
    }
  }

  // Contact CRUD actions
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
    
    const id = editingContactId || crypto.randomUUID();
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
    
    await db.contatos.put(newContact);
    setIsModalOpen(false);
    
    if (isOnline) {
      try {
        const res = await fetch(`${API_BASE}/contatos/${id}`, {
          method: editingContactId ? 'PUT' : 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            nome: formNome,
            telefone: formTelefone,
            email: formEmail || null,
            tipo_numero: formTipo
          })
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
    
    await db.contatos.update(id, { excluido: true, sincronizado: false, atualizado_em: now });
    
    if (isOnline) {
      try {
        const res = await fetch(`${API_BASE}/contatos/${id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          await db.contatos.delete(id);
        }
      } catch (err) {
        console.warn("Direct online delete failed, queued for background sync", err);
      }
    }
  };

  // User CRUD actions
  const openCreateUserModal = () => {
    setEditingUserId(null);
    setUserFormNome('');
    setUserFormEmail('');
    setUserFormSenha('');
    setUserFormPapel('CONSULTOR');
    setUserModalError(null);
    setIsUserModalOpen(true);
  };

  const openEditUserModal = (userItem: Usuario) => {
    setEditingUserId(userItem.id);
    setUserFormNome(userItem.nome);
    setUserFormEmail(userItem.email);
    setUserFormSenha('');
    setUserFormPapel(userItem.papel);
    setUserModalError(null);
    setIsUserModalOpen(true);
  };

  const handleSaveUsuario = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserModalError(null);

    const isEdit = !!editingUserId;
    const url = isEdit ? `${API_BASE}/usuarios/${editingUserId}` : `${API_BASE}/usuarios`;
    const method = isEdit ? 'PUT' : 'POST';

    const payload: Record<string, any> = {
      nome: userFormNome,
      papel: userFormPapel,
    };

    if (!isEdit) {
      payload.email = userFormEmail;
      payload.senha = userFormSenha;
    } else if (userFormSenha) {
      payload.senha = userFormSenha;
    }

    try {
      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setIsUserModalOpen(false);
        await loadUsuariosFromServer();
      } else {
        const errData = await res.json().catch(() => ({}));
        const errorMsg = typeof errData.detail === 'string'
          ? errData.detail
          : (Array.isArray(errData.detail) && errData.detail.length > 0 && errData.detail[0].msg
              ? errData.detail[0].msg
              : 'Falha ao salvar usuário.');
        setUserModalError(errorMsg);
      }
    } catch (err) {
      console.error('Error saving user:', err);
      setUserModalError('Erro de conexão ao salvar usuário.');
    }
  };

  const handleDeleteUsuario = async (userId: string, targetUserName: string) => {
    if (!confirm(`Deseja realmente excluir o usuário ${targetUserName}?`)) return;

    try {
      const res = await fetch(`${API_BASE}/usuarios/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (res.ok) {
        await loadUsuariosFromServer();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || 'Não foi possível excluir o usuário.');
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      alert('Erro de conexão ao tentar excluir usuário.');
    }
  };

  // Filtered contacts
  const filteredContacts = localContacts.filter(c => {
    const matchesSearch = 
      c.nome.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.telefone.includes(searchQuery) ||
      (c.email && c.email.toLowerCase().includes(searchQuery.toLowerCase()));
      
    const matchesType = filterType === 'todos' || c.tipo_numero === filterType;
    
    return matchesSearch && matchesType;
  }).sort((a, b) => a.nome.localeCompare(b.nome));

  // Filtered usuarios
  const filteredUsuarios = usuarios.filter(u => {
    const matchesSearch = 
      u.nome.toLowerCase().includes(userSearchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearchQuery.toLowerCase());
      
    const matchesRole = userFilterRole === 'todos' || u.papel === userFilterRole;
    
    return matchesSearch && matchesRole;
  }).sort((a, b) => a.nome.localeCompare(b.nome));

  // Render Login screen if not authenticated
  if (!token) {
    return (
      <div className="login-container">
        <form className="login-card" onSubmit={handleLogin}>
          <div className="login-header">
            <img src="https://portal.hcfmb.unesp.br/imagem/logo.png" alt="HCFMB UNESP Logo" />
            <h2 className="login-title">Aciono Você</h2>
            <p className="login-subtitle">Acesso Restrito à Lista Telefônica</p>
          </div>
          
          {loginError && (
            <div className="alert alert-error" style={{ margin: '0 0 20px 0' }}>
              <Info size={16} />
              <span>{loginError}</span>
            </div>
          )}
          
          <div className="form-group">
            <label className="form-label">E-mail funcional</label>
            <input 
              type="email" 
              className="form-input" 
              placeholder="seu-nome@hcfmb.unesp.br" 
              required
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
            />
          </div>
          
          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">Senha</label>
            <input 
              type="password" 
              className="form-input" 
              placeholder="••••••••" 
              required
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
            />
          </div>
          
          <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
            <LogIn size={18} />
            Entrar
          </button>
          
          <div style={{ marginTop: '20px', fontSize: '11px', color: '#888' }}>
            Dica: use <b>gestor@hcfmb.unesp.br</b> (senha <b>gestor123</b>) ou <b>consultor@hcfmb.unesp.br</b> (senha <b>consultor123</b>)
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar / Drawer */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={20} />
            <span style={{ fontWeight: 700, fontSize: '18px' }}>Aciono Você</span>
          </div>
          <div style={{ fontSize: '13px', opacity: 0.9 }}>
            <p style={{ fontWeight: 600 }}>{userName}</p>
            <p style={{ fontSize: '11px', opacity: 0.8 }}>Papel: {userRole}</p>
          </div>
        </div>
        
        <div className="sidebar-menu">
          <div 
            className={`menu-item ${activeTab === 'contatos' ? 'active' : ''}`}
            onClick={() => setActiveTab('contatos')}
          >
            <Phone size={18} />
            <span>Lista Telefônica</span>
          </div>

          {userRole === 'GESTOR' && (
            <div 
              className={`menu-item ${activeTab === 'usuarios' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('usuarios');
                loadUsuariosFromServer();
              }}
            >
              <Users size={18} />
              <span>Gestão de Usuários</span>
            </div>
          )}
          
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ padding: '8px 16px', fontSize: '12px', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isOnline ? 'var(--color-success)' : 'var(--color-error)' }}>
                {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
                <span>{isOnline ? 'Dispositivo Online' : 'Modo Offline Ativo'}</span>
              </div>
              {activeTab === 'contatos' && pendingSyncCount > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px', color: 'var(--color-warning)' }}>
                  <Cloud size={14} className="syncing-animate" />
                  <span>{pendingSyncCount} pendente(s)</span>
                </div>
              )}
            </div>
            
            <button className="btn btn-danger" onClick={handleLogout} style={{ justifyContent: 'flex-start' }}>
              <LogOut size={18} />
              Sair
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="app-header">
          <div className="header-brand">
            <img src="https://portal.hcfmb.unesp.br/imagem/logo.png" alt="HCFMB logo" className="header-logo" />
            <div className="header-title-container">
              <h1>{activeTab === 'contatos' ? 'Lista Telefônica' : 'Gestão de Usuários'}</h1>
              <p>HCFMB - Hospital das Clínicas de Botucatu</p>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            {activeTab === 'contatos' && pendingSyncCount > 0 && isOnline && (
              <button 
                className="btn btn-secondary" 
                onClick={triggerSync} 
                disabled={syncing}
                title="Sincronizar dados pendentes"
              >
                <RefreshCw size={16} className={syncing ? 'spin-animation' : ''} />
                Sincronizar
              </button>
            )}
            
            {activeTab === 'contatos' && userRole === 'GESTOR' && (
              <button className="btn btn-primary" onClick={openCreateModal}>
                <Plus size={16} />
                Novo Contato
              </button>
            )}

            {activeTab === 'usuarios' && userRole === 'GESTOR' && (
              <button className="btn btn-primary" onClick={openCreateUserModal}>
                <UserPlus size={16} />
                Novo Usuário
              </button>
            )}
          </div>
        </header>

        {syncMessage && activeTab === 'contatos' && (
          <div className={`alert alert-${syncMessage.type}`}>
            <Info size={16} />
            <span>{syncMessage.text}</span>
            <button 
              onClick={() => setSyncMessage(null)} 
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
            >
              <X size={16} />
            </button>
          </div>
        )}

        {!isOnline && (
          <div className="alert alert-warning">
            <WifiOff size={16} />
            <span>
              {activeTab === 'contatos'
                ? 'Operando em modo offline. Alterações serão guardadas localmente e enviadas ao servidor quando a conexão retornar.'
                : 'Operando em modo offline. A gestão de usuários necessita de conexão com o servidor.'}
            </span>
          </div>
        )}

        {/* TAB 1: CONTATOS */}
        {activeTab === 'contatos' && (
          <>
            <section className="search-container">
              <div className="search-input-wrapper">
                <Search size={18} className="search-icon" />
                <input 
                  type="text" 
                  className="search-input" 
                  placeholder="Buscar por nome, telefone ou email..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className={`btn ${filterType === 'todos' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setFilterType('todos')}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Todos
                </button>
                <button 
                  className={`btn ${filterType === 'institucional' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setFilterType('institucional')}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Institucional
                </button>
                <button 
                  className={`btn ${filterType === 'publico' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setFilterType('publico')}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Público
                </button>
              </div>
            </section>

            <section className="contacts-grid">
              {filteredContacts.length === 0 ? (
                <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#8c8c8c' }}>
                  Nenhum contato encontrado.
                </div>
              ) : (
                filteredContacts.map(c => (
                  <div className="card" key={c.id}>
                    {!c.sincronizado && (
                      <div className="sync-indicator" title="Pendente de sincronização">
                        <CloudOff size={16} />
                      </div>
                    )}
                    
                    <div className="card-main">
                      <div className="icon-wrapper">
                        <Phone size={22} />
                      </div>
                      <div className="card-info">
                        <h3 className="card-title">{c.nome}</h3>
                        <p className="card-subtitle" style={{ fontWeight: 600, color: 'var(--color-primary)' }}>
                          {c.telefone}
                        </p>
                        {c.email && (
                          <p className="card-subtitle" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Mail size={12} />
                            {c.email}
                          </p>
                        )}
                        <span className={`card-badge badge-${c.tipo_numero}`}>
                          {c.tipo_numero}
                        </span>
                      </div>
                    </div>
                    
                    {userRole === 'GESTOR' && (
                      <div className="card-actions">
                        <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => openEditModal(c)}>
                          <Edit2 size={12} />
                          Editar
                        </button>
                        <button className="btn btn-danger" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => handleDeleteContact(c.id, c.nome)}>
                          <Trash2 size={12} />
                          Excluir
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </section>
          </>
        )}

        {/* TAB 2: USUÁRIOS */}
        {activeTab === 'usuarios' && userRole === 'GESTOR' && (
          <>
            <section className="search-container">
              <div className="search-input-wrapper">
                <Search size={18} className="search-icon" />
                <input 
                  type="text" 
                  className="search-input" 
                  placeholder="Buscar usuário por nome ou e-mail..." 
                  value={userSearchQuery}
                  onChange={(e) => setUserSearchQuery(e.target.value)}
                />
              </div>
              
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className={`btn ${userFilterRole === 'todos' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setUserFilterRole('todos')}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Todos
                </button>
                <button 
                  className={`btn ${userFilterRole === 'GESTOR' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setUserFilterRole('GESTOR')}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Gestores
                </button>
                <button 
                  className={`btn ${userFilterRole === 'CONSULTOR' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setUserFilterRole('CONSULTOR')}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Consultores
                </button>
              </div>
            </section>

            {usuariosError && (
              <div className="alert alert-error">
                <Info size={16} />
                <span>{usuariosError}</span>
              </div>
            )}

            <section className="contacts-grid">
              {loadingUsuarios ? (
                <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#8c8c8c' }}>
                  Carregando usuários...
                </div>
              ) : filteredUsuarios.length === 0 ? (
                <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#8c8c8c' }}>
                  Nenhum usuário encontrado.
                </div>
              ) : (
                filteredUsuarios.map(u => (
                  <div className="card" key={u.id}>
                    <div className="card-main">
                      <div 
                        className="icon-wrapper" 
                        style={{ 
                          backgroundColor: u.papel === 'GESTOR' ? '#EDE7F6' : undefined, 
                          color: u.papel === 'GESTOR' ? '#673AB7' : undefined 
                        }}
                      >
                        <User size={22} />
                      </div>
                      <div className="card-info">
                        <h3 className="card-title">{u.nome}</h3>
                        <p className="card-subtitle" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Mail size={12} />
                          {u.email}
                        </p>
                        <span className={`card-badge ${u.papel === 'GESTOR' ? 'badge-gestor' : 'badge-consultor'}`}>
                          {u.papel}
                        </span>
                      </div>
                    </div>
                    
                    <div className="card-actions">
                      <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => openEditUserModal(u)}>
                        <Edit2 size={12} />
                        Editar
                      </button>
                      <button 
                        className="btn btn-danger" 
                        style={{ padding: '6px 12px', fontSize: '12px' }} 
                        onClick={() => handleDeleteUsuario(u.id, u.nome)}
                      >
                        <Trash2 size={12} />
                        Excluir
                      </button>
                    </div>
                  </div>
                ))
              )}
            </section>
          </>
        )}
      </main>

      {/* Contact Creation/Edition Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <form className="modal-content" onSubmit={handleSaveContact}>
            <div className="modal-header">
              <h3 className="modal-title">
                {editingContactId ? 'Editar Contato' : 'Adicionar Novo Contato'}
              </h3>
              <button 
                type="button" 
                onClick={() => setIsModalOpen(false)} 
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Nome do Contato</label>
                <input 
                  type="text" 
                  className="form-input" 
                  required 
                  placeholder="Ex: Recepção PS"
                  value={formNome}
                  onChange={(e) => setFormNome(e.target.value)}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">Telefone / Ramal</label>
                <input 
                  type="text" 
                  className="form-input" 
                  required 
                  placeholder="Ex: (14) 3811-1234 ou 1234"
                  value={formTelefone}
                  onChange={(e) => setFormTelefone(e.target.value)}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">E-mail (Opcional)</label>
                <input 
                  type="email" 
                  className="form-input" 
                  placeholder="Ex: contato@hcfmb.unesp.br"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">Tipo do Número</label>
                <select 
                  className="form-input" 
                  style={{ appearance: 'auto' }}
                  value={formTipo}
                  onChange={(e) => setFormTipo(e.target.value as 'institucional' | 'publico')}
                >
                  <option value="publico">Público</option>
                  <option value="institucional">Institucional</option>
                </select>
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary">
                Salvar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* User Creation/Edition Modal */}
      {isUserModalOpen && (
        <div className="modal-overlay">
          <form className="modal-content" onSubmit={handleSaveUsuario}>
            <div className="modal-header">
              <h3 className="modal-title">
                {editingUserId ? 'Editar Usuário' : 'Adicionar Novo Usuário'}
              </h3>
              <button 
                type="button" 
                onClick={() => setIsUserModalOpen(false)} 
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="modal-body">
              {userModalError && (
                <div className="alert alert-error" style={{ margin: '0 0 16px 0' }}>
                  <Info size={16} />
                  <span>{userModalError}</span>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Nome Completo</label>
                <input 
                  type="text" 
                  className="form-input" 
                  required 
                  placeholder="Ex: João da Silva"
                  value={userFormNome}
                  onChange={(e) => setUserFormNome(e.target.value)}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">E-mail</label>
                <input 
                  type="email" 
                  className="form-input" 
                  required={!editingUserId}
                  disabled={!!editingUserId}
                  placeholder="Ex: joao.silva@hcfmb.unesp.br"
                  value={userFormEmail}
                  onChange={(e) => setUserFormEmail(e.target.value)}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">
                  {editingUserId ? 'Nova Senha (opcional)' : 'Senha'}
                </label>
                <input 
                  type="password" 
                  className="form-input" 
                  required={!editingUserId}
                  minLength={6}
                  placeholder={editingUserId ? 'Deixe em branco para manter a senha atual' : 'Mínimo 6 caracteres'}
                  value={userFormSenha}
                  onChange={(e) => setUserFormSenha(e.target.value)}
                />
              </div>
              
              <div className="form-group">
                <label className="form-label">Papel / Função</label>
                <select 
                  className="form-input" 
                  style={{ appearance: 'auto' }}
                  value={userFormPapel}
                  onChange={(e) => setUserFormPapel(e.target.value as 'GESTOR' | 'CONSULTOR')}
                >
                  <option value="CONSULTOR">CONSULTOR (Apenas visualiza contatos)</option>
                  <option value="GESTOR">GESTOR (Acesso total + Gestão de usuários)</option>
                </select>
              </div>
            </div>
            
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setIsUserModalOpen(false)}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary">
                Salvar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Animation helpers */}
      <style jsx global>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .spin-animation {
          animation: spin 1.2s linear infinite;
        }
        .syncing-animate {
          animation: pulse 1.5s infinite ease-in-out;
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
