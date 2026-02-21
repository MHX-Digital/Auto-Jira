#!/usr/bin/env python3
"""
Bot Telegram — Resumo diario do projeto LexNotify (KAN-13) + alertas de deadline.

Uso:
  python scripts/jira_telegram_notify.py              # resumo completo
  python scripts/jira_telegram_notify.py --deadlines   # so alertas de deadline
  python scripts/jira_telegram_notify.py --setup        # testa conexao bot + chat

Setup:
  1) Fale com @BotFather no Telegram -> /newbot -> copie o token
  2) Adicione o bot a um grupo ou inicie conversa direta
  3) Para descobrir chat_id:
     curl https://api.telegram.org/bot<TOKEN>/getUpdates
     -> procure "chat":{"id": 123456789}
  4) Adicione ao .env:
     TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
     TELEGRAM_CHAT_ID=-100123456789

Requer: requests, python-dotenv
"""

import os
import sys
import base64
import time
from datetime import datetime, timedelta
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

def load_config():
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    # Jira
    jira_base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    if not (jira_base and email and token):
        sys.exit("ERRO: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN nao definidos no .env")
    cred = base64.b64encode(f"{email}:{token}".encode()).decode()
    jira_headers = {
        "Authorization": f"Basic {cred}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Telegram
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not (tg_token and tg_chat):
        sys.exit(
            "ERRO: TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID nao definidos no .env\n"
            "Veja instrucoes no cabecalho deste script."
        )

    return jira_base, jira_headers, tg_token, tg_chat


def _req(method, url, headers=None, **kw):
    for i in range(2):
        try:
            r = requests.request(method, url, headers=headers, timeout=30, **kw)
            if r.status_code >= 500 and i == 0:
                time.sleep(1); continue
            return r
        except (requests.ConnectionError, requests.Timeout):
            if i == 0: time.sleep(1); continue
            raise
    return r


# ══════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════════════════

def tg_send(bot_token, chat_id, text, parse_mode="Markdown"):
    """Envia mensagem via Telegram Bot API. Divide se > 4096 chars."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        r = _req("POST", url, json={
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        })
        if r.status_code != 200:
            print(f"  [!!] Telegram erro: {r.status_code} — {r.text[:200]}")
            return False
    return True


def tg_test(bot_token, chat_id):
    """Testa conexao com bot."""
    # Verifica bot
    r = _req("GET", f"https://api.telegram.org/bot{bot_token}/getMe")
    if r.status_code != 200:
        print(f"ERRO: Bot token invalido. HTTP {r.status_code}")
        return False
    bot_name = r.json()["result"]["username"]
    print(f"Bot conectado: @{bot_name}")

    # Testa envio
    ok = tg_send(bot_token, chat_id, f"Teste de conexao - Jira KAN notifier via @{bot_name}")
    if ok:
        print(f"Mensagem de teste enviada para chat_id={chat_id}")
    return ok


# ══════════════════════════════════════════════════════════════════════════
# JIRA QUERIES
# ══════════════════════════════════════════════════════════════════════════

def fetch_kan13_children(jira_base, jira_headers):
    """Retorna lista de issues filhas de KAN-13."""
    jql = "parent=KAN-13 ORDER BY key ASC"
    r = _req("GET", f"{jira_base}/rest/api/3/search/jql", headers=jira_headers,
             params={"jql": jql, "fields": "summary,status,duedate,labels", "maxResults": 50})
    r.raise_for_status()
    issues = []
    for i in r.json().get("issues", []):
        f = i["fields"]
        issues.append({
            "key": i["key"],
            "summary": f["summary"],
            "status": f["status"]["name"],
            "duedate": f.get("duedate"),
            "labels": f.get("labels", []),
        })
    return issues


def categorize(issues):
    """Agrupa por status e fase."""
    by_status = {}
    by_phase = {"p0": [], "p1": [], "p2": [], "other": []}

    for i in issues:
        st = i["status"]
        by_status.setdefault(st, []).append(i)

        phase = "other"
        for l in i["labels"]:
            if l in ("p0", "p1", "p2"):
                phase = l; break
        by_phase[phase].append(i)

    return by_status, by_phase


def find_deadline_alerts(issues, days_ahead=7):
    """Issues com deadline nos proximos N dias ou atrasadas."""
    today = datetime.now().date()
    alerts = {"overdue": [], "soon": []}

    for i in issues:
        if not i["duedate"]:
            continue
        due = datetime.strptime(i["duedate"], "%Y-%m-%d").date()
        if i["status"].strip().lower() == "concluido":
            continue  # ja concluida, ignorar
        if due < today:
            i["_days"] = (today - due).days
            alerts["overdue"].append(i)
        elif due <= today + timedelta(days=days_ahead):
            i["_days"] = (due - today).days
            alerts["soon"].append(i)

    return alerts


# ══════════════════════════════════════════════════════════════════════════
# MENSAGENS
# ══════════════════════════════════════════════════════════════════════════

def build_daily_summary(issues):
    today = datetime.now().strftime("%d/%m/%Y")
    by_status, by_phase = categorize(issues)
    alerts = find_deadline_alerts(issues)

    total = len(issues)
    done = len(by_status.get("Concluido", []) + by_status.get("Concluído", []))
    in_prog = len(by_status.get("Em andamento", []))
    todo = len(by_status.get("A fazer", []))

    lines = []
    lines.append(f"*KAN-13 LexNotify — Resumo {today}*")
    lines.append("")
    lines.append(f"Total: {total} issues")
    lines.append(f"  Em andamento: {in_prog}")
    lines.append(f"  A fazer: {todo}")
    lines.append(f"  Concluido: {done}")
    lines.append("")

    # Progresso por fase
    for phase, label in [("p0", "P0 (30d)"), ("p1", "P1 (60d)"), ("p2", "P2 (90d)")]:
        items = by_phase[phase]
        if not items:
            continue
        done_count = sum(1 for i in items if i["status"].strip().lower() in ("concluido", "concluído"))
        lines.append(f"*{label}:* {done_count}/{len(items)} concluidas")
        for i in items:
            icon = "done" if i["status"].strip().lower() in ("concluido", "concluído") else "wip" if i["status"] == "Em andamento" else "todo"
            emoji = {"done": "[V]", "wip": "[>]", "todo": "[ ]"}[icon]
            due_str = f" (ate {i['duedate']})" if i["duedate"] else ""
            lines.append(f"  {emoji} {i['key']} {i['summary'][:40]}{due_str}")
        lines.append("")

    # Alertas de deadline
    if alerts["overdue"]:
        lines.append("*ATRASADAS:*")
        for i in alerts["overdue"]:
            lines.append(f"  [!!] {i['key']} — {i['_days']} dias atrasada (due {i['duedate']})")
        lines.append("")

    if alerts["soon"]:
        lines.append("*VENCENDO EM 7 DIAS:*")
        for i in alerts["soon"]:
            lines.append(f"  [!] {i['key']} — vence em {i['_days']} dias ({i['duedate']})")
        lines.append("")

    if not alerts["overdue"] and not alerts["soon"]:
        lines.append("Sem alertas de deadline.")

    return "\n".join(lines)


def build_deadline_only(issues):
    today = datetime.now().strftime("%d/%m/%Y")
    alerts = find_deadline_alerts(issues)

    lines = [f"*KAN-13 — Alertas de Deadline ({today})*", ""]

    if alerts["overdue"]:
        lines.append("*ATRASADAS:*")
        for i in alerts["overdue"]:
            lines.append(f"  [!!] {i['key']} {i['summary'][:35]} — {i['_days']}d atrasada")
        lines.append("")

    if alerts["soon"]:
        lines.append("*VENCENDO EM 7 DIAS:*")
        for i in alerts["soon"]:
            lines.append(f"  [!] {i['key']} {i['summary'][:35]} — vence em {i['_days']}d")
        lines.append("")

    if not alerts["overdue"] and not alerts["soon"]:
        lines.append("Nenhum alerta. Tudo dentro do prazo.")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Jira KAN-13 Telegram Notifier")
    parser.add_argument("--setup", action="store_true", help="Testar conexao bot + chat")
    parser.add_argument("--deadlines", action="store_true", help="Enviar somente alertas de deadline")
    args = parser.parse_args()

    jira_base, jira_headers, tg_token, tg_chat = load_config()

    if args.setup:
        ok = tg_test(tg_token, tg_chat)
        sys.exit(0 if ok else 1)

    # Buscar dados
    print("Buscando issues KAN-13...")
    issues = fetch_kan13_children(jira_base, jira_headers)
    print(f"  {len(issues)} issues encontradas")

    # Montar mensagem
    if args.deadlines:
        msg = build_deadline_only(issues)
    else:
        msg = build_daily_summary(issues)

    # Mostrar no terminal
    print("\n--- Mensagem ---")
    print(msg)
    print("--- Fim ---\n")

    # Enviar
    print("Enviando via Telegram...")
    ok = tg_send(tg_token, tg_chat, msg)
    if ok:
        print("[OK] Mensagem enviada.")
    else:
        print("[!!] Falha ao enviar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
