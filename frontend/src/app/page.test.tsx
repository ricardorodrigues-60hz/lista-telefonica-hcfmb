jest.mock('../db/db', () => ({
  db: {
    transaction: async (_mode: any, _stores: any, fn: any) => fn(),
    contatos: {
      filter: () => ({ toArray: async () => [] }),
      toArray: async () => [],
      get: async () => null,
      put: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    },
  },
}));
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
    // Mock POST endpoint for create/edit and GET contacts
    mockFetch({
      '/contatos': { body: [] }
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
    // Wait for any fetch calls to settle
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    // Verify that a POST request to the contacts endpoint was made at least once
    const postCalls = (fetch as jest.Mock).mock.calls.filter(call =>
      typeof call[0] === 'string' &&
      call[0].includes('/contatos') &&
      !call[0].includes('/sync') &&
      (call[1] as RequestInit)?.method === 'POST'
    );
    expect(postCalls.length).toBeGreaterThan(0);
  });
});
