#!/usr/bin/env python3
"""
KAN-13 LexNotify v2 — Atualiza Epic com estado real (Billing DONE) + plano 90 dias.

Acoes:
  1) Reescreve KAN-13 (summary + description)
  2) Marca KAN-163 (Billing) como Concluido
  3) Edita issues existentes (prioridade, descricao, labels)
  4) Cria novas issues (Case View, Notificacao Manual)
  5) Deleta KAN-56 (substituido)
  6) Move P0 para Em andamento

Uso:
  python scripts/jira_kan13_v2_update.py
  python scripts/jira_kan13_v2_update.py --dry-run

Requer: requests, python-dotenv
"""

import argparse
import os
import sys
import base64
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
# AUTH + HTTP
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
            if i < retries: time.sleep(1); continue
            raise
    return r


# ══════════════════════════════════════════════════════════════════════════
# ADF HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _t(text, marks=None):
    n = {"type": "text", "text": text}
    if marks: n["marks"] = marks
    return n

def _b(text): return _t(text, [{"type": "strong"}])
def _em(text): return _t(text, [{"type": "em"}])
def _strike(text): return _t(text, [{"type": "strike"}])

def _p(*nodes): return {"type": "paragraph", "content": list(nodes)}
def _h(level, text): return {"type": "heading", "attrs": {"level": level}, "content": [_t(text)]}
def _rule(): return {"type": "rule"}

def _bullet(*items):
    li = []
    for item in items:
        if isinstance(item, str):
            li.append({"type": "listItem", "content": [_p(_t(item))]})
        else:
            li.append({"type": "listItem", "content": [_p(*item)]})
    return {"type": "bulletList", "content": li}

def _status_badge(text, color="neutral"):
    """Inline status lozenge via ADF."""
    return {"type": "status", "attrs": {"text": text, "color": color}}

def _doc(*blocks):
    return {"version": 1, "type": "doc", "content": list(blocks)}


# ══════════════════════════════════════════════════════════════════════════
# 1) KAN-13 EPIC — NOVA DESCRICAO
# ══════════════════════════════════════════════════════════════════════════

NEW_SUMMARY = "LexNotify — 90 dias: CRM/Kanban -> Inbox -> IA"

