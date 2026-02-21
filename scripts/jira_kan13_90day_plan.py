#!/usr/bin/env python3
"""
KAN-13 LexNotify — Plano 90 dias: atualiza Epic, edita filhas, cria novas issues.

Uso:  python scripts/jira_kan13_90day_plan.py
Modo: --dry-run  (mostra o que faria sem executar)

Requer: requests, python-dotenv
"""

import argparse
import os
import sys
import base64
import json
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERRO: pip install requests")
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ══════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════

def load_auth():
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)
    base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    if base and email and token:
        cred = base64.b64encode(f"{email}:{token}".encode()).decode()
        return base, {
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Atlassian-Token": "no-check",
        }
    sys.exit("ERRO: credenciais nao encontradas")


def _req(method, url, headers, retries=1, **kw):
    for i in range(retries + 1):
        try:
            r = requests.request(method, url, headers=headers, timeout=30, **kw)
            if r.status_code >= 500 and i < retries:
                time.sleep(1); continue
            return r
        except (requests.ConnectionError, requests.Timeout):
            if i < retries:
                time.sleep(1); continue
            raise
    return r


# ══════════════════════════════════════════════════════════════════════════
# ADF BUILDERS
# ══════════════════════════════════════════════════════════════════════════

def adf_text(t, marks=None):
    node = {"type": "text", "text": t}
    if marks:
        node["marks"] = marks
    return node

def adf_bold(t):
    return adf_text(t, [{"type": "strong"}])

def adf_para(*nodes):
    return {"type": "paragraph", "content": list(nodes)}

def adf_heading(level, t):
    return {"type": "heading", "attrs": {"level": level}, "content": [adf_text(t)]}

def adf_bullet(*items):
    """items = list of strings or list of content nodes."""
    li = []
    for item in items:
        if isinstance(item, str):
            li.append({"type": "listItem", "content": [adf_para(adf_text(item))]})
        else:
            li.append({"type": "listItem", "content": [adf_para(*item)]})
    return {"type": "bulletList", "content": li}

def adf_rule():
    return {"type": "rule"}

def adf_doc(*blocks):
    return {"version": 1, "type": "doc", "content": list(blocks)}


# ══════════════════════════════════════════════════════════════════════════
# KAN-13 — NOVA DESCRICAO (Epic 90 dias)
# ══════════════════════════════════════════════════════════════════════════

NEW_KAN13_SUMMARY = "LexNotify — Plano 90 dias (CRM + Inbox + IA)"

