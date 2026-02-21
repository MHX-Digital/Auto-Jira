# Jira KAN — Registro Completo de Execucao

**Instancia:** https://mhxdigital.atlassian.net
**Projeto:** KAN (team-managed / next-gen, ID 10000)
**Credenciais:** ver `.env`
**Data de execucao:** 2026-02-14 a 2026-02-15

---

## Restricoes Tecnicas Importantes

| Item | Detalhe |
|------|---------|
| Search API | `/rest/api/3/search` retorna **410 Gone**. Usar `/rest/api/3/search/jql` com `nextPageToken` |
| Paginacao | Usar `nextPageToken` (NAO `startAt`) |
| Descricao | Obrigatorio **ADF** (Atlassian Document Format), nao texto puro |
| Issue types | PT-BR: `Tarefa`, `Historia`. Subtask type = `Subtask` (ingles) |
| Parent field | Usar `"parent": {"key": "KAN-xxx"}` (nao epic link custom field) |
| Board config | Boards team-managed: colunas e workflows NAO configuraveis via API |
| Ranking | `PUT /rest/agile/1.0/issue/rank` aceita request mas nao surte efeito em team-managed |
| Due date | Campo `duedate` formato `YYYY-MM-DD` |
| Auth | Basic Auth: `base64(email:api_token)` |

---

## Infraestrutura Criada

### Boards (IDs fixos)

| ID | Nome | Tipo | Componentes |
|----|------|------|-------------|
| 1 | KAN board | simple | todos |
| 2 | OPERATIONS (OTC/DELIVERY/GOV) | kanban | GOV, OTC, DELIVERY |
| 3 | PRODUCT (Software e Escala) | kanban | PRODUCT, LIQUIDATION, QUANT |

### Componentes (6)

| Componente | Board | Descricao |
|------------|-------|-----------|
| GOV | OPERATIONS | Governanca, juridico, PJ |
| OTC | OPERATIONS | Operacoes OTC, compliance crypto |
| DELIVERY | OPERATIONS | Entregas clientes, projetos avulsos |
| PRODUCT | PRODUCT | Produtos tech (LexNotify, Hamza, etc.) |
| LIQUIDATION | PRODUCT | Venda de ativos (Fintech, Vrumm, VotoMap) |
| QUANT | PRODUCT | Estrategias quantitativas, P&D, IA |

---

## Epics (30 total)

### Epics Originais (KAN-4 a KAN-27)

| Key | Component | Nome |
|-----|-----------|------|
| KAN-4 | GOV | Regularizar PJ 24.409 |
| KAN-5 | GOV | Financeiro/Contabil PJ 57.435 |
| KAN-6 | OTC | OTC e KYT Compliance (Foxbit + Banco + Contratos) |
| KAN-7 | OTC | Intermediacao 1 BTC |
| KAN-10 | DELIVERY | Dev - SideWallet |
| KAN-11 | DELIVERY | Dev - BahiaGold |
| KAN-12 | DELIVERY | Dev - Avulsos (catch-all) |
| KAN-13 | PRODUCT | LexNotify AI (V1 -> Beta -> Prod) |
| KAN-14 | PRODUCT | Hamza Carbon (testnet -> mainnet/prod) |
| KAN-15 | PRODUCT | NexusP2P (conclusao V1) |
| KAN-16 | PRODUCT | InceptionPsi (validacao/pivot) |
| KAN-17 | PRODUCT | Shadpay (integracao PIX/crypto) |
| KAN-18 | LIQUIDATION | Venda APP Fintech |
| KAN-19 | LIQUIDATION | Venda Vrumm |
| KAN-20 | LIQUIDATION | Venda VotoMap |
| KAN-21 | QUANT | Pool de Liquidez Hyperliquid |
| KAN-22 | QUANT | Funding Rate Arbitrage |
| KAN-23 | QUANT | HLP Vault Allocation |
| KAN-24 | QUANT | Arb Stable/Spread |
| KAN-25 | QUANT | Nadaraya-Watson |
| KAN-26 | QUANT | kNN |
| KAN-27 | QUANT | MEV Quant Fund |

### Epics Adicionais (sessoes posteriores)

| Key | Component | Nome | Labels |
|-----|-----------|------|--------|
| KAN-129 | PRODUCT | MHX-Digital — Infra & Automacao Interna | infra, p2, repo_mhx_digital |
| KAN-130 | DELIVERY | lfg-adv — Entregas / Juridico | p3, repo_lfg_adv |
| KAN-131 | DELIVERY | x-golden — Cliente/Entrega | p3, repo_x_golden |
| KAN-138 | QUANT | Kahincorp-AI — P&D / IA | p3, repo_kahincorp_ai |
| **KAN-141** | **PRODUCT** | **OPERACAO — Realismo: Stack + Roadmap (MVP)** | **p1, infra** |
| **KAN-157** | **GOV** | **GOV — Tese de Poder & Patrimonio (MVP)** | **p1, legal** |

---

## Mapa Repositorio -> Epic

