# Documentation – `page.tsx`

## Overview
This file implements the main **React** component for the *Lista Telefônica* sub‑application (ramais HCFMB). It provides:
- User identity handling (via query string or `localStorage`).
- Role‑based UI guards (`GESTOR` vs `CONSULTOR`).
- Offline‑first data sync with **Dexie.js** (IndexedDB).
- CRUD operations (create / edit / delete) for contacts.
- Sync status UI (online/offline, pending sync count, manual sync button).
- A modal form for creating and editing contacts.
- A searchable, filterable list of contacts.
- Service‑worker registration scoped to `/lista-telefonica/`.

## Key Constants
- **`API_BASE`** – Base path for all backend requests.
  ```ts
  const API_BASE = '/lista-telefonica';
  ```

## API Routes Used
| Route | HTTP Method | Purpose | Request Body (when applicable) |
|------|-------------|---------|--------------------------------|
| `${API_BASE}/contatos` | **GET** | Fetch the full list of contacts from the central server. | – |
| `${API_BASE}/contatos/sync` | **POST** | Push locally‑modified contacts (offline changes) to the server in batch. | `{ contatos: LocalContato[] }` |
| `${API_BASE}/contatos/` | **POST** | Create a new contact. | `{ id, nome, telefone, email?, tipo_numero }` |
| `${API_BASE}/contatos/{id}` | **PUT** | Edit an existing contact. | `{ nome, telefone, email?, tipo_numero }` |
| `${API_BASE}/contatos/{id}` | **DELETE** | Soft‑delete a contact on the server. | – |

All requests include the headers **`'x-user-id': userId`** and **`'Authorization': Bearer <TOKEN>`** so the backend can enforce role‑based permissions and authentication.

## Main Hooks & State
| State | Type | Description |
|------|------|-------------|
| `userId` | `string` | Current user identifier (from URL query, `localStorage`, or fallback). |
| `userRole` | `'GESTOR' \| 'CONSULTOR'` | Derived from `userId`; only `admin123` is a `GESTOR`. |
| `isOnline` | `boolean` | Browser online/offline status (updated via `window` events). |
| `syncing` | `boolean` | Indicates a background sync is in progress. |
| `syncMessage` | `{type: 'success'|'warning'|'error', text: string}` | UI toast feedback after a sync operation. |
| `searchQuery` / `filterType` | `string` | Controls client‑side filtering of contacts. |
| `localContacts` | `LocalContato[]` | Live query from IndexedDB (Dexie) – all contacts not marked as `excluido`. |
| `pendingSyncCount` | `number` | Number of contacts with `sincronizado === false`. |
| Modal related states (`isModalOpen`, `editingContactId`, form fields) | – | Manage the create/edit modal. |

## Side Effects
1. **Service‑worker registration** – Scoped to `/lista-telefonica/`.
2. **User resolution** – Reads `user_id` from URL or `localStorage`; stores back to `localStorage`.
3. **Role derivation** – Maps `admin123` → `GESTOR`, else `CONSULTOR`.
4. **Online/offline listeners** – Update `isOnline` and trigger sync when back online.
5. **Data loading** – When `userId` or `isOnline` changes, `loadContactsFromServer()` runs.

## CRUD Flow
- **Create / Edit** (`handleSaveContact`):
  1. Generates an UUID if needed.
  2. Writes contact locally (optimistic UI).
  3. If online, POST to `/contatos/` or PUT to `/contatos/{id}`.
  4. On success, marks contact `sincronizado: true`.
- **Delete** (`handleDeleteContact`):
  1. Soft‑deletes locally (`excluido: true`).
  2. If online, DELETE to `/contatos/{id}`.
  3. On server success, removes record from IndexedDB.
- **Sync** (`triggerSync`):
  - Collects all unsynced contacts, sends them to `/contatos/sync`.
  - Updates local records based on server response (`contatos_atualizados`).

## UI Guard Logic
- Buttons for **Add**, **Edit**, **Delete** are rendered only when `userRole === 'GESTOR'`.
- The role badge at the header shows the current simulated identity and allows switching between `admin123` and a regular user.