KAN13_DESCRIPTION = adf_doc(
    # ── Meta Comercial
    adf_heading(2, "Meta Comercial"),
    adf_para(adf_bold("Objetivo:"), adf_text(" 1 cliente pagando R$300/mes em ate 30 dias.")),
    adf_bullet(
        "Produto hoje: motor de notificacoes (upload Excel + regras + cron + WhatsApp via Evolution API)",
        "Nao existe: Billing, CRM/Kanban, Inbox/Chat, IA, multi-tenant",
        "Email e Telegram sao MOCK — nao contar com eles ate P1",
    ),
    adf_rule(),

    # ── Roadmap 30/60/90
    adf_heading(2, "Roadmap 30/60/90 dias"),

    adf_heading(3, "FASE 1 — Dias 1-30: Cliente Pagando (P0)"),
    adf_para(adf_bold("Entrega:"), adf_text(" CRM minimo + Kanban de audiencias + billing + onboarding 1 cliente.")),
    adf_bullet(
        "CRM Minimo: CRUD contatos vinculados a audiencias existentes",
        "Kanban Audiencias: board visual (prazos, status, proxima acao)",
        "Estabilizar WhatsApp: delivery rate > 95%, retry automatico, logs de falha",
        "Billing: checkout simples (PIX/Stripe) para R$300/mes",
        "Onboarding: fluxo guiado para o primeiro cliente",
        "Deploy producao estavel com rollback",
    ),

    adf_heading(3, "FASE 2 — Dias 31-60: Inbox Bidirecional (P1)"),
    adf_para(adf_bold("Entrega:"), adf_text(" WhatsApp bidirecional + historico no CRM.")),
    adf_bullet(
        "Webhook recebimento WhatsApp (Evolution API callback)",
        "Inbox: tela de conversas por contato",
        "Vincular mensagens <-> contatos <-> audiencias",
        "Upload documentos vinculados a audiencia/contato",
        "Testes integracao WhatsApp end-to-end",
    ),

    adf_heading(3, "FASE 3 — Dias 61-90: IA Draft (P2)"),
    adf_para(adf_bold("Entrega:"), adf_text(" Assistente IA sugere rascunho de resposta.")),
    adf_bullet(
        "LLM gera sugestao de resposta baseada em historico da conversa",
        "Templates inteligentes por tipo de audiencia",
        "Dashboard: metricas de envio, abertura, resposta",
        "SOP e documentacao operacional",
        "Automacoes de triagem (se sobrar tempo)",
    ),
    adf_rule(),

    # ── Escopo P0/P1/P2
    adf_heading(2, "Escopo por Prioridade"),
    adf_para(adf_bold("P0 (sem isso nao fatura):"), adf_text(" CRM, Kanban audiencias, WhatsApp estavel, billing, onboarding, deploy")),
    adf_para(adf_bold("P1 (diferencial):"), adf_text(" Inbox WhatsApp bidirecional, historico CRM, upload docs, testes e2e")),
    adf_para(adf_bold("P2 (aspiracional):"), adf_text(" IA draft, templates inteligentes, dashboard metricas, SOP, automacoes")),
    adf_rule(),

    # ── Metricas
    adf_heading(2, "Metricas de Sucesso"),
    adf_bullet(
        "Ativacao: cliente completa onboarding e envia 1a notificacao em < 15 min",
        "Retencao: cliente usa o sistema toda semana no primeiro mes",
        "Confiabilidade de envio: WhatsApp delivery rate > 95%",
        "Receita: R$300/mes recorrente ate dia 30",
        "Inbox (P1): tempo medio de resposta a mensagem recebida < 4h",
    ),
    adf_rule(),

    # ── Kill-switches
    adf_heading(2, "Kill-switches (quando parar e refocar)"),
    adf_bullet(
        "Dia 30 sem cliente pagando -> pausar TUDO, focar 100% em fechar venda",
        "WhatsApp delivery < 90% -> pausar Inbox (P1), focar em confiabilidade de envio",
        "Dia 60 sem Inbox funcional -> cancelar IA (P2), focar em Inbox ate funcionar",
        "Qualquer feature P2 so comeca se P0 e P1 estiverem estaveis ha 1 semana",
    ),
    adf_rule(),

    # ── DoD do Epic
    adf_heading(2, "Definition of Done (Epic)"),
    adf_bullet(
        "1 cliente ativo pagando R$300/mes",
        "CRM com contatos vinculados a audiencias",
        "WhatsApp bidirecional (envio + recebimento)",
        "Inbox funcional com historico",
        "IA draft em modo rascunho (pode ser beta)",
        "Deploy automatizado com rollback",
        "Zero dados de cliente expostos (auth + RLS Supabase)",
    ),
)


# ══════════════════════════════════════════════════════════════════════════
# ISSUES EXISTENTES — DECISOES
# ══════════════════════════════════════════════════════════════════════════

