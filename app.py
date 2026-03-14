#!/usr/bin/env python3
"""
Auto-Jira v2 — Webhook Receiver, Telegram Bot, Chat AI, Dashboard & API Middleware.

Recebe webhooks do Jira Cloud e Telegram, envia notificacoes,
responde comandos, conversa via OpenAI, serve dashboard HTML,
e expoe API middleware para ChatGPT Actions.
"""

import os
import time
import base64
import logging
import hashlib
import hmac
from collections import deque
from datetime import datetime, timezone, timedelta

import requests
import pytz
from flask import Flask, request, jsonify, Response
from apscheduler.schedulers.background import BackgroundScheduler

# ======================================================================
# CONFIG
# ======================================================================

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("auto-jira")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "KAN")
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://mhxdigital.atlassian.net").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
OWNER_TELEGRAM_ID = int(os.environ.get("OWNER_TELEGRAM_ID", "1337538171"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "")

# Telegram Forum Topics (message_thread_id para cada topico)
# Rodar scripts/setup_telegram_topics.py para criar e obter os IDs
TOPIC_JIRA = os.environ.get("TOPIC_JIRA", "")
TOPIC_MEV = os.environ.get("TOPIC_MEV", "")
TOPIC_SHIELDFINANCE = os.environ.get("TOPIC_SHIELDFINANCE", "")
TOPIC_CHAT = os.environ.get("TOPIC_CHAT", "")
TOPIC_NEWS = os.environ.get("TOPIC_NEWS", "")
TOPIC_WHALE = os.environ.get("TOPIC_WHALE", "")
TOPIC_CRYPTO = os.environ.get("TOPIC_CRYPTO", "")
TOPIC_PANIC = os.environ.get("TOPIC_PANIC", "")
TOPIC_CLIENTS = os.environ.get("TOPIC_CLIENTS", "")
TOPIC_DOCS = os.environ.get("TOPIC_DOCS", "")

def _topic_id(env_val):
    """Converte env var string para int ou None."""
    return int(env_val) if env_val else None

START_TIME = time.time()
BRT = timezone(timedelta(hours=-3))
BRT_TZ = pytz.timezone("America/Sao_Paulo")

# Jira API auth headers
JIRA_HEADERS = {}
if JIRA_EMAIL and JIRA_API_TOKEN:
    _cred = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    JIRA_HEADERS = {
        "Authorization": f"Basic {_cred}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

# Rate limit: max 60 msgs/min
_msg_timestamps = deque(maxlen=60)
RATE_LIMIT = 60
RATE_WINDOW = 60

# Chat AI — conversation history per chat_id
_chat_history = {}
_AI_MAX_MESSAGES = 20
_ai_enabled = True

# Dashboard cache
_dashboard_cache = {"html": "", "ts": 0}
_DASHBOARD_CACHE_TTL = 300  # 5 minutes


# ======================================================================
# HELPERS
# ======================================================================

def _now_brt():
    return datetime.now(BRT).strftime("%d/%m/%Y %H:%M")


def _esc(text):
    """Escape HTML special chars para Telegram."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _req(method, url, headers=None, **kw):
    """HTTP request with 1 retry on 5xx/connection errors."""
    for i in range(2):
        try:
            r = requests.request(method, url, headers=headers, timeout=30, **kw)
            if r.status_code >= 500 and i == 0:
                time.sleep(1)
                continue
            return r
        except (requests.ConnectionError, requests.Timeout):
            if i == 0:
                time.sleep(1)
                continue
            raise
    return r


SEPARATOR = "\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014"


# ======================================================================
# SECURITY — Owner check
# ======================================================================

def is_authorized(update):
    """Verifica se a mensagem vem do OWNER_TELEGRAM_ID."""
    msg = update.get("message") or update.get("edited_message") or {}
    from_user = msg.get("from", {})
    return from_user.get("id") == OWNER_TELEGRAM_ID


def _get_chat_id(update):
    msg = update.get("message") or update.get("edited_message") or {}
    return msg.get("chat", {}).get("id")


def _get_message_text(update):
    msg = update.get("message") or update.get("edited_message") or {}
    return msg.get("text", "")


def _get_message_thread_id(update):
    """Extrai message_thread_id para responder no topic correto (Forum Groups)."""
    msg = update.get("message") or update.get("edited_message") or {}
    return msg.get("message_thread_id")


# ======================================================================
# TELEGRAM — Send
# ======================================================================

def tg_send(text, chat_id=None, topic_id=None):
    """Envia mensagem HTML via Telegram Bot API. Divide se > 4096 chars.
    topic_id: message_thread_id para Forum Topics (opcional).
    """
    target = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not target:
        log.error("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID nao configurados")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        payload = {
            "chat_id": target,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if topic_id:
            payload["message_thread_id"] = topic_id
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code != 200:
                log.error("Telegram erro: %s - %s", r.status_code, r.text[:300])
                return False
        except requests.RequestException as e:
            log.error("Telegram request falhou: %s", e)
            return False
    return True


def tg_send_plain(text, chat_id=None, topic_id=None):
    """Envia mensagem plain text (sem parse_mode).
    topic_id: message_thread_id para Forum Topics (opcional).
    """
    target = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not target:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        payload = {
            "chat_id": target,
            "text": chunk,
            "disable_web_page_preview": True,
        }
        if topic_id:
            payload["message_thread_id"] = topic_id
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code != 200:
                log.error("Telegram erro: %s - %s", r.status_code, r.text[:300])
                return False
        except requests.RequestException as e:
            log.error("Telegram request falhou: %s", e)
            return False
    return True


def tg_send_photo(chat_id, photo_url, caption=""):
    """Envia foto via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "HTML"
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except requests.RequestException:
        return False


def tg_send_document(chat_id, document_url, caption=""):
    """Envia documento via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    payload = {"chat_id": chat_id, "document": document_url}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "HTML"
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200
    except requests.RequestException:
        return False


def tg_send_poll(chat_id, question, options):
    """Cria enquete via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "question": question,
            "options": options,
            "is_anonymous": False,
        }, timeout=15)
        return r.status_code == 200
    except requests.RequestException:
        return False


def check_rate_limit():
    """Retorna True se dentro do limite."""
    now = time.time()
    while _msg_timestamps and _msg_timestamps[0] < now - RATE_WINDOW:
        _msg_timestamps.popleft()
    if len(_msg_timestamps) >= RATE_LIMIT:
        return False
    _msg_timestamps.append(now)
    return True


# ======================================================================
# JIRA API HELPERS
# ======================================================================

def jira_search(jql, fields="summary,status,issuetype,parent,duedate,labels,components,assignee,priority", max_results=100):
    """Busca issues via Jira REST API com paginacao."""
    if not JIRA_HEADERS:
        log.error("Jira auth nao configurada (JIRA_EMAIL / JIRA_API_TOKEN)")
        return []

    all_issues = []
    next_token = None

    while True:
        params = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
        }
        if next_token:
            params["nextPageToken"] = next_token

        r = _req("GET", f"{JIRA_BASE_URL}/rest/api/3/search/jql", headers=JIRA_HEADERS, params=params)
        if r.status_code != 200:
            log.error("Jira search erro: %s - %s", r.status_code, r.text[:300])
            return all_issues

        data = r.json()
        all_issues.extend(data.get("issues", []))

        next_token = data.get("nextPageToken")
        if not next_token:
            break

    return all_issues


def jira_get_issue(key):
    """Busca detalhes de uma issue especifica."""
    if not JIRA_HEADERS:
        return None
    r = _req("GET", f"{JIRA_BASE_URL}/rest/api/3/issue/{key}", headers=JIRA_HEADERS)
    if r.status_code != 200:
        return None
    return r.json()