| Repositorio | Epic | Component |
|-------------|------|-----------|
| LexNotify | KAN-13 | PRODUCT |
| Hamza Carbon | KAN-14 | PRODUCT |
| NexusP2P | KAN-15 | PRODUCT |
| InceptionPsi | KAN-16 | PRODUCT |
| Shadpay | KAN-17 | PRODUCT |
| MHX-Digital | KAN-129 | PRODUCT |
| SideWallet | KAN-10 | DELIVERY |
| BahiaGold | KAN-11 | DELIVERY |
| Dev Avulsos (catch-all) | KAN-12 | DELIVERY |
| lfg-adv | KAN-130 | DELIVERY |
| x-golden | KAN-131 | DELIVERY |
| APP Fintech | KAN-18 | LIQUIDATION |
| Vrumm | KAN-19 | LIQUIDATION |
| VotoMap | KAN-20 | LIQUIDATION |
| Kahincorp-AI | KAN-138 | QUANT |
| Pool Liquidez | KAN-21 | QUANT |
| Funding Rate | KAN-22 | QUANT |
| HLP Vault | KAN-23 | QUANT |
| Arb Stable | KAN-24 | QUANT |
| Nadaraya-Watson | KAN-25 | QUANT |
| kNN | KAN-26 | QUANT |
| MEV Quant Fund | KAN-27 | QUANT |
| OTC Compliance | KAN-6 | OTC |
| Interm. 1BTC | KAN-7 | OTC |
| PJ 24.409 | KAN-4 | GOV |
| PJ 57.435 | KAN-5 | GOV |

Issue ancora de mapeamento: **KAN-128** (atualizado com mapa completo)

---

## Issues Criadas por Sessao

### Sessao 1: Estrutura base
- KAN-4 a KAN-27 — 24 Epics originais (todos com p2)

### Sessao 2: Kit de Controle + Sprint-0
- KAN-28 a KAN-99 — 72 tasks de kit (3 por epic: SOP, Backlog, Riscos)
- KAN-100 a KAN-126 — 27 tasks Sprint-0 (P1) para 4 epics prioritarios:
  - LexNotify (KAN-100..107)
  - Hamza (KAN-108..113)
  - OTC (KAN-114..119)
  - Fintech (KAN-120..126)

### Sessao 3: Git + Mapeamento
- KAN-127 — [GIT] Playbook Git<->Jira (P1)
- KAN-128 — [JIRA] Mapa Repo->Epic

### Sessao 4: Repos pendentes
- KAN-129 — Epic MHX-Digital
- KAN-130 — Epic lfg-adv
- KAN-131 — Epic x-golden
- KAN-132..137 — Kit tasks (SOP + Backlog) para KAN-129, 130, 131
- KAN-138 — Epic Kahincorp-AI
- KAN-139..140 — Kit tasks para KAN-138

### Sessao 5 (atual): Operacao + Poder
- **KAN-141** — Epic OPERACAO: Stack + Roadmap (PRODUCT, p1, infra)
- **KAN-142** — Task Stack Tecnologica (due 2026-02-20)
  - KAN-143 — Sub: padrao repositorio
  - KAN-144 — Sub: Supabase baseline
  - KAN-145 — Sub: Meta Cloud API
  - KAN-146 — Sub: CI/CD GitHub Actions
  - KAN-147 — Sub: Sentry + logs
  - KAN-148 — Sub: vault + backups + secrets
  - KAN-149 — Sub: Runbook deploy/rollback
  - KAN-150 — Sub: custos infra (R$0)
- **KAN-151** — Task Roadmap Atual (due 2026-02-21)
  - KAN-152 — Sub: tabela roadmap
  - KAN-153 — Sub: estagios atuais
  - KAN-154 — Sub: regra de corte
  - KAN-155 — Sub: WIP max 2
  - KAN-156 — Sub: rotina diaria 5 min
- **KAN-157** — Epic GOV: Tese de Poder (GOV, p1, legal)
- **KAN-158** — Task Tese 1 pagina (due 2026-02-20)
- **KAN-159** — Task Politica de Risco / kill-switch (due 2026-02-21)
- **KAN-160** — Task Compliance e Reputacao Bancaria (due 2026-02-24)

**Total projeto: ~160 issues (KAN-1 a KAN-160)**

---

## Contexto Estrategico Registrado no Jira

| Item | Valor |
|------|-------|
| Meta de caixa | R$150.000 em 3-4 entradas |
| Receitas prioritarias | OTC e Licitacao |
| Stack padrao | Supabase/Postgres + Auth + Meta Cloud API + GitHub Actions + Sentry + vault |
| Custos infra | R$0 (placeholder) |
| Kill-switch | 30% perda por estrategia E por mes |
| Risco aceito | 30-40% limite maximo |
| Alocacao quant | US$100/estrategia inicial |
| Alavancagem | Max 2x futuros, 1x spot |
| Limite societario | 49% maximo |
| WIP | Max 2 cards Doing por board por pessoa |
| Parcelas empresas | Dia 20 |
| Deps externas | Foxbit, contador, banco, parceiro comercial |
| Compliance OTC | >50k: contrato+KYT/KYC; 10-50k: simplificado; <10k: basico |
| Carnaval 2026 | Evitar prazos 16/02-18/02 |