EPIC_DESC = _doc(
    _h(2, "Estado Atual (confirmado em codigo)"),
    _bullet(
        [_b("PRONTO:"), _t(" Billing Stripe (checkout, webhook, portal, status)")],
        [_b("PRONTO:"), _t(" Seguranca (CRON_SECRET fix, build/lint OK)")],
        [_b("PRONTO:"), _t(" Legal (termos + privacidade com secao pagamentos)")],
        [_b("PRONTO:"), _t(" Motor de notificacoes (upload Excel + regras + cron + WhatsApp outbound)")],
        [_b("MOCK:"), _t(" Email e Telegram (nao funcional)")],
        [_b("NAO EXISTE:"), _t(" CRM, Kanban, Inbox/Chat, IA, multi-tenant")],
        [_b("EXPERIMENTAL:"), _t(" adv-msg (FastAPI+Selenium) — nao e base do produto")],
    ),
    _rule(),

    _h(2, "Meta Comercial"),
    _p(_b("D+30:"), _t(" 1 cliente pagando R$300/mes com CRM + Kanban funcionais.")),
    _p(_b("D+60:"), _t(" Inbox WhatsApp bidirecional (beta).")),
    _p(_b("D+90:"), _t(" IA draft de respostas + dashboard metricas.")),
    _rule(),

    _h(2, "Roadmap 30/60/90"),

    _h(3, "FASE 1 — D+0 a D+30: Cliente Pagando (P0)"),
    _p(_em("Entrega: CRM + Kanban audiencias + onboarding + deploy prod.")),
    _bullet(
        [_strike("Billing Stripe"), _t(" — JA IMPLEMENTADO (KAN-163 concluida)")],
        [_strike("Seguranca + Legal"), _t(" — JA FEITO")],
        "CRM Core: CRUD contatos vinculados a audiencias (KAN-162)",
        "Kanban Audiencias: board visual com prazos e status (KAN-102)",
        "Case View: tela unificada audiencia + regras + logs + contato (NOVA)",
        "WhatsApp outbound: estabilizar delivery > 95% (KAN-101)",
        "Supabase: finalizar RLS + migrations (KAN-100)",
        "Deploy producao + rollback (KAN-106)",
        "Onboarding primeiro cliente (KAN-107)",
    ),

    _h(3, "FASE 2 — D+31 a D+60: Inbox WhatsApp (P1)"),
    _p(_em("Entrega: WhatsApp bidirecional com historico no CRM.")),
    _bullet(
        "Webhook recebimento Evolution API (KAN-164)",
        "Inbox: tela conversas por contato (KAN-165)",
        "Notificacao manual: envio WhatsApp ad-hoc pela UI (NOVA)",
        "Testes integracao e2e (KAN-105)",
    ),

    _h(3, "FASE 3 — D+61 a D+90: IA Draft + Polish (P2)"),
    _p(_em("Entrega: assistente IA + dashboard + documentacao.")),
    _bullet(
        "IA Draft: sugestao de resposta por LLM (KAN-166)",
        "Dashboard: metricas envio/resposta (KAN-167)",
        "Automacoes triagem (KAN-104) — so se P0+P1 estaveis",
        "Upload docs vinculados (KAN-103) — postergado de P1",
        "SOP + Riscos (KAN-55, KAN-57)",
    ),
    _rule(),

    _h(2, "Metricas de Sucesso"),
    _bullet(
        "Ativacao: cliente completa onboarding e envia 1a notificacao em < 15 min",
        "Retencao: cliente usa sistema toda semana no 1o mes",
        "Confiabilidade: WhatsApp delivery rate > 95%",
        "Receita: R$300/mes recorrente ate D+30",
        "Inbox (P1): tempo medio resposta a msg recebida < 4h",
    ),
    _rule(),

    _h(2, "Kill-switches"),
    _bullet(
        "D+30 sem cliente pagando -> pausar TUDO, focar 100% em fechar venda/onboarding",
        "WhatsApp delivery < 90% -> pausar Inbox (P1), focar em confiabilidade outbound",
        "D+60 sem Inbox funcional -> cancelar IA (P2), entregar Inbox primeiro",
        "Feature P2 so comeca se P0 e P1 estaveis ha 1+ semana",
        "adv-msg (Selenium) NAO e base — se precisar de WhatsApp Web, usar apenas como fallback temporario",
    ),
    _rule(),

    _h(2, "Definition of Done (Epic)"),
    _bullet(
        "1 cliente ativo pagando R$300/mes via Stripe",
        "CRM com contatos vinculados a audiencias",
        "Kanban visual de audiencias com prazos",
        "WhatsApp bidirecional (envio + recebimento)",
        "Inbox funcional com historico",
        "IA draft em modo beta (pode ser experimental)",
        "Deploy automatizado com rollback",
        "Zero dados de cliente expostos (auth + RLS Supabase)",
    ),
)


# ══════════════════════════════════════════════════════════════════════════
# 2) EDICOES EM ISSUES EXISTENTES
# ══════════════════════════════════════════════════════════════════════════