def jira_create_issue(payload):
    """Cria uma issue no Jira."""
    if not JIRA_HEADERS:
        return None
    r = _req("POST", f"{JIRA_BASE_URL}/rest/api/3/issue", headers=JIRA_HEADERS, json=payload)
    if r.status_code not in (200, 201):
        log.error("Jira create erro: %s - %s", r.status_code, r.text[:300])
        return None
    return r.json()


def jira_update_issue(key, payload):
    """Atualiza uma issue no Jira."""
    if not JIRA_HEADERS:
        return False
    r = _req("PUT", f"{JIRA_BASE_URL}/rest/api/3/issue/{key}", headers=JIRA_HEADERS, json=payload)
    return r.status_code == 204


def jira_transition_issue(key, transition_id):
    """Move issue para outro status."""
    if not JIRA_HEADERS:
        return False
    r = _req("POST", f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/transitions",
             headers=JIRA_HEADERS, json={"transition": {"id": str(transition_id)}})
    return r.status_code == 204


def jira_get_transitions(key):
    """Lista transitions disponiveis para uma issue."""
    if not JIRA_HEADERS:
        return []
    r = _req("GET", f"{JIRA_BASE_URL}/rest/api/3/issue/{key}/transitions", headers=JIRA_HEADERS)
    if r.status_code != 200:
        return []
    return r.json().get("transitions", [])


def _extract_adf_text(node):
    """Extrai texto simples de um nodo ADF recursivamente."""
    if not isinstance(node, dict):
        return ""
    text = ""
    if node.get("type") == "text":
        text += node.get("text", "")
    for child in node.get("content", []):
        text += _extract_adf_text(child)
        if child.get("type") == "paragraph":
            text += "\n"
    return text.strip()


# ======================================================================
# JIRA WEBHOOK — EVENT HANDLERS
# ======================================================================

def handle_issue_created(data):
    issue = data.get("issue", {})
    key = issue.get("key", "?")
    fields = issue.get("fields", {})
    summary = _esc(fields.get("summary", ""))
    creator = _esc((fields.get("creator") or {}).get("displayName", "?"))
    issue_type = _esc((fields.get("issuetype") or {}).get("name", ""))
    priority = _esc((fields.get("priority") or {}).get("name", ""))
    link = f"{JIRA_BASE_URL}/browse/{key}"

    meta_parts = []
    if issue_type:
        meta_parts.append(issue_type)
    if priority:
        meta_parts.append(priority)
    meta_line = " | ".join(meta_parts)

    return (
        f"<b>[JIRA] Nova Issue Criada</b>\n"
        f"\n"
        f"<b>{_esc(key)}</b> - {summary}\n"
        f"{SEPARATOR}\n"
        f"Tipo: {meta_line}\n"
        f"Criada por: {creator}\n"
        f"<a href=\"{link}\">Abrir no Jira</a>\n"
        f"{_now_brt()}"
    )


def handle_issue_updated(data):
    issue = data.get("issue", {})
    key = issue.get("key", "?")
    fields = issue.get("fields", {})
    summary = _esc(fields.get("summary", ""))
    changelog = data.get("changelog", {})
    user = _esc((data.get("user") or {}).get("displayName", "?"))
    link = f"{JIRA_BASE_URL}/browse/{key}"

    messages = []

    for item in changelog.get("items", []):
        field = item.get("field", "")
        from_val = _esc(item.get("fromString", "") or "")
        to_val = _esc(item.get("toString", "") or "")

        if field == "status":
            messages.append(
                f"<b>[JIRA] Status Alterado</b>\n"
                f"\n"
                f"<b>{_esc(key)}</b> - {summary}\n"
                f"{SEPARATOR}\n"
                f"<code>{from_val}</code>  &gt;&gt;  <code>{to_val}</code>\n"
                f"Por: {user}\n"
                f"<a href=\"{link}\">Abrir no Jira</a>\n"
                f"{_now_brt()}"
            )

        elif field == "assignee":
            messages.append(
                f"<b>[JIRA] Responsavel Alterado</b>\n"
                f"\n"
                f"<b>{_esc(key)}</b> - {summary}\n"
                f"{SEPARATOR}\n"
                f"<code>{from_val or 'Ninguem'}</code>  &gt;&gt;  <code>{to_val or 'Ninguem'}</code>\n"
                f"Por: {user}\n"
                f"<a href=\"{link}\">Abrir no Jira</a>\n"
                f"{_now_brt()}"
            )

        elif field == "priority":
            messages.append(
                f"<b>[JIRA] Prioridade Alterada</b>\n"
                f"\n"
                f"<b>{_esc(key)}</b> - {summary}\n"
                f"{SEPARATOR}\n"
                f"<code>{from_val}</code>  &gt;&gt;  <code>{to_val}</code>\n"
                f"Por: {user}\n"
                f"<a href=\"{link}\">Abrir no Jira</a>\n"
                f"{_now_brt()}"
            )

        elif field == "labels":
            messages.append(
                f"<b>[JIRA] Labels Alteradas</b>\n"
                f"\n"
                f"<b>{_esc(key)}</b> - {summary}\n"
                f"{SEPARATOR}\n"
                f"<code>{from_val or '(nenhuma)'}</code>  &gt;&gt;  <code>{to_val or '(nenhuma)'}</code>\n"
                f"Por: {user}\n"
                f"<a href=\"{link}\">Abrir no Jira</a>\n"
                f"{_now_brt()}"
            )

        elif field == "duedate":
            messages.append(
                f"<b>[JIRA] Deadline Alterada</b>\n"
                f"\n"
                f"<b>{_esc(key)}</b> - {summary}\n"
                f"{SEPARATOR}\n"
                f"<code>{from_val or '(sem data)'}</code>  &gt;&gt;  <code>{to_val or '(sem data)'}</code>\n"
                f"Por: {user}\n"
                f"<a href=\"{link}\">Abrir no Jira</a>\n"
                f"{_now_brt()}"
            )

        elif field == "summary":
            messages.append(
                f"<b>[JIRA] Titulo Alterado</b>\n"
                f"\n"
                f"<b>{_esc(key)}</b>\n"
                f"{SEPARATOR}\n"
                f"<code>{from_val}</code>  &gt;&gt;  <code>{to_val}</code>\n"
                f"Por: {user}\n"
                f"<a href=\"{link}\">Abrir no Jira</a>\n"
                f"{_now_brt()}"
            )

        elif field == "description":
            messages.append(
                f"<b>[JIRA] Descricao Atualizada</b>\n"
                f"\n"
                f"<b>{_esc(key)}</b> - {summary}\n"
                f"{SEPARATOR}\n"
                f"Por: {user}\n"
                f"<a href=\"{link}\">Abrir no Jira</a>\n"
                f"{_now_brt()}"
            )

    if not messages:
        return None

    return "\n\n".join(messages)


def handle_comment_created(data):
    issue = data.get("issue", {})
    key = issue.get("key", "?")
    fields = issue.get("fields", {})
    summary = _esc(fields.get("summary", ""))
    comment = data.get("comment", {})
    author = _esc((comment.get("author") or {}).get("displayName", "?"))
    link = f"{JIRA_BASE_URL}/browse/{key}"

    body_adf = comment.get("body", {})
    body_text = _esc(_extract_adf_text(body_adf))
    if len(body_text) > 500:
        body_text = body_text[:500] + "..."

    return (
        f"<b>[JIRA] Novo Comentario</b>\n"
        f"\n"
        f"<b>{_esc(key)}</b> - {summary}\n"
        f"{SEPARATOR}\n"
        f"Autor: {author}\n"
        f"\"{body_text}\"\n"
        f"<a href=\"{link}\">Abrir no Jira</a>\n"
        f"{_now_brt()}"
    )


