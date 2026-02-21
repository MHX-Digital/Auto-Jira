#!/usr/bin/env python3
"""
Mover issues do Jira para qualquer status via REST API v3.

Uso:
  python scripts/jira_move_status.py <status> <issue1> [issue2 ...]

Exemplos:
  python scripts/jira_move_status.py "Em andamento" KAN-142 KAN-151
  python scripts/jira_move_status.py "Concluído" KAN-142 KAN-151 KAN-158 KAN-159
  python scripts/jira_move_status.py "A fazer" KAN-142

Status válidos no projeto KAN: "A fazer", "Em andamento", "Concluído"

Requer: requests, python-dotenv (pip install requests python-dotenv)
"""

import argparse
import os
import sys
import base64
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERRO: instale requests -> pip install requests")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ── Auth ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_auth():
    """Carrega BASE_URL e headers de autenticação (.env ou CHATGPT_AUTH.txt)."""

    env_path = PROJECT_ROOT / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")

    if base_url and email and token:
        cred = base64.b64encode(f"{email}:{token}".encode()).decode()
        return base_url, _make_headers(f"Basic {cred}")

    # Fallback: CHATGPT_AUTH.txt
    auth_file = PROJECT_ROOT / "CHATGPT_AUTH.txt"
    if auth_file.exists():
        text = auth_file.read_text(encoding="utf-8")
        auth_value = None
        for line in text.splitlines():
            if "Basic " in line and "API Key" not in line and "Auth Type" not in line:
                auth_value = line[line.index("Basic "):].strip()
                break
        for line in text.splitlines():
            if "Base URL:" in line:
                base_url = line.split("Base URL:")[1].strip().rstrip("/")
                break
        if auth_value and base_url:
            return base_url, _make_headers(auth_value)

    sys.exit(
        "ERRO: nao foi possivel carregar credenciais.\n"
        "Defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN no .env\n"
        "ou coloque CHATGPT_AUTH.txt no diretorio raiz do projeto."
    )


def _make_headers(auth_value):
    return {
        "Authorization": auth_value,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check",
    }


# ── Helpers ───────────────────────────────────────────────────────────────

def get_current_status(base_url, headers, issue_key):
    """Retorna o nome do status atual da issue."""
    url = f"{base_url}/rest/api/3/issue/{issue_key}?fields=status"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["fields"]["status"]["name"]


def find_transition_id(base_url, headers, issue_key, target_status):
    """Retorna (id, nome) da transição correspondente, ou (None, None)."""
    url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    for t in r.json().get("transitions", []):
        if t["name"].strip().lower() == target_status.strip().lower():
            return t["id"], t["name"]
    return None, None


def list_transitions(base_url, headers, issue_key):
    """Retorna lista de nomes de transições disponíveis."""
    url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return [t["name"] for t in r.json().get("transitions", [])]


def do_transition(base_url, headers, issue_key, transition_id):
    """Executa a transição. Retorna (ok: bool, msg: str)."""
    url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
    payload = {"transition": {"id": transition_id}}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code == 204:
        return True, "transicao executada"
    if r.status_code in (403, 401) and "XSRF" in r.text:
        headers["X-Atlassian-Token"] = "no-check"
        r2 = requests.post(url, headers=headers, json=payload, timeout=30)
        if r2.status_code == 204:
            return True, "transicao executada (retry XSRF)"
        return False, f"HTTP {r2.status_code}: {r2.text[:200]}"
    return False, f"HTTP {r.status_code}: {r.text[:200]}"


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Mover issues do Jira KAN para qualquer status.",
        epilog='Exemplo: python scripts/jira_move_status.py "Em andamento" KAN-142 KAN-151',
    )
    parser.add_argument("status", help='Status alvo (ex: "A fazer", "Em andamento", "Concluído")')
    parser.add_argument("issues", nargs="+", help="Issue keys (ex: KAN-142 KAN-151)")
    args = parser.parse_args()

    target_status = args.status
    issues = [k.upper() for k in args.issues]

    base_url, headers = load_auth()
    print(f"Jira:   {base_url}")
    print(f"Issues: {', '.join(issues)}")
    print(f"Alvo:   {target_status}")
    print("-" * 72)

    results = []

    for key in issues:
        try:
            status_antes = get_current_status(base_url, headers, key)
        except requests.HTTPError as e:
            results.append((key, "?", "?", "ERRO", f"ao ler status: {e}"))
            continue

        # Já está no status alvo?
        if status_antes.strip().lower() == target_status.strip().lower():
            results.append((key, status_antes, status_antes, "OK", "ja estava nesse status"))
            continue

        # Busca transição
        tid, tname = find_transition_id(base_url, headers, key, target_status)
        if tid is None:
            disponiveis = list_transitions(base_url, headers, key)
            results.append((key, status_antes, status_antes, "ERRO",
                            f"transicao nao encontrada. Disponiveis: {disponiveis}"))
            continue

        # Executa
        ok, msg = do_transition(base_url, headers, key, tid)

        try:
            status_depois = get_current_status(base_url, headers, key)
        except requests.HTTPError:
            status_depois = "?"

        flag = "OK" if ok and status_depois.strip().lower() == target_status.strip().lower() else "ERRO"
        results.append((key, status_antes, status_depois, flag, msg))

    # ── Resumo ────────────────────────────────────────────────────────
    print()
    hdr = f"{'Issue':<12} {'Antes':<18} {'Depois':<18} {'Result':<6} Mensagem"
    print(hdr)
    print("=" * len(hdr))
    for key, antes, depois, flag, msg in results:
        print(f"{key:<12} {antes:<18} {depois:<18} {flag:<6} {msg}")

    ok_count = sum(1 for r in results if r[3] == "OK")
    total = len(results)
    print(f"\n{ok_count}/{total} issues em '{target_status}'.")
    sys.exit(0 if ok_count == total else 1)


if __name__ == "__main__":
    main()
