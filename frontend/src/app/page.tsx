'use client';

import React, { useState, useEffect } from 'react';
import { useLiveQuery } from 'dexie-react-hooks';
import { 
  Phone, Mail, Search, Plus, Edit2, Trash2, Cloud, CloudOff, 
  RefreshCw, LogIn, LogOut, Shield, User, Info, Wifi, WifiOff, X
} from 'lucide-react';
import { db, type LocalContato } from '../db/db';

const API_BASE = 'http://localhost:8085/api';

export default function Home() {
  // Authentication states
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [userRole, setUserRole] = useState<'GESTOR' | 'CONSULTOR' | null>(null);
  const [userName, setUserName] = useState<string>('');
  
  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  
  // Sync and connection state
  const [isOnline, setIsOnline] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'warning' | 'error', text: string } | null>(null);
  
  // Search and Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'todos' | 'institucional' | 'publico'>('todos');
  
  // Form modal state (for creation/edition)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingContactId, setEditingContactId] = useState<string | null>(null);
  const [formNome, setFormNome] = useState('');
  const [formTelefone, setFormTelefone] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formTipo, setFormTipo] = useState<'institucional' | 'publico'>('publico');
  
  // Fetch current contacts from local IndexedDB using Dexie
  const localContacts = useLiveQuery(
    () => db.contatos.filter(c => !c.excluido).toArray()
  ) || [];

  const pendingSyncCount = useLiveQuery(
    () => db.contatos.filter(c => !c.sincronizado).count()
  ) || 0;

  // Initialize Auth from localStorage and setup connection listeners
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedToken = localStorage.getItem('access_token');
      const storedRefreshToken = localStorage.getItem('refresh_token');
      const storedRole = localStorage.getItem('user_role') as 'GESTOR' | 'CONSULTOR' | null;
      const storedName = localStorage.getItem('user_name') || '';
      
      if (storedToken) {
        setToken(storedToken);
        setRefreshToken(storedRefreshToken);
        setUserRole(storedRole);
        setUserName(storedName);
      }
      
      setIsOnline(navigator.onLine);
      
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
  }, []);

  // Fetch from server when online & authenticated
  useEffect(() => {
    if (token && isOnline) {
      loadContactsFromServer();
    }
  }, [token, isOnline]);

  const loadContactsFromServer = async () => {
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
        // Clear all synced, then add new ones
        await db.transaction('rw', db.contatos, async () => {
          // Keep unsynced local changes, delete rest
          const unsynced = await db.contatos.filter(c => !c.sincronizado).toArray();
          await db.contatos.clear();
          
          // Re-insert unsynced
          for (const c of unsynced) {
            await db.contatos.put(c);
          }
          
          // Insert ones from server (setting sync=true)
          for (const s of data) {
            // Only insert if it doesn't clash with unsynced local version
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

  // Sync IndexedDB with remote SQLite
  const triggerSync = async () => {
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
                // Delete physical local copy if it's marked soft delete and fully synced
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
  };

  const handleLogin = async (e: React.FormEvent) => {
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
    } catch (err) {
      setLoginError('Não foi possível conectar ao servidor backend.');
    }
  };

  const handleLogout = async () => {
    // Revoga a sessão no servidor (rotação de refresh token).
    // Best-effort: se o dispositivo estiver offline, apenas seguimos com a limpeza local.
    if (refreshToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
      } catch (err) {
        // Sem conexão ou servidor indisponível: a sessão local é encerrada mesmo assim.
      }
    }

    setToken(null);
    setRefreshToken(null);
    setUserRole(null);
    setUserName('');
    localStorage.clear();
    db.contatos.clear(); // Clear cache for security
  };

  // CRUD actions
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
    
    // Save locally to IndexedDB
    await db.contatos.put(newContact);
    setIsModalOpen(false);
    
    // Try to sync instantly if online
    if (isOnline) {
      // If we are online, also hit the online direct CRUD endpoint
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
    
    // Soft delete locally
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
          // Delete completely if server confirms
          await db.contatos.delete(id);
        }
      } catch (err) {
        console.warn("Direct online delete failed, queued for background sync", err);
      }
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

  // Render Login screen if not authenticated
  if (!token) {
    return (
      <div className="login-container">
        <form className="login-card" onSubmit={handleLogin}>
          <div className="login-header">
            {/* Using the UNESP/HCFMB Portal logo */}
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
          <div className="menu-item active">
            <Phone size={18} />
            <span>Lista Telefônica</span>
          </div>
          
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ padding: '8px 16px', fontSize: '12px', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isOnline ? 'var(--color-success)' : 'var(--color-error)' }}>
                {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
                <span>{isOnline ? 'Dispositivo Online' : 'Modo Offline Ativo'}</span>
              </div>
              {pendingSyncCount > 0 && (
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
              <h1>Lista Telefônica</h1>
              <p>HCFMB - Hospital das Clínicas de Botucatu</p>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            {pendingSyncCount > 0 && isOnline && (
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
            
            {userRole === 'GESTOR' && (
              <button className="btn btn-primary" onClick={openCreateModal}>
                <Plus size={16} />
                Novo Contato
              </button>
            )}
          </div>
        </header>

        {syncMessage && (
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
            <span>Operando em modo offline. Alterações serão guardadas localmente e enviadas ao servidor quando a conexão retornar.</span>
          </div>
        )}

        {/* Search & Filtering */}
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

        {/* Contacts Cards Display */}
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
      </main>

      {/* Creation/Edition Modal */}
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