def handle_comment_updated(data):
    issue = data.get("issue", {})
    key = issue.get("key", "?")
    fields = issue.get("fields", {})
    summary = _esc(fields.get("summary", ""))
    comment = data.get("comment", {})
    author = _esc((comment.get("author") or {}).get("displayName", "?"))
    link = f"{JIRA_BASE_URL}/browse/{key}"

    body_adf = comment.get("body", {})
    body_text = _esc(_extract_adf_text(body_adf))
    if len(body_text) > 500:
        body_text = body_text[:500] + "..."

    return (
        f"<b>[JIRA] Comentario Editado</b>\n"
        f"\n"
        f"<b>{_esc(key)}</b> - {summary}\n"
        f"{SEPARATOR}\n"
        f"Autor: {author}\n"
        f"\"{body_text}\"\n"
        f"<a href=\"{link}\">Abrir no Jira</a>\n"
        f"{_now_brt()}"
    )


def handle_comment_deleted(data):
    issue = data.get("issue", {})
    key = issue.get("key", "?")
    fields = issue.get("fields", {})
    summary = _esc(fields.get("summary", ""))
    user = _esc((data.get("user") or {}).get("displayName", "?"))
    link = f"{JIRA_BASE_URL}/browse/{key}"

    return (
        f"<b>[JIRA] Comentario Deletado</b>\n"
        f"\n"
        f"<b>{_esc(key)}</b> - {summary}\n"
        f"{SEPARATOR}\n"
        f"Deletado por: {user}\n"
        f"<a href=\"{link}\">Abrir no Jira</a>\n"
        f"{_now_brt()}"
    )


def handle_issue_deleted(data):
    issue = data.get("issue", {})
    key = issue.get("key", "?")
    fields = issue.get("fields", {})
    summary = _esc(fields.get("summary", ""))
    user = _esc((data.get("user") or {}).get("displayName", "?"))

    return (
        f"<b>[JIRA] Issue Deletada</b>\n"
        f"\n"
        f"<b>{_esc(key)}</b> - {summary}\n"
        f"{SEPARATOR}\n"
        f"Deletada por: {user}\n"
        f"{_now_brt()}"
    )


# Event -> handler mapping
EVENT_HANDLERS = {
    "jira:issue_created": handle_issue_created,
    "jira:issue_updated": handle_issue_updated,
    "comment_created": handle_comment_created,
    "comment_updated": handle_comment_updated,
    "comment_deleted": handle_comment_deleted,
    "jira:issue_deleted": handle_issue_deleted,
}


# ======================================================================
# TELEGRAM BOT — Commands
# ======================================================================

def cmd_help():
    return (
        "<b>Auto-Jira Bot - Comandos</b>\n"
        f"{SEPARATOR}\n"
        "<code>/status</code> - Resumo rapido do Jira KAN\n"
        "<code>/deadlines</code> - Alertas de deadline\n"
        "<code>/sprint [n]</code> - Status sprint NexusP2P (1-5)\n"
        "<code>/board [ops|prod]</code> - Issues em andamento por board\n"
        "<code>/digest</code> - Enviar resumo diario agora\n"
        "<code>/ai on|off</code> - Ligar/desligar chat AI\n"
        "<code>/clear</code> - Limpar historico de conversa AI\n"
        "<code>/help</code> - Esta mensagem"
    )


def cmd_status():
    jql_andamento = f'project={JIRA_PROJECT_KEY} AND status="Em andamento" ORDER BY key ASC'
    jql_afazer = f'project={JIRA_PROJECT_KEY} AND status="A fazer" ORDER BY key ASC'
    jql_concluido = f'project={JIRA_PROJECT_KEY} AND status="Concluido" ORDER BY updated DESC'

    em_andamento = jira_search(jql_andamento)
    a_fazer = jira_search(jql_afazer)
    concluido = jira_search(jql_concluido)

    lines = [
        f"<b>Jira {JIRA_PROJECT_KEY} - Status</b>",
        f"{SEPARATOR}",
        f"Em andamento: <b>{len(em_andamento)}</b>",
        f"A fazer: <b>{len(a_fazer)}</b>",
        f"Concluido: <b>{len(concluido)}</b>",
        "",
    ]

    if em_andamento:
        lines.append("<b>Em andamento:</b>")
        for i in em_andamento[:15]:
            key = i["key"]
            s = _esc(i["fields"]["summary"][:50])
            lines.append(f"  {key} - {s}")

    lines.append(f"\n{_now_brt()}")
    return "\n".join(lines)


def cmd_deadlines():
    today = datetime.now(BRT).strftime("%Y-%m-%d")
    in_7d = (datetime.now(BRT) + timedelta(days=7)).strftime("%Y-%m-%d")

    jql_vencidas = (
        f'project={JIRA_PROJECT_KEY} AND status != "Concluido" '
        f'AND duedate < "{today}" ORDER BY duedate ASC'
    )
    jql_proximas = (
        f'project={JIRA_PROJECT_KEY} AND status != "Concluido" '
        f'AND duedate >= "{today}" AND duedate <= "{in_7d}" ORDER BY duedate ASC'
    )

    vencidas = jira_search(jql_vencidas)
    proximas = jira_search(jql_proximas)

    lines = [f"<b>Alertas de Deadline - {JIRA_PROJECT_KEY}</b>", SEPARATOR, ""]

    if vencidas:
        lines.append("<b>[ATRASADAS]</b>")
        for i in vencidas:
            key = i["key"]
            s = _esc(i["fields"]["summary"][:40])
            due = i["fields"].get("duedate", "?")
            lines.append(f"  {key} - {s} (venceu {due})")
        lines.append("")

    if proximas:
        lines.append("<b>[PROXIMOS 7 DIAS]</b>")
        for i in proximas:
            key = i["key"]
            s = _esc(i["fields"]["summary"][:40])
            due = i["fields"].get("duedate", "?")
            lines.append(f"  {key} - {s} (vence {due})")
        lines.append("")

    if not vencidas and not proximas:
        lines.append("Nenhum alerta de deadline ativo.")

    lines.append(_now_brt())
    return "\n".join(lines)


def cmd_sprint(args):
    sprint_num = args.strip() if args else ""
    if not sprint_num or not sprint_num.isdigit():
        return "Uso: <code>/sprint [1-5]</code>\nExemplo: /sprint 1"

    jql = (
        f'project={JIRA_PROJECT_KEY} AND parent=KAN-15 '
        f'AND labels="sprint-{sprint_num}" '
        f'ORDER BY status ASC, key ASC'
    )
    issues = jira_search(jql)

    if not issues:
        return f"Nenhuma issue encontrada para sprint {sprint_num}."

    by_status = {}
    for i in issues:
        st = i["fields"]["status"]["name"]
        by_status.setdefault(st, []).append(i)

    lines = [f"<b>Sprint {sprint_num} - NexusP2P</b>", SEPARATOR, ""]
    for status, items in by_status.items():
        lines.append(f"<b>{_esc(status)}</b> ({len(items)})")
        for i in items:
            key = i["key"]
            s = _esc(i["fields"]["summary"][:45])
            lines.append(f"  {key} - {s}")
        lines.append("")

    lines.append(_now_brt())
    return "\n".join(lines)


def cmd_board(args):
    board = args.strip().lower() if args else ""
    if board not in ("ops", "prod"):
        return "Uso: <code>/board [ops|prod]</code>"

    jql = (
        f'project={JIRA_PROJECT_KEY} AND status="Em andamento" '
        f'AND component="{board}" ORDER BY key ASC'
    )
    issues = jira_search(jql)

    if not issues:
        return f"Nenhuma issue em andamento no board <b>{_esc(board)}</b>."

    lines = [f"<b>Board {_esc(board.upper())} - Em andamento</b>", SEPARATOR, ""]
    for i in issues:
        key = i["key"]
        s = _esc(i["fields"]["summary"][:50])
        lines.append(f"  {key} - {s}")

    lines.append(f"\nTotal: {len(issues)}")
    lines.append(_now_brt())
    return "\n".join(lines)