EDITS = [
    # --- KAN-163: Billing -> CONCLUIDO ---
    {
        "key": "KAN-163",
        "summary": "[LexNotify] Billing Stripe — CONCLUIDO",
        "labels": ["p0", "done"],
        "transition_to": "Concluido",
        "description": _doc(
            _h(3, "Status: CONCLUIDO"),
            _p(_t("Billing Stripe implementado e funcional.")),
            _h(3, "O que foi entregue"),
            _bullet(
                "Migrations + tabelas subscriptions/subscription_events",
                "POST /api/billing/checkout — cria sessao Stripe",
                "POST /api/billing/webhook — recebe eventos Stripe",
                "GET /api/billing/portal — redirect para portal do cliente",
                "GET /api/billing/status — verifica status da assinatura",
                "Trial-expired com CTA para checkout",
                "Dashboard verifica assinatura quando trial expira",
            ),
        ),
    },

    # --- KAN-100: Supabase — refinar escopo ---
    {
        "key": "KAN-100",
        "summary": "[LexNotify P0] Supabase — finalizar RLS + migrations",
        "labels": ["infra", "p0"],
        "description": _doc(
            _h(3, "Objetivo"),
            _p(_t("Auth e DB ja funcionam. Falta: RLS por usuario, migration scripts versionados, storage para docs futuros.")),
            _h(3, "Criterios de Aceite"),
            _bullet(
                "RLS ativo em TODAS as tabelas com dados de usuario",
                "Usuario A nao consegue ler/escrever dados de usuario B",
                "Migration scripts no repo (up + down)",
                "Storage bucket configurado para uploads futuros",
                "Seed script para dados de teste/demo",
            ),
            _h(3, "DoD"),
            _bullet(
                "RLS testado com 2+ usuarios distintos",
                "Migrations rodam do zero (fresh install) sem erro",
                "Documentado no README como rodar migrations",
            ),
        ),
    },

    # --- KAN-101: WhatsApp OUTBOUND only ---
    {
        "key": "KAN-101",
        "summary": "[LexNotify P0] WhatsApp outbound — delivery > 95% + retry",
        "labels": ["p0"],
        "description": _doc(
            _h(3, "Objetivo"),
            _p(_t("Estabilizar envio WhatsApp outbound via Evolution API. NAO inclui recebimento (isso e P1 KAN-164).")),
            _h(3, "Criterios de Aceite"),
            _bullet(
                "Retry automatico em falha (max 3x com backoff exponencial)",
                "Log estruturado por notificacao: enviado/falha/retry/desistiu",
                "Alerta quando delivery rate < 90% (log + webhook opcional)",
                "Timeout configuravel por envio",
                "Health-check Evolution API a cada 5 min",
                "Queue: notificacoes enfileiradas, nao disparam todas ao mesmo tempo",
            ),
            _h(3, "DoD"),
            _bullet(
                "50+ envios de teste com delivery rate medido e > 95%",
                "Query/endpoint que mostra taxa de sucesso ultimas 24h",
                "adv-msg (Selenium) NAO e usado — somente Evolution API",
            ),
        ),
    },

    # --- KAN-102: Kanban — manter, refinar desc ---
    {
        "key": "KAN-102",
        "summary": "[LexNotify P0] Kanban de Audiencias — board visual + prazos",
        "labels": ["p0"],
        "description": _doc(
            _h(3, "Objetivo"),
            _p(_t("Board visual estilo kanban para acompanhar audiencias com prazos e proxima acao.")),
            _h(3, "Criterios de Aceite"),
            _bullet(
                "Colunas: Pendente | Em preparo | Aguardando | Concluida",
                "Card mostra: nome audiencia, prazo, contato vinculado, proxima acao",
                "Drag-and-drop para mudar status (ou botoes de transicao)",
                "Filtro por: vencendo essa semana / atrasadas / por contato",
                "Dados alimentados pelas audiencias existentes (upload Excel)",
                "Integracao CRM: clicar no contato abre ficha (KAN-162)",
            ),
            _h(3, "DoD"),
            _bullet(
                "Board renderiza com dados reais do Supabase",
                "Transicao de status persiste no banco",
                "Responsivo basico (desktop + tablet)",
            ),
        ),
    },

    # --- KAN-162: CRM — refinar com contexto de audiencias ---
    {
        "key": "KAN-162",
        "summary": "[LexNotify P0] CRM Core — contatos + vinculo audiencias + historico",
        "labels": ["p0"],
        "description": _doc(
            _h(3, "Objetivo"),
            _p(_t("Modulo CRM: cadastrar/editar contatos e vincular a audiencias. Base para tudo (kanban, inbox, IA).")),
            _h(3, "Criterios de Aceite"),
            _bullet(
                "CRUD contatos: nome, telefone(s), email, OAB, notas",
                "Vinculacao contato <-> audiencia (N:N)",
                "Importacao automatica de contatos a partir do Excel de audiencias",
                "Listagem com busca por nome/telefone/OAB",
                "Ficha do contato: dados + audiencias vinculadas + historico de notificacoes enviadas",
                "Dados no Supabase com RLS por usuario",
            ),
            _h(3, "DoD"),
            _bullet(
                "CRUD testado com 30+ contatos",
                "Vinculacao audiencia <-> contato funcional",
                "Historico de notificacoes visivel na ficha",
                "Sem regressao no fluxo de notificacoes existente",
            ),
        ),
    },

    # --- KAN-106: Deploy — manter ---
    {
        "key": "KAN-106",
        "summary": "[LexNotify P0] Deploy producao + rollback + runbook",
        "labels": ["infra", "p0"],
        "description": None,  # manter descricao atual
    },

    # --- KAN-107: Onboarding — refinar ---
    {
        "key": "KAN-107",
        "summary": "[LexNotify P0] Onboarding — fluxo 1o cliente (< 15 min)",
        "labels": ["p0"],
        "description": _doc(
            _h(3, "Objetivo"),
            _p(_t("Fluxo guiado do cadastro ao primeiro envio. Cliente deve estar operacional em < 15 min.")),
            _h(3, "Criterios de Aceite"),
            _bullet(
                "Wizard: criar conta -> Stripe checkout -> importar audiencias -> criar contato -> enviar teste WA",
                "Checklist visual de progresso (5 etapas)",
                "Se Stripe ja pago (trial->paid), pular etapa de billing",
                "Mensagem de boas-vindas WhatsApp ao completar",
                "Fluxo < 15 min para usuario nao-tecnico",
            ),
            _h(3, "DoD"),
            _bullet(
                "Testado end-to-end com dados de 1 cliente real",
                "Fluxo documentado (screenshots no README)",
            ),
        ),
    },

    # --- P1: ajustes ---
    {
        "key": "KAN-164",
        "summary": "[LexNotify P1] Webhook WhatsApp — recebimento mensagens",
        "labels": ["p1"],
        "description": None,
    },
    {
        "key": "KAN-165",
        "summary": "[LexNotify P1] Inbox WhatsApp — conversas por contato",
        "labels": ["p1"],
        "description": None,
    },
    {
        "key": "KAN-105",
        "summary": "[LexNotify P1] Testes e2e (WhatsApp + CRM + Kanban)",
        "labels": ["p1"],
        "description": None,
    },

    # --- P2: postergar ---
    {
        "key": "KAN-103",
        "summary": "[LexNotify P2] Upload docs vinculados a audiencia/contato",
        "labels": ["p2"],
        "duedate": "2026-05-19",
        "description": None,
    },
    {
        "key": "KAN-104",
        "summary": "[LexNotify P2] Automacoes triagem (routing + regras)",
        "labels": ["p2"],
        "description": None,
    },
    {
        "key": "KAN-55",
        "summary": "[LexNotify P2] SOP + DoR/DoD operacional",
        "labels": ["p2"],
        "description": None,
    },
    {
        "key": "KAN-57",
        "summary": "[LexNotify P2] Riscos & Dependencias",
        "labels": ["p2"],
        "description": None,
    },
    {
        "key": "KAN-166",
        "summary": "[LexNotify P2] IA Draft — sugestao resposta por LLM",
        "labels": ["p2"],
        "description": None,
    },
    {
        "key": "KAN-167",
        "summary": "[LexNotify P2] Dashboard — metricas envio/resposta",
        "labels": ["p2"],
        "description": None,
    },
]