# Edicoes em issues existentes: (key, new_summary_or_None, new_labels, new_description_adf_or_None)
ISSUE_EDITS = [
    # --- P0: manter e ajustar ---
    {
        "key": "KAN-100",
        "summary": "[LexNotify P0] Migracao Supabase (auth + db + RLS)",
        "labels": ["p0", "infra"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Migrar backend para Supabase com auth, database e RLS configurados para o cliente.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Auth Supabase (email+senha) funcionando em producao",
                "Tabelas criadas: contatos, audiencias, notificacoes, regras",
                "RLS ativo: usuario so ve seus proprios dados",
                "Storage configurado para upload de documentos",
                "Seed script para dados de teste",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "Auth testado com 2 usuarios distintos",
                "RLS validado: usuario A nao ve dados de B",
                "Migration scripts versionados no repo",
            ),
        ),
    },
    {
        "key": "KAN-101",
        "summary": "[LexNotify P0] WhatsApp — estabilizar envio (delivery > 95%)",
        "labels": ["p0"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Garantir que o envio de WhatsApp via Evolution API seja confiavel (>95% delivery rate).")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Retry automatico em falha de envio (max 3 tentativas com backoff)",
                "Log estruturado: enviado/falha/retry por notificacao",
                "Alerta quando delivery rate cai abaixo de 90% (log ou webhook)",
                "Timeout configuravel por envio",
                "Health-check da conexao Evolution API a cada 5 min",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "100 envios de teste com delivery rate medido",
                "Dashboard ou query que mostra taxa de sucesso ultimas 24h",
                "Documentacao do fluxo de retry",
            ),
        ),
    },
    {
        "key": "KAN-102",
        "summary": "[LexNotify P0] Kanban de Audiencias (board visual + prazos)",
        "labels": ["p0"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Board visual para acompanhar audiencias com prazos e proxima acao.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Board com colunas: Pendente | Em andamento | Aguardando | Concluida",
                "Card mostra: nome audiencia, prazo, contato vinculado, proxima acao",
                "Drag-and-drop para mudar status",
                "Filtro por prazo (vencendo essa semana / atrasadas)",
                "Dados vem das audiencias ja existentes (upload Excel)",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "Board renderiza com dados reais do Supabase",
                "Transicao de status persiste no banco",
                "Funciona em mobile (responsivo basico)",
            ),
        ),
    },
    {
        "key": "KAN-106",
        "summary": "[LexNotify P0] Deploy producao + rollback + runbook",
        "labels": ["p0", "infra"],
        "description": None,  # manter descricao atual
    },
    {
        "key": "KAN-107",
        "summary": "[LexNotify P0] Onboarding — fluxo primeiro cliente",
        "labels": ["p0"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Fluxo guiado para o primeiro cliente: do cadastro ao primeiro envio de notificacao.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Wizard: criar conta -> importar audiencias (Excel) -> criar regra -> enviar teste",
                "Checklist visual de progresso (4 etapas)",
                "Mensagem de boas-vindas via WhatsApp ao completar onboarding",
                "Tempo total do fluxo < 15 min",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "Testado end-to-end com dados reais de 1 cliente",
                "Fluxo documentado (screenshots ou video curto)",
            ),
        ),
    },

    # --- P1: mover para fase 2 ---
    {
        "key": "KAN-103",
        "summary": "[LexNotify P1] Upload documentos vinculados a audiencia/contato",
        "labels": ["p1"],
        "description": None,
    },
    {
        "key": "KAN-105",
        "summary": "[LexNotify P1] Testes integracao (WhatsApp e2e + CRM)",
        "labels": ["p1"],
        "description": None,
    },

    # --- P2: backlog / mover para fase 3 ---
    {
        "key": "KAN-104",
        "summary": "[LexNotify P2] Automacoes triagem (regras + routing)",
        "labels": ["p2"],
        "description": None,
    },
    {
        "key": "KAN-55",
        "summary": "[LexNotify P2] SOP + DoR/DoD + Checklists",
        "labels": ["p2"],
        "description": None,
    },
    {
        "key": "KAN-57",
        "summary": "[LexNotify P2] Riscos & Dependencias",
        "labels": ["p2"],
        "description": None,
    },

    # --- FECHAR: substituido pelo plano 90 dias ---
    {
        "key": "KAN-56",
        "summary": "[LexNotify] Backlog inicial — SUBSTITUIDO pelo plano 90 dias",
        "labels": ["p3"],
        "description": adf_doc(
            adf_para(adf_bold("Issue substituida."),
                     adf_text(" O backlog agora esta no plano de 90 dias do Epic KAN-13.")),
        ),
    },
]


# ══════════════════════════════════════════════════════════════════════════
# NOVAS ISSUES A CRIAR
# ══════════════════════════════════════════════════════════════════════════