# ======================================================================
# CHAT AI — OpenAI Integration
# ======================================================================

SYSTEM_PROMPT = """Voce eh o Bobby Axerold, assistente estrategico do Maike no grupo MHX.

O que voce faz:
- Estrategia e decisao: transforma tese em plano executavel (prioridades, trade-offs, criterios de corte)
- Macro + risco: le regime (liquidez/juros/dolar) e impoe gestao rigida de drawdown/exposicao
- Motor de alpha: estrutura sinais, filtros de robustez e validacao (evitar overfitting)
- Execucao: modela custos (spread/slippage/impacto)
- Derivativos/convexidade: desenha assimetria e protecao de cauda
- Atribuicao/feedback: decompoe PnL por fatores/sinais/custos
- Integracao com Jira: ajuda a organizar issues, boards e fluxos
- Respostas diretas, sem enrolacao. Tom profissional mas acessivel.

Contexto: Jira project KAN (MHX Digital), Telegram group MHX.
Responda em portugues. Seja conciso e direto."""


def chat_ai(chat_id, user_message):
    """Processa mensagem via OpenAI e retorna resposta."""
    if not OPENAI_API_KEY:
        return "Chat AI nao configurado (OPENAI_API_KEY ausente)."

    # Manage history
    if chat_id not in _chat_history:
        _chat_history[chat_id] = []

    history = _chat_history[chat_id]
    history.append({"role": "user", "content": user_message})

    # Sliding window
    if len(history) > _AI_MAX_MESSAGES:
        history[:] = history[-_AI_MAX_MESSAGES:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
        )
        assistant_msg = response.choices[0].message.content
        history.append({"role": "assistant", "content": assistant_msg})
        return assistant_msg
    except Exception as e:
        log.error("OpenAI erro: %s", e)
        return f"Erro ao processar mensagem: {e}"


# ======================================================================
# DAILY DIGEST
# ======================================================================

def _parse_issues(raw_issues):
    """Organiza issues em tasks e subtasks, por status."""
    tasks = []
    subtasks = []
    for i in raw_issues:
        f = i["fields"]
        entry = {
            "key": i["key"],
            "summary": f["summary"],
            "status": f["status"]["name"],
            "type": f["issuetype"]["name"],
            "parent": f.get("parent", {}).get("key") if f.get("parent") else None,
            "duedate": f.get("duedate"),
            "labels": f.get("labels", []),
            "components": [c["name"] for c in f.get("components", [])],
        }
        if f["issuetype"].get("subtask") or entry["type"] == "Subtask":
            subtasks.append(entry)
        else:
            tasks.append(entry)
    return tasks, subtasks


def _build_morning_digest(tasks, subtasks):
    """Seg-Sex manha: tarefas Em Andamento (conciso)."""
    now = datetime.now(BRT)
    data = now.strftime("%d/%m/%Y")

    andamento = [t for t in tasks if t["status"] == "Em andamento"]
    subs_andamento = [s for s in subtasks if s["status"] == "Em andamento"]
    today = now.date()

    lines = [f"Bom dia! {data}", f"{len(andamento)} tarefas em andamento:", ""]

    for t in andamento:
        due_str = ""
        if t["duedate"]:
            due = datetime.strptime(t["duedate"], "%Y-%m-%d").date()
            diff = (due - today).days
            if diff < 0:
                due_str = f" [ATRASADA {-diff}d]"
            elif diff <= 7:
                due_str = f" [vence {diff}d]"
        lines.append(f"  {t['key']} {t['summary'][:50]}{due_str}")

        child = [s for s in subs_andamento if s["parent"] == t["key"]]
        for s in child:
            lines.append(f"    > {s['key']} {s['summary'][:40]}")

    return "\n".join(lines)


def _build_night_digest(tasks, subtasks):
    """Seg-Sex noite: tarefas concluidas hoje."""
    now = datetime.now(BRT)
    data = now.strftime("%d/%m/%Y")
    today_str = now.strftime("%Y-%m-%d")

    concluidos = [t for t in tasks if t["status"] == "Concluído" or t["status"] == "Concluido"]
    subs_concluidos = [s for s in subtasks if s["status"] == "Concluído" or s["status"] == "Concluido"]
    total = len(concluidos) + len(subs_concluidos)

    if total == 0:
        return f"Boa noite! {data}\n\nNenhuma tarefa concluida hoje."

    lines = [f"Boa noite! {data}", f"{total} tarefa(s) concluida(s) hoje:", ""]

    for t in concluidos:
        lines.append(f"  {t['key']} {t['summary'][:50]}")
    for s in subs_concluidos:
        parent = f" ({s['parent']})" if s["parent"] else ""
        lines.append(f"  {s['key']} {s['summary'][:45]}{parent}")

    return "\n".join(lines)


def _build_weekly_report(tasks, subtasks):
    """Sabado manha: relatorio semanal (dom-sab)."""
    now = datetime.now(BRT)
    data = now.strftime("%d/%m/%Y")

    concluidos = [t for t in tasks if t["status"] == "Concluído" or t["status"] == "Concluido"]
    subs_concluidos = [s for s in subtasks if s["status"] == "Concluído" or s["status"] == "Concluido"]
    andamento = [t for t in tasks if t["status"] == "Em andamento"]
    afazer = [t for t in tasks if t["status"] == "A fazer"]
    em_analise = [t for t in tasks if t["status"] == "Em análise" or t["status"] == "Em analise"]
    total_concluidos = len(concluidos) + len(subs_concluidos)

    lines = [
        f"RELATORIO SEMANAL | {data}",
        "=" * 30,
        "",
        f"Concluidas: {total_concluidos}",
        f"Em andamento: {len(andamento)}",
        f"Em analise: {len(em_analise)}",
        f"A fazer: {len(afazer)}",
        "",
    ]

    if concluidos:
        lines.append("Concluidas na semana:")
        for t in concluidos:
            lines.append(f"  {t['key']} {t['summary'][:50]}")
    if subs_concluidos:
        for s in subs_concluidos:
            lines.append(f"  {s['key']} {s['summary'][:45]}")

    if concluidos or subs_concluidos:
        lines.append("")

    # Alertas de deadline
    today = now.date()
    alertas = []
    for t in andamento:
        if not t["duedate"]:
            continue
        due = datetime.strptime(t["duedate"], "%Y-%m-%d").date()
        diff = (due - today).days
        if diff < 0:
            alertas.append(f"  [ATRASADA {-diff}d] {t['key']} {t['summary'][:35]}")
        elif diff <= 14:
            alertas.append(f"  [vence {diff}d] {t['key']} {t['summary'][:35]}")

    if alertas:
        lines.append("Deadlines proximos:")
        lines.extend(alertas)

    return "\n".join(lines)


def _build_sunday_planning(tasks, subtasks):
    """Domingo noite: planejamento da semana."""
    now = datetime.now(BRT)
    today = now.date()

    andamento = [t for t in tasks if t["status"] == "Em andamento"]
    em_analise = [t for t in tasks if t["status"] == "Em análise" or t["status"] == "Em analise"]

    # Tasks com deadline na proxima semana (7 dias)
    urgentes = []
    atrasadas = []
    for t in andamento + em_analise:
        if not t["duedate"]:
            continue
        due = datetime.strptime(t["duedate"], "%Y-%m-%d").date()
        diff = (due - today).days
        if diff < 0:
            atrasadas.append((t, -diff))
        elif diff <= 7:
            urgentes.append((t, diff))

    lines = [
        f"PLANEJAMENTO DA SEMANA",
        "=" * 30,
        "",
        f"Em andamento: {len(andamento)} | Em analise: {len(em_analise)}",
        "",
    ]

    if atrasadas:
        lines.append(f"ATRASADAS ({len(atrasadas)}):")
        for t, days in sorted(atrasadas, key=lambda x: -x[1]):
            lines.append(f"  {t['key']} {t['summary'][:45]} [{days}d atrasada]")
        lines.append("")

    if urgentes:
        lines.append(f"VENCE ESTA SEMANA ({len(urgentes)}):")
        for t, days in sorted(urgentes, key=lambda x: x[1]):
            lines.append(f"  {t['key']} {t['summary'][:45]} [{days}d]")
        lines.append("")

    if not atrasadas and not urgentes:
        lines.append("Nenhum deadline critico esta semana.")
        lines.append("")

    # Top 5 em andamento (foco da semana)
    if andamento:
        lines.append(f"FOCO DA SEMANA ({min(len(andamento), 5)} prioridades):")
        for t in andamento[:5]:
            due = f" | ate {t['duedate']}" if t["duedate"] else ""
            lines.append(f"  {t['key']} {t['summary'][:45]}{due}")

    return "\n".join(lines)