## Potential Issues / Checks
- All fetch calls assume JSON responses; any non‑JSON error will throw in the `catch` block.
- `handleSwitchUser` does not refresh contacts after role change – the `useEffect` that depends on `userId` will automatically reload.
- No explicit error handling for the GET `/contatos` call; failures are logged to console only.
- The modal form does not validate phone/email formats beyond HTML5 `required`/`type=email`.
- The CSS is embedded via a `<style jsx global>` block – ensure the project’s build supports styled‑jsx (e.g., Next.js).

---

# How to Run the Tests
The repository already includes **Jest** and **React Testing Library** (commonly used in Next.js/React projects). The test file created alongside `page.tsx` (`page.test.tsx`) contains three basic suites:
1. **Render tests** – verify that the component renders without crashing for both `GESTOR` and `CONSULTOR` roles.
2. **API interaction tests** – mock `fetch` to ensure the component calls the correct endpoints when loading contacts and when performing a CRUD operation.
3. **UI guard tests** – confirm that the *Add Contact* button only appears for a manager.

To execute:
```bash
npm install   # install dev dependencies if not present
npm test      # runs jest (or `npm run test` if configured)
```
All tests are located in `frontend/src/app/page.test.tsx`.

---

# Test File – `page.test.tsx`
Below is the complete test implementation. It is deliberately lightweight but covers the requested documentation.
```tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Home from './page';

// Helper to mock fetch responses
const mockFetch = (responses: Record<string, any>) => {
  global.fetch = jest.fn().mockImplementation((url: RequestInfo) => {
    const endpoint = (url as string).replace(/^.*\/lista-telefonica/, '');
    const response = responses[endpoint] ?? { status: 404 };
    return Promise.resolve({
      ok: response.ok ?? true,
      status: response.status ?? 200,
      json: () => Promise.resolve(response.body ?? []),
    } as Response);
  });
};

describe('page.tsx – Lista Telefônica UI', () => {
  beforeEach(() => {
    // Reset fetch mock before each test
    jest.restoreAllMocks();
    // Default mock for GET /contatos – empty list
    mockFetch({ '/contatos': { body: [] } });
  });

  test('renders without crashing for admin (GESTOR)', async () => {
    // Simulate admin user via URL query
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost/?user_id=admin123'),
      writable: true,
    });
    render(<Home />);
    // Wait for the async loadContactsFromServer to finish
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/lista-telefonica/contatos', expect.any(Object)));
    // Verify role badge shows GESTOR and Add button is present
    expect(screen.getByText(/ID: admin123 \(GESTOR\)/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Novo Ramal/i })).toBeInTheDocument();
  });

  test('renders CONSULTOR view – Add button hidden', async () => {
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost/?user_id=colaborador456'),
      writable: true,
    });
    render(<Home />);
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(screen.getByText(/ID: colaborador456 \(CONSULTOR\)/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Novo Ramal/i })).not.toBeInTheDocument();
  });

  test('calls correct API when creating a contact (admin)', async () => {
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost/?user_id=admin123'),
      writable: true,
    });
    // Mock POST endpoint for create/edit
    mockFetch({
      '/contatos/': { ok: true },
      '/contatos': { body: [] },
    });
    render(<Home />);
    // Open modal
    fireEvent.click(screen.getByRole('button', { name: /Novo Ramal/i }));
    // Fill form fields
    fireEvent.change(screen.getByLabelText(/Setor/i), { target: { value: 'Recepção' } });
    fireEvent.change(screen.getByLabelText(/Número/i), { target: { value: '1234' } });
    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/Categoria de Ramal/i), { target: { value: 'publico' } });
    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /Salvar Ramal/i }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      '/lista-telefonica/contatos/',
      expect.objectContaining({ method: 'POST' })
    ));
  });
});
```
---

# Summary
- The component follows a clear offline‑first pattern with Dexie and provides a well‑structured UI.
- All API routes are documented above.
- Tests cover rendering for both roles, API call verification, and UI‑guard behavior.
- Run `npm test` to execute the suite.

Feel free to expand the test suite (e.g., simulate offline sync, error handling) as needed.
