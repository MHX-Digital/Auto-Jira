#!/usr/bin/env python3
"""
Resumo diario Jira KAN -> Telegram (8h e 19h).

Uso:
  python scripts/jira_daily_telegram.py              # envia resumo agora
  python scripts/jira_daily_telegram.py --test       # mostra no terminal sem enviar
  python scripts/jira_daily_telegram.py --install    # cria tarefas no Task Scheduler (8h + 19h)
  python scripts/jira_daily_telegram.py --uninstall  # remove tarefas do Task Scheduler

Requer: requests, python-dotenv
"""

import os
import sys
import base64
import time
import argparse
import subprocess
from datetime import datetime
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
SCRIPT_PATH = Path(__file__).resolve()

# ══════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════

def load_config():
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path, override=True)

    jira_base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    if not (jira_base and email and token):
        sys.exit("ERRO: JIRA vars nao definidas no .env")
    cred = base64.b64encode(f"{email}:{token}".encode()).decode()
    jira_h = {
        "Authorization": f"Basic {cred}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if not (tg_token and tg_chat):
        sys.exit("ERRO: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nao definidos no .env")

    return jira_base, jira_h, tg_token, tg_chat


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
# JIRA — BUSCAR TUDO DO PROJETO
# ══════════════════════════════════════════════════════════════════════════

def fetch_all_active_issues(jira_base, jira_h):
    """Busca todas as issues do projeto KAN que nao estao concluidas."""
    all_issues = []
    next_token = None

    while True:
        params = {
            "jql": 'project=KAN AND status != "Concluído" ORDER BY key ASC',
            "fields": "summary,status,issuetype,parent,duedate,labels,components",
            "maxResults": 100,
        }
        if next_token:
            params["nextPageToken"] = next_token

        r = _req("GET", f"{jira_base}/rest/api/3/search/jql", headers=jira_h, params=params)
        r.raise_for_status()
        data = r.json()
        all_issues.extend(data.get("issues", []))

        next_token = data.get("nextPageToken")
        if not next_token:
            break

    return all_issues


def parse_issues(raw_issues):
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


# ══════════════════════════════════════════════════════════════════════════
# TEMPLATES TELEGRAM
# ══════════════════════════════════════════════════════════════════════════

def escape_md(text):
    """Escape chars especiais do MarkdownV2."""
    chars = r'_*[]()~`>#+-=|{}.!'
    for c in chars:
        text = text.replace(c, f'\\{c}')
    return text


def build_messages(tasks, subtasks):
    """Monta as 2 mensagens do resumo diario."""
    now = datetime.now()
    hora = now.strftime("%H:%M")
    data = now.strftime("%d/%m/%Y")
    periodo = "Bom dia" if now.hour < 12 else "Boa noite"

    # Separar por status
    tasks_afazer = [t for t in tasks if t["status"] == "A fazer"]
    tasks_andamento = [t for t in tasks if t["status"] == "Em andamento"]
    subs_afazer = [s for s in subtasks if s["status"] == "A fazer"]
    subs_andamento = [s for s in subtasks if s["status"] == "Em andamento"]

    # ── MSG 1: A FAZER (resumo contagem) ──────────────────────────────
    msg1_lines = []
    msg1_lines.append(f"{periodo}! Resumo Jira KAN - {data} ({hora})")
    msg1_lines.append("")
    msg1_lines.append("--- A FAZER ---")
    msg1_lines.append("")
    msg1_lines.append(f"Tasks (Epics/Tarefas): {len(tasks_afazer)}")
    msg1_lines.append(f"Subtasks: {len(subs_afazer)}")
    msg1_lines.append(f"Total pendente: {len(tasks_afazer) + len(subs_afazer)}")
    msg1_lines.append("")

    if tasks_afazer:
        msg1_lines.append("Tasks pendentes:")
        for t in tasks_afazer:
            due = f" | ate {t['duedate']}" if t["duedate"] else ""
            labels = f" [{', '.join(t['labels'])}]" if t["labels"] else ""
            msg1_lines.append(f"  - {t['key']} {t['summary'][:50]}{labels}{due}")
        msg1_lines.append("")

    if subs_afazer:
        msg1_lines.append(f"Subtasks pendentes ({len(subs_afazer)}):")
        # Agrupar por parent
        by_parent = {}
        for s in subs_afazer:
            p = s["parent"] or "sem parent"
            by_parent.setdefault(p, []).append(s)
        for parent, subs in sorted(by_parent.items()):
            msg1_lines.append(f"  [{parent}]")
            for s in subs:
                msg1_lines.append(f"    - {s['key']} {s['summary'][:45]}")
        msg1_lines.append("")

    # ── MSG 2: EM ANDAMENTO (detalhado) ───────────────────────────────
    msg2_lines = []
    msg2_lines.append("--- EM ANDAMENTO ---")
    msg2_lines.append("")
    msg2_lines.append(f"Tasks ativas: {len(tasks_andamento)}")
    msg2_lines.append(f"Subtasks ativas: {len(subs_andamento)}")
    msg2_lines.append("")

    if tasks_andamento:
        msg2_lines.append("== TASKS ==")
        msg2_lines.append("")
        for t in tasks_andamento:
            due = f"Deadline: {t['duedate']}" if t["duedate"] else "Sem deadline"
            comp = f"Componente: {', '.join(t['components'])}" if t["components"] else ""
            labels = f"Labels: {', '.join(t['labels'])}" if t["labels"] else ""

            msg2_lines.append(f"{t['key']} - {t['summary']}")
            info_parts = [x for x in [due, comp, labels] if x]
            if info_parts:
                msg2_lines.append(f"  {' | '.join(info_parts)}")

            # Subtasks desta task
            child_subs = [s for s in subs_andamento if s["parent"] == t["key"]]
            if child_subs:
                msg2_lines.append(f"  Subtasks em andamento ({len(child_subs)}):")
                for s in child_subs:
                    msg2_lines.append(f"    > {s['key']} {s['summary'][:45]}")
            msg2_lines.append("")

    # Subtasks em andamento orfas (parent nao esta em andamento)
    andamento_keys = {t["key"] for t in tasks_andamento}
    subs_orfas = [s for s in subs_andamento if s["parent"] not in andamento_keys]
    if subs_orfas:
        msg2_lines.append("== SUBTASKS (parent nao listado acima) ==")
        msg2_lines.append("")
        by_parent = {}
        for s in subs_orfas:
            p = s["parent"] or "sem parent"
            by_parent.setdefault(p, []).append(s)
        for parent, subs in sorted(by_parent.items()):
            msg2_lines.append(f"  [{parent}]")
            for s in subs:
                msg2_lines.append(f"    > {s['key']} {s['summary'][:45]}")
        msg2_lines.append("")

    # Deadlines proximas (em andamento com due nos proximos 7 dias)
    from datetime import timedelta
    today = datetime.now().date()
    alertas = []
    for t in tasks_andamento + subs_andamento:
        if not t["duedate"]:
            continue
        due = datetime.strptime(t["duedate"], "%Y-%m-%d").date()
        diff = (due - today).days
        if diff < 0:
            alertas.append(f"  [ATRASADA] {t['key']} {t['summary'][:35]} ({-diff}d atrasada)")
        elif diff <= 7:
            alertas.append(f"  [URGENTE] {t['key']} {t['summary'][:35]} (vence em {diff}d)")

    if alertas:
        msg2_lines.append("--- ALERTAS DEADLINE ---")
        msg2_lines.append("")
        for a in alertas:
            msg2_lines.append(a)
        msg2_lines.append("")

    # Footer
    msg2_lines.append("---")
    msg2_lines.append("MHX Digital | Jira KAN Notifier")

    return "\n".join(msg1_lines), "\n".join(msg2_lines)


# ══════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════════════════

def tg_send(bot_token, chat_id, text):
    """Envia mensagem plain text (sem markdown para evitar erros de parse)."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        r = _req("POST", url, json={
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True,
        })
        if r.status_code != 200:
            print(f"  [!!] Telegram erro: {r.status_code} - {r.text[:300]}")
            return False
        time.sleep(0.3)  # rate limit
    return True


# ══════════════════════════════════════════════════════════════════════════
# TASK SCHEDULER (Windows)
# ══════════════════════════════════════════════════════════════════════════

TASK_NAME_8H = "JiraKAN_Telegram_8h"
TASK_NAME_19H = "JiraKAN_Telegram_19h"


def install_scheduler():
    """Cria tarefas no Task Scheduler: 8h e 19h, com 'run on logon if missed'."""
    python_exe = sys.executable
    script = str(SCRIPT_PATH)
    workdir = str(PROJECT_ROOT)

    for task_name, hour in [(TASK_NAME_8H, "08:00"), (TASK_NAME_19H, "19:00")]:
        # Deletar se existe
        subprocess.run(
            ["schtasks", "/Delete", "/TN", task_name, "/F"],
            capture_output=True
        )

        # Criar: daily trigger + StartWhenAvailable (roda ao ligar se perdeu horario)
        # Usamos XML para StartWhenAvailable que nao esta disponivel via /Create flags
        xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Jira KAN Telegram Notifier ({hour})</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-02-19T{hour}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>{script}</Arguments>
      <WorkingDirectory>{workdir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

        xml_path = PROJECT_ROOT / f"_task_{task_name}.xml"
        xml_path.write_text(xml, encoding="utf-16")

        result = subprocess.run(
            ["schtasks", "/Create", "/TN", task_name, "/XML", str(xml_path), "/F"],
            capture_output=True, text=True
        )

        xml_path.unlink(missing_ok=True)

        if result.returncode == 0:
            print(f"  [OK] {task_name} criada ({hour}, diaria, StartWhenAvailable)")
        else:
            print(f"  [!!] {task_name} falhou: {result.stderr.strip()}")


def uninstall_scheduler():
    for task_name in [TASK_NAME_8H, TASK_NAME_19H]:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", task_name, "/F"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  [OK] {task_name} removida")
        else:
            print(f"  [!!] {task_name}: {result.stderr.strip()}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Jira KAN -> Telegram Daily Notifier")
    parser.add_argument("--test", action="store_true", help="Mostra mensagens no terminal sem enviar")
    parser.add_argument("--install", action="store_true", help="Instala no Task Scheduler (8h + 19h)")
    parser.add_argument("--uninstall", action="store_true", help="Remove do Task Scheduler")
    args = parser.parse_args()

    if args.install:
        print("Instalando no Task Scheduler...")
        install_scheduler()
        return

    if args.uninstall:
        print("Removendo do Task Scheduler...")
        uninstall_scheduler()
        return

    jira_base, jira_h, tg_token, tg_chat = load_config()

    # Buscar dados
    print("Buscando issues do Jira KAN...")
    raw = fetch_all_active_issues(jira_base, jira_h)
    tasks, subtasks = parse_issues(raw)
    print(f"  {len(tasks)} tasks + {len(subtasks)} subtasks (nao concluidas)")

    # Montar mensagens
    msg1, msg2 = build_messages(tasks, subtasks)

    if args.test:
        print("\n========== MSG 1: A FAZER ==========")
        print(msg1)
        print("\n========== MSG 2: EM ANDAMENTO ==========")
        print(msg2)
        print("\n[test mode — nao enviado]")
        return

    # Enviar
    print("\nEnviando MSG 1 (A fazer)...")
    ok1 = tg_send(tg_token, tg_chat, msg1)
    print(f"  {'[OK]' if ok1 else '[!!]'}")

    print("Enviando MSG 2 (Em andamento)...")
    ok2 = tg_send(tg_token, tg_chat, msg2)
    print(f"  {'[OK]' if ok2 else '[!!]'}")

    if ok1 and ok2:
        print("\nResumo enviado com sucesso.")
    else:
        print("\nAlgum envio falhou — verifique acima.")
        sys.exit(1)


if __name__ == "__main__":
    main()