def send_daily_digest():
    """Envia digest contextual baseado no dia/horario.

    Seg-Sex 08h: tarefas Em Andamento
    Seg-Sex 19h: tarefas concluidas no dia
    Sab 08h: relatorio semanal (dom-sab)
    Sab 19h: nao envia
    Dom 08h: nao envia
    Dom 19h: planejamento da semana
    """
    now = datetime.now(BRT)
    weekday = now.weekday()  # 0=seg, 5=sab, 6=dom
    is_morning = now.hour < 12

    # Sab noite e Dom manha: nao envia
    if (weekday == 5 and not is_morning) or (weekday == 6 and is_morning):
        log.info("Digest suprimido: %s %s", ["seg","ter","qua","qui","sex","sab","dom"][weekday],
                 "manha" if is_morning else "noite")
        return

    log.info("Enviando digest: %s %s", ["seg","ter","qua","qui","sex","sab","dom"][weekday],
             "manha" if is_morning else "noite")

    try:
        # Busca todas as issues (incluindo concluidas para noite/semanal)
        if is_morning and weekday < 5:
            # Seg-Sex manha: so precisa das nao concluidas
            jql = f'project={JIRA_PROJECT_KEY} AND status != "Concluido" ORDER BY key ASC'
        else:
            # Noite / Sab manha / Dom noite: precisa de tudo
            jql = f'project={JIRA_PROJECT_KEY} ORDER BY key ASC'

        raw = jira_search(jql)
        if not raw:
            log.warning("Digest: nenhuma issue encontrada")
            return

        tasks, subtasks = _parse_issues(raw)

        # Escolhe o builder correto
        if weekday == 5 and is_morning:
            msg = _build_weekly_report(tasks, subtasks)
        elif weekday == 6 and not is_morning:
            msg = _build_sunday_planning(tasks, subtasks)
        elif is_morning:
            msg = _build_morning_digest(tasks, subtasks)
        else:
            msg = _build_night_digest(tasks, subtasks)

        jira_topic = _topic_id(TOPIC_JIRA)
        ok = tg_send_plain(msg, topic_id=jira_topic)

        if ok:
            log.info("Digest enviado com sucesso")
        else:
            log.error("Digest: falha no envio")
    except Exception as e:
        log.error("Digest erro: %s", e)


# ======================================================================
# DASHBOARD HTML
# ======================================================================

