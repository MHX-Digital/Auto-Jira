# Auto-Jira

Automacao completa do Jira Cloud para o projeto KAN da MHX Digital.
Webhook em tempo real para Telegram + scripts de gerenciamento + documentacao do projeto.

**Instancia:** https://mhxdigital.atlassian.net
**Projeto:** KAN (team-managed)
**Deploy webhook:** Railway (Dockerfile)

---

## Sumario

- [Arquitetura](#arquitetura)
- [Webhook (Telegram)](#webhook-telegram)
- [Deploy no Railway](#deploy-no-railway)
- [Scripts Ativos](#scripts-ativos)
- [Documentacao do Projeto](#documentacao-do-projeto)
- [Estado Atual do Jira](#estado-atual-do-jira)
- [Restricoes Tecnicas da API](#restricoes-tecnicas-da-api)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Estrutura de Pastas](#estrutura-de-pastas)

---

## Arquitetura

```
Jira Cloud --webhook--> Railway (Flask/Gunicorn) --API--> Telegram Bot
                              |
                        POST /webhook/jira
                              |
                     Identifica evento
                     Formata mensagem
                              |
                     Envia para o chat
```

### Eventos monitorados

| Evento | Descricao |
|--------|-----------|
| Issue criada | Nova tarefa, story, epic, etc |
| Status alterado | Mudanca de coluna (A fazer / Em andamento / Concluido) |
| Responsavel alterado | Troca de assignee |
| Prioridade alterada | Mudanca de prioridade |
| Comentario criado | Novo comentario em issue |
| Issue deletada | Remocao de issue |

### Formato da notificacao

```
[JIRA] Status Alterado

KAN-170 -- 2FA (TOTP)
------------------------
A fazer  >>  Em andamento
Por: Maike Henrique
Abrir no Jira
21/02/2026 15:30
```

### Seguranca

- **Webhook Secret:** Validacao via header (opcional)
- **Rate Limiting:** Max 60 mensagens/minuto
- **Filtro por Projeto:** Apenas issues do KAN sao processadas

---

## Deploy no Railway

### 1. Criar servico

1. Acesse [railway.app](https://railway.app) e crie um novo projeto
2. Conecte o repositorio GitHub: `MHX-Digital/Auto-Jira`
3. O Railway detecta o `Dockerfile` automaticamente

### 2. Configurar Variables

No dashboard do Railway, em **Variables**:

| Variavel | Descricao | Obrigatorio |
|----------|-----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token do bot (@BotFather) | Sim |
| `TELEGRAM_CHAT_ID` | ID do chat/grupo | Sim |
| `JIRA_BASE_URL` | `https://mhxdigital.atlassian.net` | Sim |
| `JIRA_PROJECT_KEY` | `KAN` | Sim |
| `WEBHOOK_SECRET` | UUID para validar requests (opcional) | Nao |

### 3. Registrar webhook no Jira

Apos o deploy, com a URL do Railway:

1. Acesse: `Settings > System > Webhooks` no Jira
   Ou: `https://mhxdigital.atlassian.net/plugins/servlet/webhooks`
2. Clique em **Create a webhook**
3. Configure:
   - **Name:** `Auto-Jira Telegram`
   - **URL:** `https://SUA-URL.up.railway.app/webhook/jira`
   - **Events:** Issue created/updated/deleted + Comment created
   - **JQL Filter:** `project = KAN`
4. Salve

### 4. Testar

```bash
python scripts/jira_register_webhook.py --test https://SUA-URL.up.railway.app
```

Ou altere o status de qualquer issue no Jira e verifique o Telegram.

---

## Scripts Ativos

Scripts para gerenciamento local do projeto (rodam na maquina, nao no Railway).
Todos leem `.env` da raiz do projeto.

| Script | Descricao | Uso |
|--------|-----------|-----|
| `jira_register_webhook.py` | Registra/lista/deleta webhooks no Jira | `--register URL`, `--list`, `--delete ID`, `--test URL` |
| `jira_move_status.py` | Move issues para qualquer status via CLI | `"Em andamento" KAN-170 KAN-171` |
| `jira_set_in_progress.py` | Batch: move issues para "Em andamento" | (sem args) |
| `jira_set_duedates.py` | Atribui due dates 30/60/90 dias | (sem args) |
| `jira_telegram_notify.py` | Resumo + alertas de deadline no Telegram | `--setup`, `--deadlines` |
| `jira_daily_telegram.py` | Resumo diario completo (8h + 19h) | `--test`, `--install`, `--uninstall` |
| `jira_nexusp2p_update.py` | Cria/atualiza 26 tasks pos-beta NexusP2P | `--dry-run` |
| `jira_kan13_v2_update.py` | Atualiza plano 90 dias LexNotify | `--dry-run` |
| `jira_kan13_90day_plan.py` | v1 do plano 90 dias (superseded by v2) | (sem args) |
| `jira_move_subtasks_to_in_progress.py` | Move subtasks para "Em andamento" | (sem args) |
| `gerar_auth_chatgpt.py` | Gera base64 auth para ChatGPT Actions | (sem args) |

### Instalar dependencias

```bash
pip install requests python-dotenv
```

---

## Documentacao do Projeto

Arquivos em `docs/` para manter contexto entre sessoes.

| Arquivo | Conteudo |
|---------|---------|
| `JIRA_SESSAO_COMPLETA.md` | Registro completo de execucao: restricoes API, boards, componentes, epics, issues criadas por sessao, JQLs uteis, labels padrao, contexto estrategico |
| `NEXUSP2P_COMPLETO.md` | NexusP2P: 5 sprints pos-beta (mar-jun 2026), 26 tasks, stack, dependencias externas, progresso por fase |
| `JIRA_INTEGRACAO_COMPLETA.md` | Documentacao operacional da API: endpoints, payloads, exemplos, contrato ADF |
| `GPT_INSTRUCTIONS_AXEROLD.md` | Instrucoes do GPT Bobby Axerold (estrategia + integracao Telegram/Jira) |
| `JIRA_OPENAPI_SCHEMA.yaml` | Schema OpenAPI 3.1 para integracao ChatGPT Actions com Jira |
| `TELEGRAM_OPENAPI_SCHEMA.yaml` | Schema OpenAPI para integracao ChatGPT Actions com Telegram |
| `schema.txt` | Schema de referencia |
| `epics.json` | Dump JSON dos 30 epics com metadados |

### Para continuar de onde parou

1. Leia `docs/JIRA_SESSAO_COMPLETA.md` — tem todo o historico de execucao, issues criadas, restricoes tecnicas
2. Leia `docs/NEXUSP2P_COMPLETO.md` — estado completo do NexusP2P com 5 sprints planejados
3. Veja a secao [Estado Atual](#estado-atual-do-jira) abaixo para o snapshot mais recente

---

## Estado Atual do Jira

**Ultima atualizacao:** 2026-02-21

### Numeros gerais

- ~195 issues (KAN-1 a KAN-195, KAN-56 deletada)
- 31 Epics
- 6 Componentes: GOV, OTC, DELIVERY, PRODUCT, LIQUIDATION, QUANT
- 3 Boards: 1 (simple), 2 (OPERATIONS), 3 (PRODUCT)

### Projetos principais

**KAN-13 — LexNotify AI** (plano 90 dias)

| Fase | Issues | Status | Deadline |
|------|--------|--------|----------|
| P0 (30d) | KAN-100, 101, 102, 106, 107, 162, 168 | Em andamento | 2026-03-20 |
| P1 (60d) | KAN-105, 164, 165, 169 | A fazer | 2026-04-19 |
| P2 (90d) | KAN-55, 57, 103, 104, 166, 167 | A fazer | 2026-05-19 |
| Done | KAN-163 (Billing Stripe), seguranca, legal | Concluido | -- |

**KAN-15 — NexusP2P** (pos-beta, 26 tasks)

| Sprint | Issues | Foco | Deadline |
|--------|--------|------|----------|
| 1 Seguranca | KAN-170~173, 193 | 2FA, sessoes, reCAPTCHA, rate limit | 2026-03-31 |
| 2 Pagamentos | KAN-174~177 | PIX BB API, webhooks, WebSocket | 2026-04-30 |
| 3 Comunicacao | KAN-178~180 | Email, SMS, notificacoes | 2026-05-15 |
| 4 Tecnico | KAN-181~186, 189~190, 194 | Zustand, TanStack, testes, CI/CD | 2026-05-31 |
| 5 Admin | KAN-187~188, 191~192, 195 | KYC OCR, APM, backup, painel admin | 2026-06-30 |

Beta: KAN-61, 62, 63 concluidas.

### Mapa Repositorio -> Epic

| Repositorio | Epic | Componente |
|-------------|------|------------|
| LexNotify | KAN-13 | PRODUCT |
| Hamza Carbon | KAN-14 | PRODUCT |
| NexusP2P | KAN-15 | PRODUCT |
| InceptionPsi | KAN-16 | PRODUCT |
| Shadpay | KAN-17 | PRODUCT |
| MHX-Digital | KAN-129 | PRODUCT |
| SideWallet | KAN-10 | DELIVERY |
| BahiaGold | KAN-11 | DELIVERY |
| Kahincorp-AI | KAN-138 | QUANT |
| APP Fintech | KAN-18 | LIQUIDATION |
| Vrumm | KAN-19 | LIQUIDATION |
| VotoMap | KAN-20 | LIQUIDATION |

### Labels padrao

| Label | Uso |
|-------|-----|
| p1, p2, p3 | Prioridade |
| infra | Infraestrutura / DevOps |
| legal | Juridico / compliance |
| security | Seguranca |
| blocked | Bloqueado |
| waiting_partner | Esperando parceiro externo |
| waiting_client | Esperando cliente |

### Contexto estrategico

| Item | Valor |
|------|-------|
| Meta de caixa | R$150.000 em 3-4 entradas |
| Receitas prioritarias | OTC e Licitacao |
| Stack padrao | Supabase + Auth + Meta Cloud API + GitHub Actions + Sentry |
| Kill-switch | 30% perda por estrategia E por mes |
| Alocacao quant | US$100/estrategia inicial |
| Alavancagem max | 2x futuros, 1x spot |
| WIP | Max 2 cards Doing por board por pessoa |

---

## Restricoes Tecnicas da API

| Restricao | Detalhe |
|-----------|---------|
| Search API | `/rest/api/3/search` retorna **410 Gone**. Usar `/rest/api/3/search/jql` com `nextPageToken` |
| Paginacao | Usar `nextPageToken` (NAO `startAt`) |
| Descricao | Obrigatorio **ADF** (Atlassian Document Format), nao texto puro |
| Issue types | PT-BR: `Tarefa`, `Historia`. Subtask type = `Subtask` (ingles) |
| Parent field | Usar `"parent": {"key": "KAN-xxx"}` (nao epic link custom field) |
| Board config | Team-managed: colunas e workflows NAO configuraveis via API |
| Ranking | `PUT /rest/agile/1.0/issue/rank` aceita request mas nao surte efeito em team-managed |
| Auth | Basic: `base64(email:api_token)` |
| Transitions | Nomes com acentos — usar fuzzy match (`'conclu' in name.lower()`) |

### JQLs uteis

```
-- P1 por board
project = KAN AND labels = p1 AND component in (PRODUCT, LIQUIDATION, QUANT)
project = KAN AND labels = p1 AND component in (GOV, OTC, DELIVERY)

-- Deadlines
project = KAN AND duedate >= now() AND duedate <= 7d ORDER BY duedate ASC

-- Status
project = KAN AND status = "Em andamento" ORDER BY priority DESC

-- Orfaos
project = KAN AND issuetype not in (Epic) AND parent is EMPTY

-- Atualizadas hoje
project = KAN AND updated >= startOfDay() ORDER BY updated DESC
```

---

## Desenvolvimento Local

```bash
# Clonar
git clone https://github.com/MHX-Digital/Auto-Jira.git
cd Auto-Jira

# Dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Preencha com seus tokens

# Rodar webhook local
python app.py

# Testar webhook
curl -X POST http://localhost:5000/webhook/jira \
  -H "Content-Type: application/json" \
  -d '{"webhookEvent":"jira:issue_updated","issue":{"key":"KAN-1","fields":{"summary":"Teste"}},"user":{"displayName":"Dev"},"changelog":{"items":[{"field":"status","fromString":"A fazer","toString":"Em andamento"}]}}'
```

### Docker local

```bash
docker build -t auto-jira .
docker run -p 8080:8080 --env-file .env auto-jira
```

### Endpoints

> **Nota:** Todas as rotas `/api/*` requerem autenticacao via header `Authorization: Bearer <APP_SECRET_KEY>`.
> As rotas `/cron/*` aceitam Bearer token ou query param `?secret=<CRON_SECRET>`.

**Health**

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/` | Health check (status + uptime + projeto) |

**Webhooks**

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/webhook/jira` | Recebe webhooks do Jira Cloud e notifica Telegram |
| POST | `/webhook/telegram` | Recebe updates do Telegram Bot (comandos + chat AI) |

**Dashboard**

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/dashboard` | Painel HTML com cards, issues em andamento e alertas de deadline |

**API Middleware (auth required)**

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/health` | Health check autenticado |
| GET | `/api/jira/status` | Resumo do projeto (contagens por status + lista de issues) |
| GET | `/api/jira/deadlines` | Issues atrasadas e vencendo nos proximos 7 dias |
| GET | `/api/jira/search` | Busca issues via JQL (query param `?jql=`) |
| GET | `/api/jira/issue/<key>` | Detalhes de uma issue especifica |
| POST | `/api/jira/issue` | Cria nova issue no Jira |
| PUT | `/api/jira/issue/<key>` | Atualiza campos de uma issue existente |
| POST | `/api/jira/issue/<key>/transition` | Move issue para outro status (ou lista transitions disponiveis) |
| POST | `/api/telegram/send` | Envia mensagem de texto via Telegram |
| POST | `/api/telegram/send-photo` | Envia foto via Telegram |
| POST | `/api/telegram/send-document` | Envia documento via Telegram |
| POST | `/api/telegram/send-poll` | Cria enquete via Telegram |
| GET | `/api/telegram/updates` | Lista updates recentes do Telegram (filtrado por owner) |

**Cron (auth required)**

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET/POST | `/cron/daily-digest` | Trigger externo do resumo diario (envia no Telegram) |
| GET/POST | `/cron/test` | Dry-run do digest (retorna preview sem enviar) |

---

## Estrutura de Pastas

```
Auto-Jira/
|-- app.py                  # Webhook Flask (deploy Railway)
|-- Dockerfile              # Build para Railway
|-- requirements.txt        # flask, gunicorn, requests
|-- railway.toml            # Config Railway
|-- .env.example            # Template de variaveis
|-- .gitignore              # Protege .env e dados sensiveis
|-- README.md               # Este arquivo
|
|-- scripts/                # Scripts utilitarios (uso local)
|   |-- jira_register_webhook.py
|   |-- jira_move_status.py
|   |-- jira_set_in_progress.py
|   |-- jira_set_duedates.py
|   |-- jira_telegram_notify.py
|   |-- jira_daily_telegram.py
|   |-- jira_nexusp2p_update.py
|   |-- jira_kan13_v2_update.py
|   |-- jira_kan13_90day_plan.py
|   |-- jira_move_subtasks_to_in_progress.py
|   +-- gerar_auth_chatgpt.py
|
|-- docs/                   # Documentacao e referencia
|   |-- JIRA_SESSAO_COMPLETA.md
|   |-- NEXUSP2P_COMPLETO.md
|   |-- JIRA_INTEGRACAO_COMPLETA.md
|   |-- GPT_INSTRUCTIONS_AXEROLD.md
|   |-- JIRA_OPENAPI_SCHEMA.yaml
|   |-- TELEGRAM_OPENAPI_SCHEMA.yaml
|   |-- schema.txt
|   +-- epics.json
|
+-- _archive/               # Scripts legados (referencia historica)
    |-- jira_executor.py
    |-- jira_audit_v2.py
    |-- jira_config.py
    |-- jira_fix_kahincorp.py
    |-- jira_operacao_poder.py
    |-- jira_passo234.py
    |-- jira_rank.py
    |-- jira_repos_pendentes.py
    +-- verify.py
```

---

**MHX Digital** -- Automacao Jira + Telegram