---

## Due Dates Definidos

| Key | Task | Due Date |
|-----|------|----------|
| KAN-142 | Stack Tecnologica | 2026-02-20 (sex) |
| KAN-151 | Roadmap Atual | 2026-02-21 (sab) |
| KAN-158 | Tese de Poder | 2026-02-20 (sex) |
| KAN-159 | Politica de Risco | 2026-02-21 (sab) |
| KAN-160 | Compliance | 2026-02-24 (ter) |

Todos pos-Carnaval (16-18/02 evitado).

---

## Labels Padrao

| Label | Uso |
|-------|-----|
| p1 | Prioridade maxima (Sprint-0) |
| p2 | Prioridade media |
| p3 | Prioridade baixa |
| infra | Infraestrutura / DevOps |
| legal | Juridico / compliance |
| security | Seguranca |
| blocked | Bloqueado |
| waiting_partner | Esperando parceiro externo |
| waiting_client | Esperando cliente |
| repo_* | Vinculo com repositorio Git |

---

## Limpeza Realizada (Passo 3)

- KAN-1, KAN-2, KAN-3: receberam component **GOV** (estavam vazios)
- 4 orfaos identificados (sem parent epic): KAN-1, KAN-2, KAN-127, KAN-128
- Labels: todas dentro do padrao

---

## JQLs Uteis

```
-- P1 por board
project = KAN AND labels = p1 AND component in (PRODUCT, LIQUIDATION, QUANT) ORDER BY key ASC
project = KAN AND labels = p1 AND component in (GOV, OTC, DELIVERY) ORDER BY key ASC

-- Due dates
project = KAN AND duedate >= startOfWeek() AND duedate <= endOfWeek() ORDER BY duedate ASC
project = KAN AND duedate >= now() AND duedate <= 7d ORDER BY duedate ASC

-- Orfaos / problemas
project = KAN AND issuetype not in (Epic) AND parent is EMPTY ORDER BY key ASC
project = KAN AND component is EMPTY ORDER BY key ASC

-- Status
project = KAN AND labels in (blocked, waiting_partner, waiting_client) ORDER BY key ASC
project = KAN AND status = "Em andamento" ORDER BY priority DESC

-- Por tipo
project = KAN AND labels = infra ORDER BY key ASC
project = KAN AND labels = legal ORDER BY key ASC
project = KAN AND labels = security ORDER BY key ASC

-- Pessoal
project = KAN AND assignee = currentUser() AND status != "Concluido" ORDER BY priority DESC
project = KAN AND updated >= startOfDay() ORDER BY updated DESC
```

---

## Scripts Criados

| Arquivo | Funcao |
|---------|--------|
| `jira_executor.py` | Passos 1-3: padronizacao epics + kit controle (72 tasks) + Sprint-0 (27 tasks) |
| `jira_audit_v2.py` | Auditoria de consistencia (P1, components, parents) |
| `jira_passo234.py` | Git Playbook (KAN-127) + Repo Map (KAN-128) + JQL filters |
| `jira_repos_pendentes.py` | Resolver repos pendentes (KAN-129..131) |
| `jira_fix_kahincorp.py` | Corrigir Kahincorp-AI (KAN-138..140) |
| `jira_rank.py` | Ranquear P1 nos boards (limitacao team-managed) |
| `jira_operacao_poder.py` | Operacao + Alinhamento de Poder (KAN-141..160) |
| `gerar_auth_chatgpt.py` | Gerar base64 auth para ChatGPT Actions |
| `JIRA_OPENAPI_SCHEMA.yaml` | Schema OpenAPI 3.1.1 para ChatGPT Actions |
| `JIRA_INTEGRACAO_COMPLETA.md` | Documentacao de integracao (endpoints, auth, contrato) |
| `.env` | Credenciais Jira (NAO commitar) |

---

## Para Continuar

1. **Carregar .env** nos scripts futuros (ver padrao abaixo)
2. **Renovar token** antes de 2026-02-21
3. **Orfaos** KAN-127 e KAN-128: vincular a epic apropriado manualmente
4. **Board ranking**: reordenar manualmente (API nao funciona em team-managed)
5. **Colunas do board**: configurar manualmente (Backlog, Ready, Doing, Review, Done)

### Padrao para carregar .env nos scripts:

```python
import os
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()

BASE = os.getenv("JIRA_BASE_URL")
EMAIL = os.getenv("JIRA_EMAIL")
TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT = os.getenv("JIRA_PROJECT_KEY")
```

Ou sem dependencia externa:

```python
import os

def load_env(path=".env"):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

load_env()
BASE = os.environ["JIRA_BASE_URL"]
EMAIL = os.environ["JIRA_EMAIL"]
TOKEN = os.environ["JIRA_API_TOKEN"]
PROJECT = os.environ["JIRA_PROJECT_KEY"]
```