DASHBOARD_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0d1117; color: #c9d1d9; padding: 20px; }
.container { max-width: 1100px; margin: 0 auto; }
h1 { color: #58a6ff; margin-bottom: 8px; font-size: 1.5rem; }
.subtitle { color: #8b949e; margin-bottom: 24px; font-size: 0.9rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
         gap: 16px; margin-bottom: 32px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
        padding: 20px; text-align: center; }
.card .number { font-size: 2.2rem; font-weight: 700; color: #58a6ff; }
.card .label { color: #8b949e; font-size: 0.85rem; margin-top: 4px; }
.card.warning .number { color: #d29922; }
.card.danger .number { color: #f85149; }
table { width: 100%; border-collapse: collapse; margin-bottom: 32px; }
th { background: #161b22; color: #58a6ff; text-align: left; padding: 12px;
     border-bottom: 2px solid #30363d; font-size: 0.85rem; }
td { padding: 10px 12px; border-bottom: 1px solid #21262d; font-size: 0.85rem; }
tr:hover { background: #161b22; }
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.alert-row td { background: rgba(248,81,73,0.08); }
.warning-row td { background: rgba(210,153,34,0.08); }
.section-title { color: #58a6ff; font-size: 1.1rem; margin: 24px 0 12px 0; }
.footer { color: #484f58; font-size: 0.8rem; margin-top: 32px;
          padding-top: 16px; border-top: 1px solid #21262d; }
@media (max-width: 600px) {
  .cards { grid-template-columns: 1fr 1fr; }
  td, th { padding: 8px 6px; font-size: 0.8rem; }
}
"""


def build_dashboard_html():
    """Gera dashboard HTML server-side."""
    jql_all = f'project={JIRA_PROJECT_KEY} AND status != "Concluido" ORDER BY key ASC'
    jql_done = f'project={JIRA_PROJECT_KEY} AND status = "Concluido"'
    jql_andamento = f'project={JIRA_PROJECT_KEY} AND status = "Em andamento" ORDER BY key ASC'

    all_issues = jira_search(jql_all)
    done_issues = jira_search(jql_done, fields="summary")
    andamento = jira_search(jql_andamento)

    tasks_afazer = [i for i in all_issues
                    if i["fields"]["status"]["name"] == "A fazer"]
    tasks_andamento = andamento

    today = datetime.now(BRT).date()
    alertas = []
    for i in all_issues:
        dd = i["fields"].get("duedate")
        if not dd:
            continue
        due = datetime.strptime(dd, "%Y-%m-%d").date()
        diff = (due - today).days
        if diff < 0:
            alertas.append({"issue": i, "diff": diff, "type": "overdue"})
        elif diff <= 7:
            alertas.append({"issue": i, "diff": diff, "type": "upcoming"})

    # Build cards
    total = len(all_issues) + len(done_issues)
    cards_html = f"""
    <div class="cards">
      <div class="card"><div class="number">{total}</div><div class="label">Total Issues</div></div>
      <div class="card"><div class="number">{len(tasks_andamento)}</div><div class="label">Em Andamento</div></div>
      <div class="card"><div class="number">{len(tasks_afazer)}</div><div class="label">A Fazer</div></div>
      <div class="card"><div class="number">{len(done_issues)}</div><div class="label">Concluido</div></div>
      <div class="card {"danger" if len([a for a in alertas if a["type"]=="overdue"]) > 0 else ""}">
        <div class="number">{len([a for a in alertas if a["type"]=="overdue"])}</div>
        <div class="label">Atrasadas</div></div>
      <div class="card {"warning" if len([a for a in alertas if a["type"]=="upcoming"]) > 0 else ""}">
        <div class="number">{len([a for a in alertas if a["type"]=="upcoming"])}</div>
        <div class="label">Vencendo (7d)</div></div>
    </div>"""

    # Build table — Em andamento
    rows = ""
    for i in tasks_andamento:
        f = i["fields"]
        key = i["key"]
        summary = _esc(f["summary"][:60])
        status = _esc(f["status"]["name"])
        dd = f.get("duedate") or "-"
        labels = ", ".join(f.get("labels", [])) or "-"
        link = f"{JIRA_BASE_URL}/browse/{key}"
        rows += f'<tr><td><a href="{link}">{key}</a></td><td>{summary}</td><td>{status}</td><td>{dd}</td><td>{labels}</td></tr>\n'

    table_html = f"""
    <h2 class="section-title">Em Andamento ({len(tasks_andamento)})</h2>
    <table>
      <thead><tr><th>Key</th><th>Summary</th><th>Status</th><th>Deadline</th><th>Labels</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>""" if tasks_andamento else ""

    # Build alerts table
    alerts_html = ""
    if alertas:
        arows = ""
        alertas.sort(key=lambda a: a["diff"])
        for a in alertas:
            i = a["issue"]
            f = i["fields"]
            key = i["key"]
            summary = _esc(f["summary"][:50])
            dd = f.get("duedate", "?")
            link = f"{JIRA_BASE_URL}/browse/{key}"
            row_class = "alert-row" if a["type"] == "overdue" else "warning-row"
            tag = f'{a["diff"]}d atrasada' if a["type"] == "overdue" else f'vence em {a["diff"]}d'
            arows += f'<tr class="{row_class}"><td><a href="{link}">{key}</a></td><td>{summary}</td><td>{dd}</td><td>{tag}</td></tr>\n'

        alerts_html = f"""
        <h2 class="section-title">Alertas de Deadline</h2>
        <table>
          <thead><tr><th>Key</th><th>Summary</th><th>Deadline</th><th>Status</th></tr></thead>
          <tbody>{arows}</tbody>
        </table>"""

    now_str = datetime.now(BRT).strftime("%d/%m/%Y %H:%M:%S BRT")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MHX Digital - Jira {JIRA_PROJECT_KEY} Dashboard</title>
  <style>{DASHBOARD_CSS}</style>
</head>
<body>
  <div class="container">
    <h1>MHX Digital - Jira {JIRA_PROJECT_KEY} Dashboard</h1>
    <div class="subtitle">Painel de acompanhamento de issues</div>
    {cards_html}
    {table_html}
    {alerts_html}
    <div class="footer">Ultima atualizacao: {now_str}</div>
  </div>
</body>
</html>"""


# ======================================================================
# API MIDDLEWARE — Auth helper
# ======================================================================

def require_api_key():
    """Verifica Bearer token no header Authorization. Retorna erro ou None."""
    if not APP_SECRET_KEY:
        return jsonify({"error": "API auth not configured"}), 500

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing or invalid Authorization header"}), 401

    token = auth[7:]
    if not hmac.compare_digest(token, APP_SECRET_KEY):
        return jsonify({"error": "invalid API key"}), 401

    return None


# ======================================================================
# ROUTES — Health
# ======================================================================

@app.route("/", methods=["GET"])
def health():
    uptime = int(time.time() - START_TIME)
    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    return jsonify({
        "status": "ok",
        "service": "Auto-Jira v2",
        "uptime": f"{h}h {m}m {s}s",
        "project": JIRA_PROJECT_KEY,
    })


# ======================================================================
# ROUTES — Jira Webhook
# ======================================================================

@app.route("/webhook/jira", methods=["POST"])
def webhook_jira():
    # Validate secret
    if WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Atlassian-Webhook-Identifier", "")
        if header_secret and header_secret != WEBHOOK_SECRET:
            log.warning("Webhook secret invalido")
            return jsonify({"error": "unauthorized"}), 401

    if not check_rate_limit():
        log.warning("Rate limit atingido")
        return jsonify({"error": "rate limited"}), 429

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no json body"}), 400

    event = data.get("webhookEvent", "")
    log.info("Evento recebido: %s", event)

    # Filter by project
    issue = data.get("issue", {})
    issue_key = issue.get("key", "")
    if issue_key and not issue_key.startswith(f"{JIRA_PROJECT_KEY}-"):
        log.info("Issue %s ignorada (projeto diferente)", issue_key)
        return jsonify({"status": "ignored", "reason": "wrong project"}), 200

    handler = EVENT_HANDLERS.get(event)
    if not handler:
        log.info("Evento nao tratado: %s", event)
        return jsonify({"status": "ignored", "reason": "unhandled event"}), 200

    message = handler(data)
    if not message:
        log.info("Sem mudancas relevantes no changelog")
        return jsonify({"status": "ignored", "reason": "no relevant changes"}), 200

    ok = tg_send(message, topic_id=_topic_id(TOPIC_JIRA))
    if ok:
        log.info("Notificacao enviada: %s [%s] -> topico Jira", issue_key, event)
        return jsonify({"status": "sent"}), 200
    else:
        log.error("Falha ao enviar notificacao para Telegram")
        return jsonify({"error": "telegram send failed"}), 500


# ======================================================================
# ROUTES — Telegram Webhook
# ======================================================================

@app.route("/webhook/telegram", methods=["POST"])
def webhook_telegram():
    global _ai_enabled

    # Validate Telegram webhook secret
    if TELEGRAM_WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header_secret != TELEGRAM_WEBHOOK_SECRET:
            log.warning("Telegram webhook secret invalido")
            return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "no json body"}), 400

    # Authorization check
    if not is_authorized(data):
        msg = data.get("message") or data.get("edited_message") or {}
        from_user = msg.get("from", {})
        log.warning("Telegram msg nao autorizada: user_id=%s username=%s",
                     from_user.get("id"), from_user.get("username"))
        return jsonify({"status": "ignored"}), 200

    chat_id = _get_chat_id(data)
    topic_id = _get_message_thread_id(data)
    text = _get_message_text(data).strip()

    if not text or not chat_id:
        return jsonify({"status": "ok"}), 200

    # Parse command
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]  # remove @botname
        args = parts[1] if len(parts) > 1 else ""

        response = None

        if cmd == "/help" or cmd == "/start":
            response = cmd_help()
        elif cmd == "/status":
            response = cmd_status()
        elif cmd == "/deadlines":
            response = cmd_deadlines()
        elif cmd == "/sprint":
            response = cmd_sprint(args)
        elif cmd == "/board":
            response = cmd_board(args)
        elif cmd == "/digest":
            send_daily_digest()
            response = "Digest enviado."
        elif cmd == "/clear":
            _chat_history.pop(chat_id, None)
            response = "Historico de conversa limpo."
        elif cmd == "/ai":
            if args.strip().lower() == "off":
                _ai_enabled = False
                response = "Chat AI desligado."
            elif args.strip().lower() == "on":
                _ai_enabled = True
                response = "Chat AI ligado."
            else:
                status = "ligado" if _ai_enabled else "desligado"
                response = f"Chat AI esta <b>{status}</b>.\nUso: <code>/ai on|off</code>"
        else:
            response = f"Comando desconhecido: {_esc(cmd)}\nDigite /help para ver comandos."

        if response:
            tg_send(response, chat_id=chat_id, topic_id=topic_id)

    else:
        # Free text — Chat AI
        if _ai_enabled and OPENAI_API_KEY:
            ai_response = chat_ai(chat_id, text)
            tg_send_plain(ai_response, chat_id=chat_id, topic_id=topic_id)

    return jsonify({"status": "ok"}), 200


# ======================================================================
# ROUTES — Dashboard
# ======================================================================

@app.route("/dashboard", methods=["GET"])
def dashboard():
    now = time.time()
    if now - _dashboard_cache["ts"] < _DASHBOARD_CACHE_TTL and _dashboard_cache["html"]:
        return Response(_dashboard_cache["html"], content_type="text/html")

    try:
        html = build_dashboard_html()
        _dashboard_cache["html"] = html
        _dashboard_cache["ts"] = now
        return Response(html, content_type="text/html")
    except Exception as e:
        log.error("Dashboard erro: %s", e)
        return Response(f"<h1>Erro ao carregar dashboard</h1><p>{e}</p>",
                        content_type="text/html", status=500)


# ======================================================================
# ROUTES — API Middleware (for ChatGPT Actions)
# ======================================================================

@app.route("/api/health", methods=["GET"])
def api_health():
    auth_err = require_api_key()
    if auth_err:
        return auth_err
    uptime = int(time.time() - START_TIME)
    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    return jsonify({
        "status": "ok",
        "service": "Auto-Jira v2 API",
        "uptime": f"{h}h {m}m {s}s",
        "project": JIRA_PROJECT_KEY,
    })


@app.route("/api/jira/status", methods=["GET"])
def api_jira_status():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    jql_all = f'project={JIRA_PROJECT_KEY} AND status != "Concluido" ORDER BY key ASC'
    jql_done = f'project={JIRA_PROJECT_KEY} AND status = "Concluido"'
    issues = jira_search(jql_all)
    done = jira_search(jql_done, fields="summary")

    by_status = {}
    for i in issues:
        st = i["fields"]["status"]["name"]
        by_status.setdefault(st, []).append({
            "key": i["key"],
            "summary": i["fields"]["summary"],
        })

    return jsonify({
        "project": JIRA_PROJECT_KEY,
        "total": len(issues) + len(done),
        "done": len(done),
        "active": len(issues),
        "by_status": {k: {"count": len(v), "issues": v} for k, v in by_status.items()},
    })


@app.route("/api/jira/deadlines", methods=["GET"])
def api_jira_deadlines():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    today = datetime.now(BRT).strftime("%Y-%m-%d")
    in_7d = (datetime.now(BRT) + timedelta(days=7)).strftime("%Y-%m-%d")

    vencidas = jira_search(
        f'project={JIRA_PROJECT_KEY} AND status != "Concluido" '
        f'AND duedate < "{today}" ORDER BY duedate ASC'
    )
    proximas = jira_search(
        f'project={JIRA_PROJECT_KEY} AND status != "Concluido" '
        f'AND duedate >= "{today}" AND duedate <= "{in_7d}" ORDER BY duedate ASC'
    )

    def _issue_summary(i):
        return {"key": i["key"], "summary": i["fields"]["summary"],
                "duedate": i["fields"].get("duedate"), "status": i["fields"]["status"]["name"]}

    return jsonify({
        "overdue": [_issue_summary(i) for i in vencidas],
        "upcoming_7d": [_issue_summary(i) for i in proximas],
    })


@app.route("/api/jira/search", methods=["GET"])
def api_jira_search():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    jql = request.args.get("jql", "")
    if not jql:
        return jsonify({"error": "jql parameter required"}), 400

    issues = jira_search(jql)
    results = []
    for i in issues:
        f = i["fields"]
        results.append({
            "key": i["key"],
            "summary": f.get("summary"),
            "status": f.get("status", {}).get("name"),
            "issuetype": f.get("issuetype", {}).get("name"),
            "priority": (f.get("priority") or {}).get("name"),
            "duedate": f.get("duedate"),
            "labels": f.get("labels", []),
            "assignee": (f.get("assignee") or {}).get("displayName"),
        })
    return jsonify({"total": len(results), "issues": results})


@app.route("/api/jira/issue/<key>", methods=["GET"])
def api_jira_issue(key):
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    issue = jira_get_issue(key)
    if not issue:
        return jsonify({"error": "issue not found"}), 404

    f = issue.get("fields", {})
    return jsonify({
        "key": issue["key"],
        "summary": f.get("summary"),
        "status": f.get("status", {}).get("name"),
        "issuetype": f.get("issuetype", {}).get("name"),
        "priority": (f.get("priority") or {}).get("name"),
        "duedate": f.get("duedate"),
        "labels": f.get("labels", []),
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "description_text": _extract_adf_text(f.get("description", {})),
        "components": [c["name"] for c in f.get("components", [])],
        "created": f.get("created"),
        "updated": f.get("updated"),
        "link": f"{JIRA_BASE_URL}/browse/{issue['key']}",
    })


@app.route("/api/jira/issue", methods=["POST"])
def api_jira_create_issue():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "json body required"}), 400

    # Build Jira payload
    fields = {"project": {"key": JIRA_PROJECT_KEY}}
    if "summary" in data:
        fields["summary"] = data["summary"]
    if "issuetype" in data:
        fields["issuetype"] = {"name": data["issuetype"]}
    else:
        fields["issuetype"] = {"name": "Task"}
    desc = data.get("issue_description") or data.get("description")
    if desc:
        fields["description"] = {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc}]}],
        }
    if "priority" in data:
        fields["priority"] = {"name": data["priority"]}
    if "labels" in data:
        fields["labels"] = data["labels"]
    if "duedate" in data:
        fields["duedate"] = data["duedate"]
    if "assignee" in data:
        fields["assignee"] = {"accountId": data["assignee"]}
    if "parent" in data:
        fields["parent"] = {"key": data["parent"]}

    result = jira_create_issue({"fields": fields})
    if not result:
        return jsonify({"error": "failed to create issue"}), 500

    return jsonify({"key": result.get("key"), "link": f"{JIRA_BASE_URL}/browse/{result.get('key')}"}), 201


@app.route("/api/jira/issue/<key>", methods=["PUT"])
def api_jira_update_issue(key):
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "json body required"}), 400

    fields = {}
    if "summary" in data:
        fields["summary"] = data["summary"]
    desc = data.get("issue_description") or data.get("description")
    if desc:
        fields["description"] = {
            "version": 1,
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc}]}],
        }
    if "priority" in data:
        fields["priority"] = {"name": data["priority"]}
    if "labels" in data:
        fields["labels"] = data["labels"]
    if "duedate" in data:
        fields["duedate"] = data["duedate"]
    if "assignee" in data:
        fields["assignee"] = {"accountId": data["assignee"]}

    ok = jira_update_issue(key, {"fields": fields})
    if not ok:
        return jsonify({"error": "failed to update issue"}), 500

    return jsonify({"status": "updated", "key": key})


