# Relatório de Diagnóstico — Estado ANTES das Correções

Este documento registra os erros de sintaxe, falsos positivos de linting, dependências faltantes e problemas de importação identificados antes da intervenção no repositório `backend`.

---

## 1. Falsos Positivos de Ortografia (`typos` / `pre_lint`)
A ferramenta de verificação ortográfica `typos` (executada via `pre_lint`) estava configurada sem dicionário de exceções para palavras em português. Isso causava **57 erros de linting**, bloqueando o comando `task test`:

### Principais erros apontados pelo `typos`:
- `README.md`: `controle` sugerido como `control`, `clientes` sugerido como `clients`, `ative` sugerido como `active`, `instale` sugerido como `install`.
- `Dockerfile`: `oficial` sugerido como `official`, `vai` sugerido como `via`, `Comando` sugerido como `Commando`.
- `app/modules/usuarios.py`: parâmetro `autor` sugerido como `author`.
- `app/modules/contatos.py`: termo `momento` e docstrings com `cliente` sugeridos como `memento` e `client`.
- `app/modules/sync.py`: variáveis e métodos `_timestamp_cliente_naive_utc`, `cliente_atualizado_em`, `cliente` sugeridos como `client`.
- `app/modules/auth.py`: `CredenciaisInvalidasError` e docstrings com `funcional` sugeridos como `Invalidates` e `functional`.
- `tests/*`: docstrings e testes contendo `ser`, `atual`, `ignora` sugeridos como `set`, `actual`, `ignore`.

---

## 2. Erros de Sintaxe e Importação nos Módulos (`app/`)

### A. Typos em nomes de classes em `app/core.py`
- A exceção de autenticação estava declarada com erro de digitação no nome da classe:
  ```python
  class CredenciaisInvalidatesError(AppError):
      status_code = HTTPStatus.UNAUTHORIZED
      detail = 'E-mail ou senha inválidos.'
  ```
- **Consequência**: Ao tentar importar `CredenciaisInvalidasError` em `app/modules/auth.py`, ocorria um `ImportError`.

### B. Importação Circular em `app/core.py`
- O arquivo `app/core.py` continha importações no topo do arquivo:
  ```python
  from app.modules.contatos import Contato
  from app.modules.usuarios import Usuario
  ```
- Como `app.modules.contatos` e `app.modules.usuarios` importam `Base` de `app.core`, ocorria o erro:
  ```text
  ImportError: cannot import name 'Base' from partially initialized module 'app.core' (most likely due to a circular import)
  ```

### C. Conflitos de Namespace e Imports Redundantes em `app/modules/contatos.py`
- Importação duplicada e não utilizada na linha 14:
  ```python
  import datetime
  ```
  seguida na linha 21 por:
  ```python
  from datetime import datetime, timezone
  ```
- Anotação de tipo incorreta na classe `ContatoResponse`:
  ```python
  class ContatoResponse(ContatoBase):
      id: UUID
      criado_em: Optional[datetime.datetime] = None
      atualizado_em: datetime.datetime
  ```
- **Consequência**: Como `datetime` já era a classe `datetime.datetime`, tentar usar `datetime.datetime` gerava erro de atributo/tipo em tempo de execução.

---

## 3. Configurações de Linting e Testes em `pyproject.toml`

### A. Dependências de Desenvolvimento Ausentes
- Faltava a biblioteca `aiosqlite`, impedindo o SQLAlchemy de conectar ao banco em memória `sqlite+aiosqlite:///:memory:` durante as suítes de testes assíncronas.
- Faltava o plugin `pytest-asyncio`, impedindo o `pytest` de executar funções de teste marcadas com `async def`.

### B. Alvo de Cobertura Incorreto
- A configuração do `pytest` apontava para um módulo inexistente:
  ```toml
  addopts = ['-p', 'no:warnings', '--cov=lista_backend', '--cov-context=test']
  ```
- **Consequência**: O relatório de cobertura falhava com o aviso `CoverageWarning: Module lista_backend was never imported`.

### C. Regras do Ruff Sem Ignorar Padrões Válidos
- Com `preview = true` ativado no Ruff sem a lista de `ignore`, o linter gerava **87 avisos/erros** sobre imports dentro de funções de rotas (padrão essencial no FastAPI para evitar imports circulares) e comparações de números mágicos em testes.
