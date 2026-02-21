#!/usr/bin/env python3
"""
Auto-Jira — Webhook Receiver & Telegram Notifier.

Recebe webhooks do Jira Cloud e envia notificacoes
formatadas no Telegram em tempo real.
"""

import os
import time
import logging
from collections import deque
from datetime import datetime, timezone, timedelta

import requests
from flask import Flask, request, jsonify

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
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "KAN")
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://mhxdigital.atlassian.net").rstrip("/")

START_TIME = time.time()
BRT = timezone(timedelta(hours=-3))

# Rate limit: max 60 msgs/min
_msg_timestamps = deque(maxlen=60)
RATE_LIMIT = 60
RATE_WINDOW = 60


# ======================================================================
# TELEGRAM
# ======================================================================

def tg_send(text):
    """Envia mensagem HTML via Telegram Bot API. Divide se > 4096 chars."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID nao configurados")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            r = requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=15)
            if r.status_code != 200:
                log.error("Telegram erro: %s — %s", r.status_code, r.text[:300])
                return False
        except requests.RequestException as e:
            log.error("Telegram request falhou: %s", e)
            return False
    return True


def check_rate_limit():
    """Retorna True se dentro do limite."""
    now = time.time()
    while _msg_timestamps and _msg_timestamps[0] < now - RATE_WINDOW:
        _msg_timestamps.popleft()
    if len(_msg_timestamps) >= RATE_LIMIT:
        return False
    _msg_timestamps.append(now)
    return True


def _now_brt():
    return datetime.now(BRT).strftime("%d/%m/%Y %H:%M")


def _esc(text):
    """Escape HTML special chars para Telegram."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ======================================================================
# MESSAGE TEMPLATES
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
    meta_line = "  \u2022  ".join(meta_parts)

    return (
        f"\U0001f195 <b>Nova Issue Criada</b>\n"
        f"\n"
        f"\U0001f4cb <b>{_esc(key)}</b> \u2014 {summary}\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001f4dd {meta_line}\n"
        f"\U0001f464 Criada por {creator}\n"
        f"\U0001f517 <a href=\"{link}\">Abrir no Jira</a>\n"
        f"\u23f0 {_now_brt()}"
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
                f"\U0001f504 <b>Status Alterado</b>\n"
                f"\n"
                f"\U0001f4cb <b>{_esc(key)}</b> \u2014 {summary}\n"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                f"\U0001f4ca <code>{from_val}</code> \u2192 <code>{to_val}</code>\n"
                f"\U0001f464 {user}\n"
                f"\U0001f517 <a href=\"{link}\">Abrir no Jira</a>\n"
                f"\u23f0 {_now_brt()}"
            )

        elif field == "assignee":
            messages.append(
                f"\U0001f465 <b>Responsavel Alterado</b>\n"
                f"\n"
                f"\U0001f4cb <b>{_esc(key)}</b> \u2014 {summary}\n"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                f"\U0001f464 <code>{from_val or 'Ninguem'}</code> \u2192 <code>{to_val or 'Ninguem'}</code>\n"
                f"\U0001f517 <a href=\"{link}\">Abrir no Jira</a>\n"
                f"\u23f0 {_now_brt()}"
            )

        elif field == "priority":
            messages.append(
                f"\u26a1 <b>Prioridade Alterada</b>\n"
                f"\n"
                f"\U0001f4cb <b>{_esc(key)}</b> \u2014 {summary}\n"
                f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
                f"\U0001f4ca <code>{from_val}</code> \u2192 <code>{to_val}</code>\n"
                f"\U0001f464 {user}\n"
                f"\U0001f517 <a href=\"{link}\">Abrir no Jira</a>\n"
                f"\u23f0 {_now_brt()}"
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
        f"\U0001f4ac <b>Novo Comentario</b>\n"
        f"\n"
        f"\U0001f4cb <b>{_esc(key)}</b> \u2014 {summary}\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001f464 {author}\n"
        f"\U0001f4dd {body_text}\n"
        f"\U0001f517 <a href=\"{link}\">Abrir no Jira</a>\n"
        f"\u23f0 {_now_brt()}"
    )


def handle_issue_deleted(data):
    issue = data.get("issue", {})
    key = issue.get("key", "?")
    fields = issue.get("fields", {})
    summary = _esc(fields.get("summary", ""))
    user = _esc((data.get("user") or {}).get("displayName", "?"))

    return (
        f"\U0001f5d1 <b>Issue Deletada</b>\n"
        f"\n"
        f"\U0001f4cb <b>{_esc(key)}</b> \u2014 {summary}\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001f464 Deletada por {user}\n"
        f"\u23f0 {_now_brt()}"
    )


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


# Event -> handler mapping
EVENT_HANDLERS = {
    "jira:issue_created": handle_issue_created,
    "jira:issue_updated": handle_issue_updated,
    "comment_created": handle_comment_created,
    "jira:issue_deleted": handle_issue_deleted,
}


# ======================================================================
# ROUTES
# ======================================================================

@app.route("/", methods=["GET"])
def health():
    uptime = int(time.time() - START_TIME)
    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    return jsonify({
        "status": "ok",
        "service": "Auto-Jira",
        "uptime": f"{h}h {m}m {s}s",
        "project": JIRA_PROJECT_KEY,
    })


@app.route("/webhook/jira", methods=["POST"])
def webhook_jira():
    # Validate secret
    if WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Atlassian-Webhook-Identifier", "")
        if header_secret != WEBHOOK_SECRET:
            log.warning("Webhook secret invalido")
            return jsonify({"error": "unauthorized"}), 401

    # Rate limit
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

    # Handle event
    handler = EVENT_HANDLERS.get(event)
    if not handler:
        log.info("Evento nao tratado: %s", event)
        return jsonify({"status": "ignored", "reason": "unhandled event"}), 200

    message = handler(data)
    if not message:
        log.info("Sem mudancas relevantes no changelog")
        return jsonify({"status": "ignored", "reason": "no relevant changes"}), 200

    # Send to Telegram
    ok = tg_send(message)
    if ok:
        log.info("Notificacao enviada: %s [%s]", issue_key, event)
        return jsonify({"status": "sent"}), 200
    else:
        log.error("Falha ao enviar notificacao para Telegram")
        return jsonify({"error": "telegram send failed"}), 500


# ======================================================================
# MAIN (dev only)
# ======================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log.info("Servidor dev na porta %d", port)
    app.run(host="0.0.0.0", port=port, debug=True)