@app.route("/api/jira/issue/<key>/transition", methods=["POST"])
def api_jira_transition(key):
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data or "transition_id" not in data:
        # List available transitions
        transitions = jira_get_transitions(key)
        return jsonify({"available_transitions": transitions})

    ok = jira_transition_issue(key, data["transition_id"])
    if not ok:
        return jsonify({"error": "transition failed"}), 500

    return jsonify({"status": "transitioned", "key": key})


@app.route("/api/telegram/send", methods=["POST"])
def api_telegram_send():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "text field required"}), 400

    chat_id = data.get("chat_id", TELEGRAM_CHAT_ID)
    parse_mode = data.get("parse_mode", "HTML")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": data["text"],
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if "reply_to_message_id" in data:
        payload["reply_to_message_id"] = data["reply_to_message_id"]
    if "message_thread_id" in data:
        payload["message_thread_id"] = data["message_thread_id"]
    elif "topic" in data:
        # Aceita nome do topico: jira, mev, shieldfinance, chat, news, whale, crypto, panic, clients, docs
        topic_map = {
            "jira": TOPIC_JIRA, "mev": TOPIC_MEV, "shieldfinance": TOPIC_SHIELDFINANCE,
            "chat": TOPIC_CHAT, "news": TOPIC_NEWS,
            "whale": TOPIC_WHALE, "crypto": TOPIC_CRYPTO, "panic": TOPIC_PANIC,
            "clients": TOPIC_CLIENTS, "docs": TOPIC_DOCS,
        }
        tid = _topic_id(topic_map.get(data["topic"].lower(), ""))
        if tid:
            payload["message_thread_id"] = tid

    try:
        r = requests.post(url, json=payload, timeout=15)
        return jsonify(r.json()), r.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/telegram/send-photo", methods=["POST"])
def api_telegram_send_photo():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data or "photo" not in data:
        return jsonify({"error": "photo field required"}), 400

    chat_id = data.get("chat_id", TELEGRAM_CHAT_ID)
    ok = tg_send_photo(chat_id, data["photo"], data.get("caption", ""))
    return jsonify({"ok": ok})


