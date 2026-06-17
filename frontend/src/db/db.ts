import Dexie, { type Table } from 'dexie';

export interface LocalContato {
  id: string; // UUID
  nome: string;
  telefone: string;
  email?: string;
  tipo_numero: 'institucional' | 'publico';
  atualizado_em: string; // ISO string
  sincronizado: boolean; // false = local change pending sync
  excluido: boolean; // soft delete flag
}

export class AcionoVoceDB extends Dexie {
  contatos!: Table<LocalContato>;

  constructor() {
    super('AcionoVoceDB');
    this.version(1).stores({
      contatos: 'id, nome, telefone, email, tipo_numero, atualizado_em, sincronizado, excluido'
    });
  }
}

export const db = new AcionoVoceDB();
