# Ello API

Backend do sistema de gestão escolar, inicialmente focado em alunos e biblioteca.

## Rodar localmente

```bash
uv sync
uv run alembic upgrade head
uv run ello
```

A documentação interativa fica em `http://127.0.0.1:8000/docs`.

## Configuração

- `DATABASE_URL`: conexão do banco. O padrão local é `sqlite:///./escola.db`.
- `MIGRATION_DATABASE_URL`: conexão usada apenas pelo Alembic. No Supabase,
  prefira a conexão direta para migrações.
- `DATABASE_POOL_MODE`: use `session` em servidor persistente e `transaction`
  em deploy serverless/autoscaling com o pooler de transação do Supabase.
- `FRONTEND_ORIGINS`: origens permitidas pelo navegador, separadas por vírgula.
  O padrão é `http://localhost:5173`.
- `JWT_SECRET`: chave aleatória de pelo menos 32 caracteres usada para assinar tokens.
- `JWT_EXPIRE_MINUTES`: duração do login; o padrão é 480 minutos (8 horas).
- `PORT`: porta fornecida pela hospedagem; o padrão local é 8000.

Exemplo para PostgreSQL:

```bash
DATABASE_URL="postgresql+psycopg://usuario:senha@host/banco" \
uv run alembic upgrade head
```

O projeto já inclui o driver Psycopg para PostgreSQL.

## Deploy

O SQLite é apenas local. Em produção, crie um projeto no Supabase e configure no
serviço que hospedar a API:

```text
DATABASE_URL=postgresql://...URL do pooler ou conexão da aplicação...
MIGRATION_DATABASE_URL=postgresql://...URL direta para migrações...
DATABASE_POOL_MODE=session
FRONTEND_ORIGINS=https://dominio-real-do-front.example
JWT_SECRET=uma-chave-aleatoria-longa-e-exclusiva-da-producao
JWT_EXPIRE_MINUTES=480
```

Não copie o `.env` local para o deploy. Cadastre os valores no painel secreto da
hospedagem. A URL do banco contém senha e nunca deve entrar no Git.

Comando de preparação/release:

```bash
uv run alembic upgrade head
```

Comando de inicialização da API:

```bash
uv run ello-prod
```

Na Vercel, `api/index.py` expõe o objeto FastAPI diretamente para o runtime
serverless; não configure comando de inicialização nem diretório de saída.

Depois do primeiro deploy, abra o terminal do serviço e execute uma vez:

```bash
uv run criar-admin
```

Se o host for serverless/autoscaling e usar a porta 6543 do pooler de transação,
configure `DATABASE_POOL_MODE=transaction`. Isso desativa prepared statements e
o pool local do SQLAlchemy, evitando conflito com o pooler do Supabase.

## Primeiro administrador

Depois de aplicar as migrações, crie o primeiro administrador pelo terminal:

```bash
uv run criar-admin
```

O comando pede nome, login e senha. A senha não aparece enquanto é digitada e
somente o hash Argon2 é armazenado. Depois disso, o admin cria os demais usuários
pela API e atribui o cargo `biblioteca`.

## Autenticação e autorização

`POST /auth/login` recebe JSON:

```json
{
  "login": "biblioteca",
  "senha": "senha-do-usuario"
}
```

A resposta contém `access_token`. O frontend deve enviá-lo nas rotas protegidas:

```text
Authorization: Bearer <access_token>
```

`GET /auth/me` informa o usuário e os cargos atuais. Todas as rotas `/alunos` e
`/livros` exigem `biblioteca` ou `admin`. Somente `admin` acessa `/usuarios` para
criar contas, trocar senha, ativar/desativar e atribuir cargos.

## Verificações

```bash
uv run ruff check .
uv run pytest
```

## Regra atual de estoque

Cada cadastro de livro representa uma obra/edição e `estoque` informa quantas
unidades iguais existem. `DELETE /livros/{id}` remove uma unidade. Para excluir
todo o cadastro, use `DELETE /livros/{id}?remover_todos=true`.

Se a escola confirmar que cada exemplar físico possui código próprio, será criada
uma tabela de exemplares ligada ao livro; essa regra ainda precisa ser confirmada.

## Migrações

O servidor não altera tabelas automaticamente. Depois de atualizar o projeto,
execute:

```bash
uv run alembic upgrade head
```

Para criar uma nova migração após alterar os modelos:

```bash
uv run alembic revision --autogenerate -m "descricao da alteracao"
```