@app.route("/api/telegram/send-document", methods=["POST"])
def api_telegram_send_document():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data or "document" not in data:
        return jsonify({"error": "document field required"}), 400

    chat_id = data.get("chat_id", TELEGRAM_CHAT_ID)
    ok = tg_send_document(chat_id, data["document"], data.get("caption", ""))
    return jsonify({"ok": ok})


@app.route("/api/telegram/send-poll", methods=["POST"])
def api_telegram_send_poll():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data or "question" not in data or "options" not in data:
        return jsonify({"error": "question and options fields required"}), 400

    chat_id = data.get("chat_id", TELEGRAM_CHAT_ID)
    ok = tg_send_poll(chat_id, data["question"], data["options"])
    return jsonify({"ok": ok})


@app.route("/api/telegram/topics", methods=["GET"])
def api_telegram_topics():
    """Lista topicos configurados no grupo MHX."""
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    topics = {
        "jira": _topic_id(TOPIC_JIRA),
        "mev": _topic_id(TOPIC_MEV),
        "shieldfinance": _topic_id(TOPIC_SHIELDFINANCE),
        "chat": _topic_id(TOPIC_CHAT),
        "news": _topic_id(TOPIC_NEWS),
        "whale": _topic_id(TOPIC_WHALE),
        "crypto": _topic_id(TOPIC_CRYPTO),
        "panic": _topic_id(TOPIC_PANIC),
        "clients": _topic_id(TOPIC_CLIENTS),
        "docs": _topic_id(TOPIC_DOCS),
    }
    configured = {k: v for k, v in topics.items() if v is not None}
    return jsonify({
        "topics": configured,
        "total_configured": len(configured),
        "total_available": len(topics),
    })


@app.route("/api/telegram/updates", methods=["GET"])
def api_telegram_updates():
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"limit": 20}
    offset = request.args.get("offset")
    if offset:
        params["offset"] = offset

    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        # Filter to owner messages only
        if data.get("ok") and data.get("result"):
            filtered = []
            for update in data["result"]:
                msg = update.get("message") or update.get("edited_message") or {}
                from_user = msg.get("from", {})
                if from_user.get("id") == OWNER_TELEGRAM_ID:
                    filtered.append(update)
            data["result"] = filtered
        return jsonify(data)
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500


# ======================================================================
# ROUTES — Cron Trigger (external cron service)
# ======================================================================

CRON_SECRET = os.environ.get("CRON_SECRET", "") or APP_SECRET_KEY


def _check_cron_auth():
    """Verifica auth para rotas /cron/*. Aceita Bearer token ou ?secret= query param."""
    if not CRON_SECRET:
        return jsonify({"error": "CRON_SECRET not configured"}), 500

    # Check Bearer token first
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and hmac.compare_digest(auth[7:], CRON_SECRET):
        return None

    # Fallback to query param (useful for cron-job.org)
    secret = request.args.get("secret", "")
    if secret and hmac.compare_digest(secret, CRON_SECRET):
        return None

    return jsonify({"error": "unauthorized"}), 401


@app.route("/cron/daily-digest", methods=["GET", "POST"])
def cron_daily_digest():
    """Endpoint para trigger externo do daily digest (cron-job.org, Railway cron, etc.)."""
    auth_err = _check_cron_auth()
    if auth_err:
        return auth_err

    log.info("[CRON] Daily digest triggered via HTTP")
    try:
        send_daily_digest()
        return jsonify({"status": "ok", "message": "daily digest sent", "timestamp": _now_brt()})
    except Exception as e:
        log.error("[CRON] Daily digest failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/cron/test", methods=["GET", "POST"])
def cron_test():
    """Dry-run: retorna o digest sem enviar no Telegram."""
    auth_err = _check_cron_auth()
    if auth_err:
        return auth_err

    log.info("[CRON] Test digest requested")
    try:
        jql = f'project={JIRA_PROJECT_KEY} AND status != "Concluido" ORDER BY key ASC'
        raw = jira_search(jql)
        if not raw:
            return jsonify({"status": "ok", "message": "no issues found", "msg1": "", "msg2": ""})

        tasks, subtasks = _parse_issues(raw)
        msg1, msg2 = _build_digest_messages(tasks, subtasks)

        return jsonify({
            "status": "ok",
            "message": "dry run - not sent to Telegram",
            "total_issues": len(raw),
            "total_tasks": len(tasks),
            "total_subtasks": len(subtasks),
            "msg1_preview": msg1[:500],
            "msg2_preview": msg2[:500],
            "timestamp": _now_brt(),
        })
    except Exception as e:
        log.error("[CRON] Test digest failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ======================================================================
# SCHEDULER — APScheduler (fallback, runs if container stays alive)
# ======================================================================

def check_recurring_payments():
    """Verifica pagamentos recorrentes e envia lembrete 2 dias antes (dia 18)."""
    today = datetime.now(BRT_TZ)
    if today.day != 18:
        return
    log.info("Dia 18 — enviando lembrete de parcelas dia 20")
    next_month = today.strftime("%B/%Y")
    msg = (
        f"\u26a0\ufe0f LEMBRETE PARCELAS — Vencimento dia 20\n"
        f"{SEPARATOR}\n"
        f"\n"
        f"\U0001f4b3 KAN-213 — Divida ativa 1: R$620,68\n"
        f"   Parcela mensal (18x) — pagar ate 20/{today.strftime('%m/%Y')}\n"
        f"\n"
        f"\U0001f4b3 KAN-214 — Divida ativa 2: R$588,60\n"
        f"   Parcela mensal (60x) — pagar ate 20/{today.strftime('%m/%Y')}\n"
        f"\n"
        f"\U0001f4c5 Faltam 2 dias!\n"
        f"\n"
        f"PJ 24.409 — modo manutencao"
    )
    tg_send_plain(msg, topic_id=_topic_id(TOPIC_JIRA))


def check_protesto_reminder():
    """Envia lembrete do protesto KAN-212 no dia 1 de maio."""
    today = datetime.now(BRT_TZ)
    if today.month != 5 or today.day != 1:
        return
    log.info("1 de maio — lembrete protesto KAN-212")
    msg = (
        "\u26a0\ufe0f LEMBRETE PROTESTO — KAN-212\n"
        f"{SEPARATOR}\n"
        "\n"
        "\U0001f4cb Protesto cartorio: R$118,62\n"
        "   PJ 24.409 — pagar ate 15/mai/2026\n"
        "\n"
        "\U0001f4c5 Faltam 14 dias para o vencimento!\n"
        "\n"
        "Acao: realizar pagamento e solicitar baixa do protesto."
    )
    tg_send_plain(msg, topic_id=_topic_id(TOPIC_JIRA))


scheduler = BackgroundScheduler(timezone=BRT_TZ)
scheduler.add_job(send_daily_digest, "cron", hour="8,19", minute=0, id="daily_digest")
scheduler.add_job(check_recurring_payments, "cron", hour=9, minute=0, day="18", id="payment_reminder")
scheduler.add_job(check_protesto_reminder, "cron", hour=9, minute=0, day="1", id="protesto_reminder")


def _start_scheduler():
    """Inicia APScheduler com logging claro."""
    try:
        scheduler.start()
        jobs = scheduler.get_jobs()
        log.info("=" * 50)
        log.info("APScheduler iniciado com %d job(s):", len(jobs))
        for job in jobs:
            log.info("  - %s | trigger: %s | next: %s", job.id, job.trigger, job.next_run_time)
        log.info("NOTA: Use cron externo (cron-job.org) como trigger principal.")
        log.info("  URL: /cron/daily-digest?secret=<CRON_SECRET>")
        log.info("=" * 50)
    except Exception as e:
        log.error("APScheduler falhou ao iniciar: %s", e)


# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":
    _start_scheduler()
    port = int(os.environ.get("PORT", 5000))
    log.info("Servidor dev na porta %d", port)
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
else:
    # Production (gunicorn)
    _start_scheduler()