NEW_ISSUES = [
    {
        "summary": "[LexNotify P0] CRM Minimo — CRUD contatos vinculados a audiencias",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p0"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Modulo CRM minimo: cadastrar, editar e listar contatos, vinculando-os as audiencias importadas via Excel.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "CRUD completo de contatos (nome, telefone, email, notas)",
                "Vinculacao contato <-> audiencia (1 contato pode ter N audiencias)",
                "Listagem com busca por nome/telefone",
                "Importacao automatica de contatos a partir do Excel de audiencias",
                "Dados persistem no Supabase com RLS por usuario",
                "Tela responsiva (desktop + mobile basico)",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "CRUD testado com 50+ contatos",
                "Vinculacao audiencia <-> contato funciona para dados importados",
                "RLS validado: usuario A nao ve contatos de B",
                "Sem regressao no fluxo de notificacoes existente",
            ),
        ),
    },
    {
        "summary": "[LexNotify P0] Billing Minimo — checkout R$300/mes (PIX ou Stripe)",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p0"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Implementar cobranca recorrente minima para o primeiro cliente.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Pagina de checkout com plano unico: R$300/mes",
                "Suporte a PIX (preferencial) ou Stripe",
                "Webhook confirma pagamento e ativa conta",
                "Status da assinatura visivel no painel do usuario",
                "Bloqueio de funcionalidades se assinatura vencida (grace period 7 dias)",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "Fluxo testado end-to-end (pagamento -> ativacao)",
                "Webhook de confirmacao funciona em producao",
                "Grace period implementado e testado",
            ),
        ),
    },
    {
        "summary": "[LexNotify P1] Webhook WhatsApp — recebimento de mensagens",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p1"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Receber mensagens WhatsApp via webhook da Evolution API e persistir no banco.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Endpoint webhook recebe callback da Evolution API",
                "Mensagem recebida salva no Supabase (remetente, conteudo, timestamp)",
                "Vinculacao automatica ao contato CRM pelo numero de telefone",
                "Tratamento de duplicatas (idempotente por messageId)",
                "Log de mensagens recebidas acessivel via API",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "10+ mensagens recebidas e persistidas corretamente em teste",
                "Vinculacao contato funciona para numeros conhecidos",
                "Mensagem de numero desconhecido cria contato provisorio",
            ),
        ),
    },
    {
        "summary": "[LexNotify P1] Inbox WhatsApp — tela de conversas por contato",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p1"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Tela de inbox que exibe conversas WhatsApp organizadas por contato, com historico.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Lista de conversas ordenada por ultima mensagem",
                "Tela de conversa mostra historico (enviadas + recebidas)",
                "Campo para enviar nova mensagem diretamente da inbox",
                "Badge de mensagens nao lidas",
                "Filtro: todas / nao lidas / por contato",
                "Vinculo visivel: contato + audiencias associadas",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "Inbox funciona com 5+ conversas simultaneas",
                "Envio pela inbox entrega via Evolution API",
                "Real-time ou polling a cada 30s para novas mensagens",
                "Responsivo (desktop + mobile)",
            ),
        ),
    },
    {
        "summary": "[LexNotify P2] IA Draft — sugestao de resposta por LLM",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p2"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Assistente IA que sugere rascunho de resposta baseado no historico da conversa e tipo de audiencia.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Botao 'Sugerir resposta' na inbox gera draft via LLM",
                "Contexto enviado ao LLM: ultimas 10 mensagens + tipo de audiencia",
                "Usuario pode editar o draft antes de enviar",
                "Fallback se LLM falhar: campo vazio com mensagem de erro",
                "Rate limit: max 20 sugestoes/hora por usuario",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "Draft gerado em < 5 segundos para 90% dos requests",
                "Qualidade avaliada manualmente em 10 conversas reais",
                "Custo por sugestao documentado (tokens/R$)",
                "Feature flag para desabilitar sem deploy",
            ),
        ),
    },
    {
        "summary": "[LexNotify P2] Dashboard — metricas envio, abertura, resposta",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p2"],
        "description": adf_doc(
            adf_heading(3, "Objetivo"),
            adf_para(adf_text("Dashboard com metricas operacionais do LexNotify.")),
            adf_heading(3, "Criterios de Aceite"),
            adf_bullet(
                "Metricas: total enviado, entregue, falha, taxa de resposta (inbox)",
                "Filtro por periodo (7d, 30d, custom)",
                "Grafico de linha: volume de envios por dia",
                "Alerta visual se delivery rate < 90%",
            ),
            adf_heading(3, "DoD"),
            adf_bullet(
                "Dashboard carrega em < 3 segundos",
                "Dados consistentes com logs de envio",
                "Funciona com 30+ dias de historico",
            ),
        ),
    },
]


