#!/usr/bin/env python3
"""
Mover issues QUANT + produtos para "Em andamento" e criar Epic "Kairi" se necessário.

Uso:
  python scripts/jira_set_in_progress.py

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

EXISTING_ISSUES = [
    "KAN-21", "KAN-22", "KAN-23", "KAN-24", "KAN-25", "KAN-26", "KAN-27",  # QUANT
    "KAN-15",  # NexusP2P
    "KAN-13",  # LexNotify
]

KAIRI = {
    "summary": "Kairi (estratégia — automação)",
    "issuetype": "Epic",
    "component": "QUANT",
    "labels": ["p2", "strategy"],
    "description_text": (
        "Estratégia Kairi — automatização e operação. "
        "Inclui execução, risk/kill-switch e observabilidade."
    ),
}

MAX_RETRIES = 1

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

def _request(method, url, headers, retries=MAX_RETRIES, **kwargs):
    """Wrapper com 1 retry em falhas transitórias (5xx, timeout, connection)."""
    for attempt in range(retries + 1):
        try:
            r = requests.request(method, url, headers=headers, timeout=30, **kwargs)
            if r.status_code >= 500 and attempt < retries:
                time.sleep(1)
                continue
            return r
        except (requests.ConnectionError, requests.Timeout):
            if attempt < retries:
                time.sleep(1)
                continue
            raise
    return r  # fallback (não deveria chegar aqui)


# ── Jira helpers ──────────────────────────────────────────────────────────

def get_status_and_summary(base_url, headers, key):
    r = _request("GET", f"{base_url}/rest/api/3/issue/{key}?fields=status,summary", headers)
    r.raise_for_status()
    f = r.json()["fields"]
    return f["status"]["name"], f["summary"]


def find_transition(base_url, headers, key, target):
    r = _request("GET", f"{base_url}/rest/api/3/issue/{key}/transitions", headers)
    r.raise_for_status()
    transitions = r.json().get("transitions", [])
    for t in transitions:
        if t["name"].strip().lower() == target.strip().lower():
            return t["id"]
    return None, transitions


def do_transition(base_url, headers, key, tid):
    r = _request("POST", f"{base_url}/rest/api/3/issue/{key}/transitions", headers,
                 json={"transition": {"id": tid}})
    if r.status_code == 204:
        return True, "transicao executada"
    return False, f"HTTP {r.status_code}: {r.text[:250]}"


def move_to_in_progress(base_url, headers, key):
    """Tenta mover issue para TARGET_STATUS. Retorna dict de resultado."""
    try:
        status_antes, summary = get_status_and_summary(base_url, headers, key)
    except requests.HTTPError as e:
        return {"key": key, "summary": "?", "antes": "?", "depois": "?",
                "flag": "ERRO", "msg": str(e)[:150]}

    if status_antes.strip().lower() == TARGET_STATUS.strip().lower():
        return {"key": key, "summary": summary, "antes": status_antes,
                "depois": status_antes, "flag": "OK", "msg": "ja estava"}

    result = find_transition(base_url, headers, key, TARGET_STATUS)
    if isinstance(result, tuple):
        _, transitions = result
        nomes = [t["name"] for t in transitions]
        return {"key": key, "summary": summary, "antes": status_antes,
                "depois": status_antes, "flag": "ERRO",
                "msg": f"transicao nao encontrada. Disponiveis: {nomes}"}
    tid = result

    ok, msg = do_transition(base_url, headers, key, tid)
    try:
        status_depois, _ = get_status_and_summary(base_url, headers, key)
    except Exception:
        status_depois = "?"

    flag = "OK" if ok and status_depois.strip().lower() == TARGET_STATUS.strip().lower() else "ERRO"
    return {"key": key, "summary": summary, "antes": status_antes,
            "depois": status_depois, "flag": flag, "msg": msg}


# ── Criar Epic Kairi ─────────────────────────────────────────────────────

def search_kairi(base_url, headers):
    """Busca Epic Kairi via JQL. Retorna key ou None."""
    jql = 'project=KAN AND issuetype=Epic AND summary ~ "Kairi"'
    r = _request("GET", f"{base_url}/rest/api/3/search/jql",
                 headers, params={"jql": jql, "fields": "summary,status", "maxResults": 5})
    r.raise_for_status()
    issues = r.json().get("issues", [])
    for iss in issues:
        if "kairi" in iss["fields"]["summary"].lower():
            return iss["key"]
    return None


def get_component_id(base_url, headers, component_name):
    r = _request("GET", f"{base_url}/rest/api/3/project/KAN/components", headers)
    r.raise_for_status()
    for c in r.json():
        if c["name"].strip().lower() == component_name.strip().lower():
            return c["id"]
    return None


def build_adf(text):
    """Monta ADF mínimo para um parágrafo de texto."""
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def create_kairi(base_url, headers):
    """Cria Epic Kairi. Retorna key da issue criada."""
    comp_id = get_component_id(base_url, headers, KAIRI["component"])
    if not comp_id:
        raise RuntimeError(f"Componente '{KAIRI['component']}' nao encontrado")

    fields = {
        "project": {"key": "KAN"},
        "issuetype": {"name": KAIRI["issuetype"]},
        "summary": KAIRI["summary"],
        "components": [{"id": comp_id}],
        "labels": KAIRI["labels"],
        "description": build_adf(KAIRI["description_text"]),
    }

    r = _request("POST", f"{base_url}/rest/api/3/issue", headers, json={"fields": fields})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Erro ao criar Kairi: HTTP {r.status_code} — {r.text[:300]}")

    return r.json()["key"]


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    base_url, headers = load_auth()
    print(f"Jira:  {base_url}")
    print(f"Alvo:  {TARGET_STATUS}")
    print("=" * 80)

    results = []

    # 1) Issues existentes
    print(f"\n[1/2] Movendo {len(EXISTING_ISSUES)} issues existentes...")
    for key in EXISTING_ISSUES:
        r = move_to_in_progress(base_url, headers, key)
        results.append(r)
        sym = "[OK]" if r["flag"] == "OK" else "[!!]"
        print(f"  {sym} {r['key']}: {r['msg']}")

    # 2) Kairi
    print("\n[2/2] Epic Kairi...")
    kairi_key = search_kairi(base_url, headers)
    if kairi_key:
        print(f"  Kairi ja existe: {kairi_key}")
    else:
        try:
            kairi_key = create_kairi(base_url, headers)
            print(f"  Kairi criada: {kairi_key}")
        except RuntimeError as e:
            results.append({"key": "KAIRI", "summary": KAIRI["summary"],
                            "antes": "-", "depois": "-", "flag": "ERRO", "msg": str(e)[:150]})
            kairi_key = None

    if kairi_key:
        r = move_to_in_progress(base_url, headers, kairi_key)
        results.append(r)
        sym = "[OK]" if r["flag"] == "OK" else "[!!]"
        print(f"  {sym} {r['key']}: {r['msg']}")

    # ── Resumo final ──────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    hdr = f"{'Issue':<10} {'Summary':<38} {'Antes':<14} {'Depois':<14} {'OK?':<5} Msg"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        summ = (r["summary"][:36] + "..") if len(r["summary"]) > 38 else r["summary"]
        print(f"{r['key']:<10} {summ:<38} {r['antes']:<14} {r['depois']:<14} {r['flag']:<5} {r['msg']}")

    ok = sum(1 for r in results if r["flag"] == "OK")
    total = len(results)
    print(f"\n{ok}/{total} OK.")
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
