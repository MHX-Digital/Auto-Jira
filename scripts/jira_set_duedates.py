#!/usr/bin/env python3
"""
Atribuir due dates nas issues filhas de KAN-13 conforme plano 30/60/90 dias.

Uso:  python scripts/jira_set_duedates.py
"""

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


def _req(method, url, headers, **kw):
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


# ── Plano de datas ────────────────────────────────────────────────────────
# Hoje: 2026-02-18
# P0 = 30 dias  -> 2026-03-20
# P1 = 60 dias  -> 2026-04-19
# P2 = 90 dias  -> 2026-05-19

DUEDATES = {
    # P0 — Fase 1 (Dias 1-30)
    "KAN-100": "2026-03-20",  # Supabase
    "KAN-101": "2026-03-20",  # WhatsApp estabilizar
    "KAN-102": "2026-03-20",  # Kanban audiencias
    "KAN-106": "2026-03-20",  # Deploy
    "KAN-107": "2026-03-20",  # Onboarding
    "KAN-162": "2026-03-20",  # CRM Minimo
    "KAN-163": "2026-03-20",  # Billing

    # P1 — Fase 2 (Dias 31-60)
    "KAN-103": "2026-04-19",  # Upload docs
    "KAN-105": "2026-04-19",  # Testes integracao
    "KAN-164": "2026-04-19",  # Webhook WhatsApp
    "KAN-165": "2026-04-19",  # Inbox WhatsApp

    # P2 — Fase 3 (Dias 61-90)
    "KAN-55":  "2026-05-19",  # SOP
    "KAN-57":  "2026-05-19",  # Riscos
    "KAN-104": "2026-05-19",  # Automacoes
    "KAN-166": "2026-05-19",  # IA Draft
    "KAN-167": "2026-05-19",  # Dashboard
}


def main():
    base, headers = load_auth()
    print(f"Jira: {base}")
    print(f"Atribuindo due dates a {len(DUEDATES)} issues...")
    print("=" * 75)

    results = []

    for key, due in DUEDATES.items():
        r = _req("PUT", f"{base}/rest/api/3/issue/{key}", headers,
                 json={"fields": {"duedate": due}})
        if r.status_code == 204:
            # Confirmar
            r2 = _req("GET", f"{base}/rest/api/3/issue/{key}?fields=summary,duedate,labels", headers)
            r2.raise_for_status()
            f = r2.json()["fields"]
            actual_due = f.get("duedate", "?")
            labels = ",".join(f.get("labels", []))
            summ = f["summary"][:45]
            results.append((key, summ, labels, due, actual_due, "OK"))
            print(f"  [OK] {key}: duedate = {actual_due}")
        else:
            results.append((key, "?", "?", due, "?", f"HTTP {r.status_code}"))
            print(f"  [!!] {key}: HTTP {r.status_code} — {r.text[:150]}")

    # Resumo
    print("\n" + "=" * 75)
    print("RESUMO")
    print("=" * 75)
    hdr = f"{'Key':<10} {'Labels':<10} {'Due date':<12} {'OK?':<5} Summary"
    print(hdr)
    print("-" * len(hdr))
    for key, summ, labels, due, actual, flag in results:
        s = (summ[:40] + "..") if len(summ) > 42 else summ
        print(f"{key:<10} {labels:<10} {actual:<12} {flag:<5} {s}")

    ok = sum(1 for r in results if r[5] == "OK")
    print(f"\n{ok}/{len(results)} OK.")


if __name__ == "__main__":
    main()
