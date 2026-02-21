# Auto-Jira

Servico de notificacoes automaticas do Jira no Telegram via webhooks.
Recebe eventos em tempo real e envia mensagens formatadas para seu grupo/chat no Telegram.

---

## Como Funciona

```
Jira Cloud ──webhook──> Railway (Flask/Gunicorn) ──API──> Telegram Bot
                              │
                        POST /webhook/jira
                              │
                     Identifica evento
                     Formata mensagem
                              │
                     Envia para o chat
```

### Eventos Monitorados

| Evento | Descricao | Emoji |
|--------|-----------|-------|
| Issue criada | Nova tarefa, story, epic, etc | 🆕 |
| Status alterado | Mudanca de coluna no board | 🔄 |
| Responsavel alterado | Troca de assignee | 👥 |
| Prioridade alterada | Mudanca de prioridade | ⚡ |
| Comentario criado | Novo comentario em issue | 💬 |
| Issue deletada | Remocao de issue | 🗑️ |

### Exemplo de Notificacao

```
🔄 Status Alterado

📋 KAN-170 — 2FA (TOTP)
━━━━━━━━━━━━━━━━━━━━━━━━
📊 A fazer → Em andamento
👤 Maike Henrique
🔗 Abrir no Jira
⏰ 21/02/2026 15:30
```

---

## Deploy no Railway

### 1. Criar o Servico

1. Acesse [railway.app](https://railway.app) e crie um novo projeto
2. Conecte este repositorio GitHub
3. O Railway detecta o `Dockerfile` automaticamente

### 2. Configurar Variables

No dashboard do Railway, adicione as seguintes variaveis em **Variables**:

| Variavel | Descricao | Obrigatorio |
|----------|-----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token do bot (@BotFather) | Sim |
| `TELEGRAM_CHAT_ID` | ID do chat/grupo | Sim |
| `JIRA_BASE_URL` | URL do Jira (ex: `https://empresa.atlassian.net`) | Sim |
| `JIRA_PROJECT_KEY` | Chave do projeto (ex: `KAN`) | Sim |
| `WEBHOOK_SECRET` | Secret para validar webhooks (opcional) | Nao |

### 3. Registrar Webhook no Jira

Apos o deploy, copie a URL gerada pelo Railway (ex: `https://auto-jira-xxx.up.railway.app`).

**Via interface do Jira:**

1. Acesse: `Settings > System > Webhooks`
   Ou diretamente: `https://SEU-DOMINIO.atlassian.net/plugins/servlet/webhooks`
2. Clique em **Create a webhook**
3. Configure:
   - **Name:** `Auto-Jira Telegram`
   - **URL:** `https://SUA-URL-RAILWAY.up.railway.app/webhook/jira`
   - **Events:** Marque:
     - Issue: created, updated, deleted
     - Comment: created
   - **JQL Filter:** `project = KAN`
4. Salve

**Via script (alternativo):**

```bash
python scripts/jira_register_webhook.py --register https://SUA-URL-RAILWAY.up.railway.app
```

### 4. Testar

```bash
# Testa se o servico esta online
python scripts/jira_register_webhook.py --test https://SUA-URL-RAILWAY.up.railway.app

# Ou via curl
curl https://SUA-URL-RAILWAY.up.railway.app/
```

Depois, altere o status de qualquer issue no Jira e verifique o Telegram.

---

## Configurar Bot do Telegram

Se voce ainda nao tem um bot:

1. Abra o Telegram e fale com [@BotFather](https://t.me/BotFather)
2. Envie `/newbot` e siga as instrucoes
3. Copie o **token** gerado
4. Crie um grupo e adicione o bot, ou inicie conversa direta
5. Para descobrir o `chat_id`:
   ```bash
   curl https://api.telegram.org/bot<SEU_TOKEN>/getUpdates
   ```
   Procure por `"chat":{"id": ...}`

---

## Scripts Utilitarios

Scripts para gerenciamento local do projeto Jira (rodam na sua maquina, nao no Railway):

| Script | Descricao |
|--------|-----------|
| `jira_register_webhook.py` | Registra/lista/deleta webhooks no Jira |
| `jira_telegram_notify.py` | Resumo diario + alertas de deadline no Telegram |
| `jira_move_status.py` | Move issues para qualquer status via CLI |
| `jira_set_duedates.py` | Atribui due dates em batch |
| `jira_set_in_progress.py` | Move issues para "Em andamento" em batch |
| `jira_nexusp2p_update.py` | Atualiza tarefas do NexusP2P |
| `jira_kan13_v2_update.py` | Atualiza plano LexNotify |
| `jira_daily_telegram.py` | Resumo diario completo do projeto |

### Uso dos Scripts

```bash
# Instalar dependencias
pip install requests python-dotenv

# Copiar e preencher .env
cp .env.example .env

# Exemplos
python scripts/jira_move_status.py "Em andamento" KAN-170 KAN-171
python scripts/jira_telegram_notify.py --setup
python scripts/jira_register_webhook.py --list
```

---

## Desenvolvimento Local

```bash
# Clonar
git clone https://github.com/MHX-Digital/Auto-Jira.git
cd Auto-Jira

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Edite .env com seus tokens

# Rodar servidor local
python app.py

# Testar webhook localmente (outra aba)
curl -X POST http://localhost:5000/webhook/jira \
  -H "Content-Type: application/json" \
  -d '{"webhookEvent":"jira:issue_updated","issue":{"key":"KAN-1","fields":{"summary":"Teste"}},"user":{"displayName":"Dev"},"changelog":{"items":[{"field":"status","fromString":"A fazer","toString":"Em andamento"}]}}'
```

### Docker Local

```bash
docker build -t auto-jira .
docker run -p 8080:8080 --env-file .env auto-jira
```

---

## Endpoints

| Metodo | Rota | Descricao |
|--------|------|-----------|
| `GET` | `/` | Health check (status + uptime) |
| `POST` | `/webhook/jira` | Recebe webhooks do Jira |

---

## Seguranca

- **Webhook Secret:** Configure `WEBHOOK_SECRET` para validar que requests vem do Jira
- **Rate Limiting:** Max 60 mensagens/minuto para evitar flood
- **Filtro por Projeto:** Apenas issues do projeto configurado sao processadas
- **Dados sensiveis:** `.env` no `.gitignore`, nunca suba tokens para o repositorio

---

## Estrutura

```
Auto-Jira/
├── app.py              # Servico Flask (webhook receiver)
├── Dockerfile          # Build para Railway
├── requirements.txt    # Dependencias Python
├── railway.toml        # Config Railway
├── .env.example        # Template de variaveis
├── .gitignore          # Protecao de dados sensiveis
├── README.md           # Este arquivo
└── scripts/            # Scripts utilitarios (uso local)
    ├── jira_register_webhook.py
    ├── jira_telegram_notify.py
    ├── jira_move_status.py
    ├── jira_set_duedates.py
    ├── jira_set_in_progress.py
    ├── jira_nexusp2p_update.py
    ├── jira_kan13_v2_update.py
    ├── jira_kan13_90day_plan.py
    ├── jira_daily_telegram.py
    └── jira_move_subtasks_to_in_progress.py
```

---

**MHX Digital** — Automacao Jira + Telegram
