#!/usr/bin/env python3
"""
Mover subtasks KAN para "Em andamento" via REST API v3.

Uso:
  python scripts/jira_move_subtasks_to_in_progress.py

Requer: requests, python-dotenv (pip install requests python-dotenv)
"""

import os
import sys
import base64
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERRO: instale requests -> pip install requests")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ── Config ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_STATUS = "Em andamento"

SUBTASKS = [
    "KAN-143", "KAN-144", "KAN-145", "KAN-146", "KAN-147",
    "KAN-148", "KAN-149", "KAN-150", "KAN-152", "KAN-153",
    "KAN-154", "KAN-155", "KAN-156",
]

# ── Auth ──────────────────────────────────────────────────────────────────

def load_auth():
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")

    if base_url and email and token:
        cred = base64.b64encode(f"{email}:{token}".encode()).decode()
        return base_url, _headers(f"Basic {cred}")

    auth_file = PROJECT_ROOT / "CHATGPT_AUTH.txt"
    if auth_file.exists():
        text = auth_file.read_text(encoding="utf-8")
        auth_val = burl = None
        for line in text.splitlines():
            if "Basic " in line and "API Key" not in line and "Auth Type" not in line:
                auth_val = line[line.index("Basic "):].strip()
            if "Base URL:" in line:
                burl = line.split("Base URL:")[1].strip().rstrip("/")
        if auth_val and burl:
            return burl, _headers(auth_val)

    sys.exit("ERRO: credenciais nao encontradas (.env ou CHATGPT_AUTH.txt)")


def _headers(auth):
    return {
        "Authorization": auth,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check",
    }


# ── HTTP com retry ────────────────────────────────────────────────────────

def _req(method, url, headers, **kwargs):
    for attempt in range(2):
        try:
            r = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            if r.status_code >= 500 and attempt == 0:
                time.sleep(1)
                continue
            return r
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 0:
                time.sleep(1)
                continue
            raise
    return r


# ── Jira helpers ──────────────────────────────────────────────────────────

def get_issue_info(base_url, headers, key):
    r = _req("GET", f"{base_url}/rest/api/3/issue/{key}?fields=status,summary,issuetype,parent", headers)
    r.raise_for_status()
    f = r.json()["fields"]
    parent_key = f.get("parent", {}).get("key", "-") if f.get("parent") else "-"
    return {
        "status": f["status"]["name"],
        "summary": f["summary"],
        "type": f["issuetype"]["name"],
        "parent": parent_key,
    }


def find_transition_id(base_url, headers, key):
    r = _req("GET", f"{base_url}/rest/api/3/issue/{key}/transitions", headers)
    r.raise_for_status()
    transitions = r.json().get("transitions", [])
    for t in transitions:
        if t["name"].strip().lower() == TARGET_STATUS.strip().lower():
            return t["id"], None
    return None, [t["name"] for t in transitions]


def do_transition(base_url, headers, key, tid):
    r = _req("POST", f"{base_url}/rest/api/3/issue/{key}/transitions", headers,
             json={"transition": {"id": tid}})
    if r.status_code == 204:
        return True, "transicao executada"
    return False, f"HTTP {r.status_code}: {r.text[:200]}"


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    base_url, headers = load_auth()
    print(f"Jira:      {base_url}")
    print(f"Subtasks:  {len(SUBTASKS)}")
    print(f"Alvo:      {TARGET_STATUS}")
    print("=" * 90)

    results = []

    for key in SUBTASKS:
        # Ler estado atual
        try:
            info = get_issue_info(base_url, headers, key)
        except requests.HTTPError as e:
            results.append((key, "?", "-", "?", "?", "ERRO", str(e)[:120]))
            print(f"  [!!] {key}: erro ao ler — {e}")
            continue

        status_antes = info["status"]
        summary = info["summary"]
        parent = info["parent"]

        # Ja esta?
        if status_antes.strip().lower() == TARGET_STATUS.strip().lower():
            results.append((key, summary, parent, status_antes, status_antes, "OK", "ja estava"))
            print(f"  [OK] {key}: ja estava")
            continue

        # Buscar transicao
        tid, available = find_transition_id(base_url, headers, key)
        if tid is None:
            results.append((key, summary, parent, status_antes, status_antes, "ERRO",
                            f"sem transicao. Disponiveis: {available}"))
            print(f"  [!!] {key}: transicao nao encontrada")
            continue

        # Executar
        ok, msg = do_transition(base_url, headers, key, tid)

        # Validar
        try:
            info2 = get_issue_info(base_url, headers, key)
            status_depois = info2["status"]
        except Exception:
            status_depois = "?"

        flag = "OK" if ok and status_depois.strip().lower() == TARGET_STATUS.strip().lower() else "ERRO"
        results.append((key, summary, parent, status_antes, status_depois, flag, msg))
        print(f"  [{flag}] {key}: {msg}")

    # ── Resumo ────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("RESUMO")
    print("=" * 90)
    hdr = f"{'Key':<10} {'Summary':<32} {'Parent':<10} {'Antes':<14} {'Depois':<14} {'OK?':<5} Msg"
    print(hdr)
    print("-" * len(hdr))
    for key, summ, parent, antes, depois, flag, msg in results:
        s = (summ[:30] + "..") if len(summ) > 32 else summ
        print(f"{key:<10} {s:<32} {parent:<10} {antes:<14} {depois:<14} {flag:<5} {msg}")

    ok_count = sum(1 for r in results if r[5] == "OK")
    print(f"\n{ok_count}/{len(results)} OK.")
    sys.exit(0 if ok_count == len(results) else 1)


if __name__ == "__main__":
    main()