# ══════════════════════════════════════════════════════════════════════════
# 3) NOVAS ISSUES
# ══════════════════════════════════════════════════════════════════════════

NEW_ISSUES = [
    {
        "summary": "[LexNotify P0] Case View — tela unificada da audiencia",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p0"],
        "duedate": "2026-03-20",
        "description": _doc(
            _h(3, "Objetivo"),
            _p(_t("Tela principal do advogado: visao unificada de uma audiencia com tudo que ele precisa num so lugar.")),
            _h(3, "Criterios de Aceite"),
            _bullet(
                "Header: nome da audiencia, prazo, status (do kanban), vara/tribunal",
                "Secao Contato: dados do contato vinculado (do CRM), com link para ficha",
                "Secao Regras: regras de notificacao ativas para essa audiencia",
                "Secao Historico: log de notificacoes enviadas (data, canal, status entrega)",
                "Secao Notas: campo de texto livre para anotacoes do advogado",
                "Acao rapida: botao 'Enviar notificacao agora' (dispara WhatsApp ad-hoc)",
                "Dados carregados do Supabase com RLS",
            ),
            _h(3, "DoD"),
            _bullet(
                "Tela funciona com dados reais de audiencia importada",
                "Historico mostra notificacoes reais (enviadas pelo cron)",
                "Responsivo (desktop + mobile basico)",
                "Navegacao: Kanban -> clique no card -> Case View",
            ),
        ),
    },
    {
        "summary": "[LexNotify P1] Notificacao Manual — envio WhatsApp ad-hoc pela UI",
        "issuetype": {"name": "Tarefa"},
        "parent": {"key": "KAN-13"},
        "labels": ["p1"],
        "duedate": "2026-04-19",
        "description": _doc(
            _h(3, "Objetivo"),
            _p(_t("Permitir envio manual de WhatsApp pela UI (fora do cron), direto do Case View ou da ficha do contato.")),
            _h(3, "Criterios de Aceite"),
            _bullet(
                "Botao 'Enviar mensagem' no Case View e na ficha do contato",
                "Modal: selecionar template ou digitar mensagem livre",
                "Preview da mensagem antes de enviar",
                "Envio via Evolution API (mesmo pipeline do cron)",
                "Log da mensagem manual no historico do contato/audiencia",
                "Rate limit: max 30 msgs manuais/hora por usuario",
            ),
            _h(3, "DoD"),
            _bullet(
                "Envio manual testado com 10+ mensagens",
                "Mensagem aparece no historico do Case View",
                "Nao interfere no cron (mensagens manuais sao separadas)",
            ),
        ),
    },
]