# ══════════════════════════════════════════════════════════════════════════
# EXECUCAO
# ══════════════════════════════════════════════════════════════════════════

def get_component_id(base, headers, name):
    r = _req("GET", f"{base}/rest/api/3/project/KAN/components", headers)
    r.raise_for_status()
    for c in r.json():
        if c["name"].strip().lower() == name.strip().lower():
            return c["id"]
    return None


def get_status(base, headers, key):
    r = _req("GET", f"{base}/rest/api/3/issue/{key}?fields=status,summary", headers)
    r.raise_for_status()
    f = r.json()["fields"]
    return f["status"]["name"], f["summary"]


def transition_to(base, headers, key, target):
    """Retorna (ok, status_depois, msg)."""
    status_antes, _ = get_status(base, headers, key)
    if status_antes.strip().lower() == target.strip().lower():
        return True, status_antes, "ja estava"

    r = _req("GET", f"{base}/rest/api/3/issue/{key}/transitions", headers)
    r.raise_for_status()
    tid = None
    for t in r.json().get("transitions", []):
        if t["name"].strip().lower() == target.strip().lower():
            tid = t["id"]; break
    if not tid:
        return False, status_antes, "transicao nao disponivel"

    r2 = _req("POST", f"{base}/rest/api/3/issue/{key}/transitions", headers,
              json={"transition": {"id": tid}})
    if r2.status_code == 204:
        st, _ = get_status(base, headers, key)
        return True, st, "transicao executada"
    return False, status_antes, f"HTTP {r2.status_code}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que faria sem executar")
    args = parser.parse_args()
    dry = args.dry_run

    base, headers = load_auth()
    results = []  # (key, summary, antes, depois, flag, msg)

    print(f"{'[DRY-RUN] ' if dry else ''}KAN-13 LexNotify — Plano 90 dias")
    print(f"Jira: {base}")
    print("=" * 90)

    # ── 1) Atualizar Epic KAN-13 ──────────────────────────────────────
    print("\n[1/4] Atualizando Epic KAN-13...")
    if not dry:
        payload = {
            "fields": {
                "summary": NEW_KAN13_SUMMARY,
                "description": KAN13_DESCRIPTION,
            }
        }
        r = _req("PUT", f"{base}/rest/api/3/issue/KAN-13", headers, json=payload)
        if r.status_code == 204:
            print("  [OK] Summary + description atualizados")
            results.append(("KAN-13", NEW_KAN13_SUMMARY, "-", "-", "OK", "epic atualizado"))
        else:
            print(f"  [!!] HTTP {r.status_code}: {r.text[:200]}")
            results.append(("KAN-13", NEW_KAN13_SUMMARY, "-", "-", "ERRO", f"HTTP {r.status_code}"))
    else:
        print(f"  Novo summary: {NEW_KAN13_SUMMARY}")
        results.append(("KAN-13", NEW_KAN13_SUMMARY, "-", "-", "DRY", "dry-run"))

    # ── 2) Editar issues existentes ───────────────────────────────────
    print(f"\n[2/4] Editando {len(ISSUE_EDITS)} issues existentes...")
    for edit in ISSUE_EDITS:
        key = edit["key"]
        fields = {}
        if edit.get("summary"):
            fields["summary"] = edit["summary"]
        if edit.get("labels") is not None:
            fields["labels"] = edit["labels"]
        if edit.get("description"):
            fields["description"] = edit["description"]

        if not dry:
            r = _req("PUT", f"{base}/rest/api/3/issue/{key}", headers, json={"fields": fields})
            if r.status_code == 204:
                print(f"  [OK] {key}: editado")
                results.append((key, edit.get("summary", "?"), "-", "-", "OK", "editado"))
            else:
                print(f"  [!!] {key}: HTTP {r.status_code}: {r.text[:150]}")
                results.append((key, edit.get("summary", "?"), "-", "-", "ERRO", f"HTTP {r.status_code}"))
        else:
            print(f"  [DRY] {key}: {edit.get('summary', '(sem mudanca)')}")
            results.append((key, edit.get("summary", "?"), "-", "-", "DRY", "dry-run"))

    # ── 3) Criar novas issues ─────────────────────────────────────────
    print(f"\n[3/4] Criando {len(NEW_ISSUES)} novas issues...")
    new_keys = []
    for issue in NEW_ISSUES:
        fields = {
            "project": {"key": "KAN"},
            "summary": issue["summary"],
            "issuetype": issue["issuetype"],
            "parent": issue["parent"],
            "labels": issue["labels"],
        }
        if issue.get("description"):
            fields["description"] = issue["description"]

        if not dry:
            r = _req("POST", f"{base}/rest/api/3/issue", headers, json={"fields": fields})
            if r.status_code in (200, 201):
                new_key = r.json()["key"]
                new_keys.append(new_key)
                print(f"  [OK] {new_key}: {issue['summary']}")
                results.append((new_key, issue["summary"], "-", "A fazer", "OK", "criada"))
            else:
                print(f"  [!!] ERRO ao criar '{issue['summary'][:40]}': HTTP {r.status_code}: {r.text[:200]}")
                results.append(("???", issue["summary"], "-", "-", "ERRO", f"HTTP {r.status_code}"))
        else:
            print(f"  [DRY] Nova: {issue['summary']}")
            results.append(("NEW", issue["summary"], "-", "-", "DRY", "dry-run"))

    # ── 4) Mover P0 para "Em andamento" ──────────────────────────────
    p0_keys = ["KAN-100", "KAN-101", "KAN-102", "KAN-106", "KAN-107"] + [
        k for k in new_keys if any(ni["labels"] == ["p0"] and ni["summary"] in
            [r[1] for r in results if r[0] == k] for ni in NEW_ISSUES)
    ]
    # Simpler: move all P0 (existing edits + new issues with p0 label)
    p0_existing = [e["key"] for e in ISSUE_EDITS if "p0" in e.get("labels", [])]
    p0_new = [new_keys[i] for i, ni in enumerate(NEW_ISSUES)
              if "p0" in ni.get("labels", []) and i < len(new_keys)]
    all_p0 = p0_existing + p0_new

    print(f"\n[4/4] Movendo {len(all_p0)} issues P0 para 'Em andamento'...")
    for key in all_p0:
        if not dry:
            ok, st_depois, msg = transition_to(base, headers, key, "Em andamento")
            flag = "OK" if ok else "ERRO"
            print(f"  [{flag}] {key}: {msg}")
            # Atualiza resultado existente
            for i, r in enumerate(results):
                if r[0] == key:
                    results[i] = (key, r[1], r[2] if r[2] != "-" else "A fazer", st_depois, flag, f"{r[5]} + {msg}")
                    break
        else:
            print(f"  [DRY] {key}: -> Em andamento")

    # ── Resumo ────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("RESUMO FINAL")
    print("=" * 90)
    hdr = f"{'Key':<10} {'Summary':<50} {'Flag':<5} Msg"
    print(hdr)
    print("-" * len(hdr))
    for key, summ, antes, depois, flag, msg in results:
        s = (summ[:48] + "..") if len(summ) > 50 else summ
        print(f"{key:<10} {s:<50} {flag:<5} {msg}")

    ok_count = sum(1 for r in results if r[4] in ("OK", "DRY"))
    print(f"\n{ok_count}/{len(results)} OK.")


if __name__ == "__main__":
    main()
