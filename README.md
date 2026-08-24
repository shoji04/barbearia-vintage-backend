# Barbearia Vintage — Backend

API REST para o sistema de agendamento de uma barbearia: cadastro de
funcionários com login via JWT, CRUD de clientes e CRUD de agendamentos,
com disparo automático de webhook (n8n) para envio de e-mail de confirmação
a cada novo agendamento.

**Deploy:** https://barbearia-vintage-backend.onrender.com

## Tecnologias

- [Flask](https://flask.palletsprojects.com/) — framework web
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) — ORM
- [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) — autenticação via JWT
- [Flask-Cors](https://flask-cors.readthedocs.io/) — CORS
- **PostgreSQL** em produção (via `psycopg`) e **SQLite** em desenvolvimento local
- [Gunicorn](https://gunicorn.org/) — servidor WSGI de produção

## Como rodar localmente

### 1. Instalar dependências

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar o `.env`

Crie um arquivo `.env` na raiz do projeto com as variáveis descritas em
[Variáveis de ambiente](#variáveis-de-ambiente). Para uso local, basta
definir `JWT_SECRET_KEY` e `CODIGO_FUNCIONARIO` — sem `DATABASE_URL` a
aplicação usa SQLite automaticamente.

### 3. Criar o funcionário inicial (seed)

Existem duas formas de criar o primeiro funcionário:

- **Script interativo:**

  ```bash
  python seed_funcionario.py
  ```

- **Rota da API** (`POST /register`), informando o `CODIGO_FUNCIONARIO`
  configurado no `.env`.

### 4. Rodar a aplicação

```bash
python app.py
```

A API sobe em `http://localhost:5001` (ou na porta definida em `PORT`).

## Rotas da API

Todas as rotas retornam JSON. Rotas marcadas com 🔒 exigem o header
`Authorization: Bearer <token>` obtido no login.

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/login` | Autentica um funcionário (`email`, `senha`) e retorna o token JWT |
| POST | `/register` | Cadastra um novo funcionário mediante `codigo` de acesso válido |
| GET | `/clientes` 🔒 | Lista todos os clientes |
| GET | `/clientes/<id>` 🔒 | Retorna um cliente específico |
| POST | `/clientes` 🔒 | Cria um novo cliente |
| PUT | `/clientes/<id>` 🔒 | Atualiza um cliente existente |
| DELETE | `/clientes/<id>` 🔒 | Remove um cliente |
| GET | `/agendamentos` 🔒 | Lista agendamentos (filtro opcional `?data=AAAA-MM-DD`) |
| POST | `/agendamentos` 🔒 | Cria um agendamento e dispara o webhook do n8n |
| PUT | `/agendamentos/<id>` 🔒 | Atualiza data, horário, serviço ou status de um agendamento |
| DELETE | `/agendamentos/<id>` 🔒 | Remove um agendamento |

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `JWT_SECRET_KEY` | Sim | Chave secreta usada para assinar os tokens JWT |
| `CODIGO_FUNCIONARIO` | Sim | Código exigido em `/register` para permitir o cadastro de um novo funcionário |
| `N8N_WEBHOOK_URL` | Sim | URL do webhook do n8n acionado ao criar um agendamento (envio de e-mail) |
| `DATABASE_URL` | Não | String de conexão do PostgreSQL (produção/Render). Se não definida, usa SQLite local |

Variáveis adicionais opcionais: `PORT` (porta do servidor, definida
automaticamente pelo Render) e `FLASK_DEBUG` (ativa o modo debug do Flask
em desenvolvimento).