# ══════════════════════════════════════════════════════════════════════════
# ISSUE A DELETAR
# ══════════════════════════════════════════════════════════════════════════

DELETE_KEYS = ["KAN-56"]  # Backlog substituido


# ══════════════════════════════════════════════════════════════════════════
# TRANSITION HELPER
# ══════════════════════════════════════════════════════════════════════════

def transition_to(base, headers, key, target):
    # Verificar status atual
    r = _req("GET", f"{base}/rest/api/3/issue/{key}?fields=status", headers)
    r.raise_for_status()
    current = r.json()["fields"]["status"]["name"]
    if current.strip().lower() == target.strip().lower():
        return True, current, "ja estava"

    # Buscar transicao
    r2 = _req("GET", f"{base}/rest/api/3/issue/{key}/transitions", headers)
    r2.raise_for_status()
    tid = None
    for t in r2.json().get("transitions", []):
        if t["name"].strip().lower() == target.strip().lower():
            tid = t["id"]; break
    if not tid:
        avail = [t["name"] for t in r2.json().get("transitions", [])]
        return False, current, f"transicao '{target}' nao disponivel. Disponiveis: {avail}"

    r3 = _req("POST", f"{base}/rest/api/3/issue/{key}/transitions", headers,
              json={"transition": {"id": tid}})
    if r3.status_code == 204:
        r4 = _req("GET", f"{base}/rest/api/3/issue/{key}?fields=status", headers)
        new_st = r4.json()["fields"]["status"]["name"] if r4.status_code == 200 else "?"
        return True, new_st, "transicao executada"
    return False, current, f"HTTP {r3.status_code}: {r3.text[:150]}"


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run

    base, headers = load_auth()
    log = []  # (key, action, flag, msg)

    tag = "[DRY] " if dry else ""
    print(f"{tag}KAN-13 LexNotify v2 — Update com Billing DONE")
    print(f"Jira: {base}")
    print("=" * 85)

    # ── 1) Reescrever Epic KAN-13 ────────────────────────────────────
    print(f"\n[1/5] Reescrevendo Epic KAN-13...")
    if not dry:
        r = _req("PUT", f"{base}/rest/api/3/issue/KAN-13", headers,
                 json={"fields": {"summary": NEW_SUMMARY, "description": EPIC_DESC}})
        ok = r.status_code == 204
        print(f"  {'[OK]' if ok else '[!!]'} summary + description")
        log.append(("KAN-13", "reescrito", "OK" if ok else "ERRO", f"HTTP {r.status_code}"))
    else:
        print(f"  {tag}{NEW_SUMMARY}")
        log.append(("KAN-13", "reescrito", "DRY", ""))

    # ── 2) Deletar KAN-56 ────────────────────────────────────────────
    print(f"\n[2/5] Deletando issues obsoletas...")
    for key in DELETE_KEYS:
        if not dry:
            r = _req("DELETE", f"{base}/rest/api/3/issue/{key}", headers)
            ok = r.status_code == 204
            print(f"  {'[OK]' if ok else '[!!]'} {key} deletada")
            log.append((key, "deletada", "OK" if ok else "ERRO", f"HTTP {r.status_code}"))
        else:
            print(f"  {tag}{key} seria deletada")
            log.append((key, "deletada", "DRY", ""))

    # ── 3) Editar issues existentes ──────────────────────────────────
    print(f"\n[3/5] Editando {len(EDITS)} issues existentes...")
    for edit in EDITS:
        key = edit["key"]
        fields = {}
        if edit.get("summary"): fields["summary"] = edit["summary"]
        if edit.get("labels") is not None: fields["labels"] = edit["labels"]
        if edit.get("description"): fields["description"] = edit["description"]
        if edit.get("duedate"): fields["duedate"] = edit["duedate"]

        if not dry and fields:
            r = _req("PUT", f"{base}/rest/api/3/issue/{key}", headers, json={"fields": fields})
            ok = r.status_code == 204
            print(f"  {'[OK]' if ok else '[!!]'} {key} editada")
            if not ok:
                print(f"       {r.text[:200]}")
            log.append((key, "editada", "OK" if ok else "ERRO", edit.get("summary", "")[:50]))
        else:
            print(f"  {tag}{key}: {edit.get('summary','')[:60]}")
            log.append((key, "editada", "DRY", ""))

        # Transicao?
        if edit.get("transition_to") and not dry:
            tok, st, msg = transition_to(base, headers, key, edit["transition_to"])
            print(f"       -> {edit['transition_to']}: {'[OK]' if tok else '[!!]'} {msg}")
            log.append((key, f"-> {edit['transition_to']}", "OK" if tok else "ERRO", msg))

    # ── 4) Criar novas issues ────────────────────────────────────────
    print(f"\n[4/5] Criando {len(NEW_ISSUES)} novas issues...")
    new_keys = []
    for issue in NEW_ISSUES:
        fields = {
            "project": {"key": "KAN"},
            "summary": issue["summary"],
            "issuetype": issue["issuetype"],
            "parent": issue["parent"],
            "labels": issue["labels"],
        }
        if issue.get("description"): fields["description"] = issue["description"]
        if issue.get("duedate"): fields["duedate"] = issue["duedate"]

        if not dry:
            r = _req("POST", f"{base}/rest/api/3/issue", headers, json={"fields": fields})
            if r.status_code in (200, 201):
                nk = r.json()["key"]
                new_keys.append((nk, issue))
                print(f"  [OK] {nk}: {issue['summary'][:55]}")
                log.append((nk, "criada", "OK", issue["summary"][:50]))
            else:
                print(f"  [!!] ERRO: {r.status_code} — {r.text[:200]}")
                log.append(("???", "criada", "ERRO", f"HTTP {r.status_code}"))
        else:
            print(f"  {tag}Nova: {issue['summary'][:60]}")
            log.append(("NEW", "criada", "DRY", ""))

    # ── 5) Mover P0 para Em andamento ────────────────────────────────
    p0_keys = [e["key"] for e in EDITS if "p0" in e.get("labels", []) and e.get("transition_to") is None]
    p0_new = [nk for nk, ni in new_keys if "p0" in ni.get("labels", [])]
    all_p0 = p0_keys + p0_new

    print(f"\n[5/5] Garantindo {len(all_p0)} issues P0 em 'Em andamento'...")
    for key in all_p0:
        if not dry:
            tok, st, msg = transition_to(base, headers, key, "Em andamento")
            print(f"  {'[OK]' if tok else '[!!]'} {key}: {msg}")
            log.append((key, "-> Em andamento", "OK" if tok else "ERRO", msg))
        else:
            print(f"  {tag}{key}")

    # ── Resumo ────────────────────────────────────────────────────────
    print("\n" + "=" * 85)
    print("RESUMO")
    print("=" * 85)
    hdr = f"{'Key':<10} {'Acao':<18} {'Flag':<5} Detalhe"
    print(hdr)
    print("-" * 80)
    for key, action, flag, detail in log:
        d = (detail[:50] + "..") if len(detail) > 52 else detail
        print(f"{key:<10} {action:<18} {flag:<5} {d}")

    ok = sum(1 for l in log if l[2] in ("OK", "DRY"))
    print(f"\n{ok}/{len(log)} OK.")


if __name__ == "__main__":
    main()
