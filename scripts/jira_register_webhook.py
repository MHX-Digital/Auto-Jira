#!/usr/bin/env python3
"""
Registra/lista/deleta webhooks no Jira Cloud para notificacoes Telegram.

Uso:
  python scripts/jira_register_webhook.py --register <RAILWAY_URL>
  python scripts/jira_register_webhook.py --list
  python scripts/jira_register_webhook.py --delete <WEBHOOK_ID>
  python scripts/jira_register_webhook.py --test <RAILWAY_URL>

Exemplos:
  python scripts/jira_register_webhook.py --register https://jira-telegram-webhook-xxx.up.railway.app
  python scripts/jira_register_webhook.py --list
  python scripts/jira_register_webhook.py --delete 10001
  python scripts/jira_register_webhook.py --test https://jira-telegram-webhook-xxx.up.railway.app

Requer: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN no .env
"""

import os
import sys
import json
import base64
import argparse
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


def get_config():
    env_path = PROJECT_ROOT / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)

    jira_base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    if not (jira_base and email and token):
        sys.exit("ERRO: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN nao definidos no .env")

    cred = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {cred}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return jira_base, headers


def list_webhooks(jira_base, headers):
    """Lista todos os webhooks registrados."""
    url = f"{jira_base}/rest/webhooks/1.0/webhook"
    r = requests.get(url, headers=headers, timeout=30)

    if r.status_code == 403:
        print("[!!] Acesso negado. Webhooks REST API requer admin ou app OAuth.")
        print("     Para projetos team-managed, registre o webhook manualmente:")
        print(f"     {jira_base}/plugins/servlet/webhooks")
        return

    if r.status_code != 200:
        print(f"[!!] Erro HTTP {r.status_code}: {r.text[:300]}")
        return

    webhooks = r.json()
    if not webhooks:
        print("Nenhum webhook registrado.")
        return

    print(f"Webhooks registrados ({len(webhooks)}):\n")
    for wh in webhooks:
        print(f"  ID: {wh.get('self', '').split('/')[-1]}")
        print(f"  Nome: {wh.get('name', '?')}")
        print(f"  URL: {wh.get('url', '?')}")
        print(f"  Eventos: {', '.join(wh.get('events', []))}")
        print(f"  Ativo: {wh.get('enabled', '?')}")
        print()


def register_webhook(jira_base, headers, railway_url):
    """Registra webhook no Jira via REST API."""
    railway_url = railway_url.rstrip("/")
    webhook_url = f"{railway_url}/webhook/jira"

    payload = {
        "name": "Jira -> Telegram Notifications",
        "url": webhook_url,
        "events": [
            "jira:issue_created",
            "jira:issue_updated",
            "comment_created",
            "jira:issue_deleted",
        ],
        "filters": {
            "issue-related-events-section": f"project = {os.getenv('JIRA_PROJECT_KEY', 'KAN')}"
        },
        "excludeBody": False,
    }

    url = f"{jira_base}/rest/webhooks/1.0/webhook"
    print(f"Registrando webhook: {webhook_url}")
    print(f"Eventos: {', '.join(payload['events'])}")
    print()

    r = requests.post(url, headers=headers, json=payload, timeout=30)

    if r.status_code == 403:
        print("[!!] Acesso negado. A REST API de webhooks requer permissao de admin.")
        print()
        print("=== REGISTRO MANUAL ===")
        print(f"1. Acesse: {jira_base}/plugins/servlet/webhooks")
        print("2. Clique em 'Create a webhook'")
        print(f"3. Nome: Jira -> Telegram Notifications")
        print(f"4. URL: {webhook_url}")
        print(f"5. JQL Filter: project = KAN")
        print("6. Marque os eventos:")
        print("   - Issue: created, updated, deleted")
        print("   - Comment: created")
        print("7. Salve")
        return

    if r.status_code in (200, 201):
        result = r.json()
        wh_id = result.get("self", "").split("/")[-1]
        print(f"[OK] Webhook registrado com sucesso!")
        print(f"     ID: {wh_id}")
        print(f"     URL: {webhook_url}")
    else:
        print(f"[!!] Erro HTTP {r.status_code}: {r.text[:500]}")


def delete_webhook(jira_base, headers, webhook_id):
    """Deleta um webhook pelo ID."""
    url = f"{jira_base}/rest/webhooks/1.0/webhook/{webhook_id}"
    r = requests.delete(url, headers=headers, timeout=30)

    if r.status_code == 204:
        print(f"[OK] Webhook {webhook_id} deletado.")
    elif r.status_code == 403:
        print("[!!] Acesso negado.")
    else:
        print(f"[!!] Erro HTTP {r.status_code}: {r.text[:300]}")


def test_railway(railway_url):
    """Testa se o servico Railway esta respondendo."""
    railway_url = railway_url.rstrip("/")

    # Health check
    print(f"Testando health check: {railway_url}/")
    try:
        r = requests.get(f"{railway_url}/", timeout=15)
        if r.status_code == 200:
            data = r.json()
            print(f"[OK] Servico online!")
            print(f"     Status: {data.get('status')}")
            print(f"     Uptime: {data.get('uptime')}")
        else:
            print(f"[!!] HTTP {r.status_code}: {r.text[:200]}")
            return
    except requests.RequestException as e:
        print(f"[!!] Conexao falhou: {e}")
        return

    # Simulate webhook
    print(f"\nTestando webhook endpoint: {railway_url}/webhook/jira")
    test_payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "KAN-999",
            "fields": {
                "summary": "TESTE - Webhook Connectivity Check",
                "creator": {"displayName": "Test Script"},
                "issuetype": {"name": "Tarefa"},
                "priority": {"name": "Medium"},
            },
        },
        "user": {"displayName": "Test Script"},
        "changelog": {
            "items": [
                {
                    "field": "status",
                    "fromString": "A fazer",
                    "toString": "Em andamento",
                }
            ]
        },
    }

    try:
        r = requests.post(
            f"{railway_url}/webhook/jira",
            json=test_payload,
            timeout=15,
        )
        print(f"  Resposta: HTTP {r.status_code} - {r.text[:200]}")
        if r.status_code == 200:
            print("[OK] Webhook endpoint funcionando! Verifique o Telegram.")
        elif r.status_code == 401:
            print("[OK] Endpoint respondeu (401 = secret exigido, normal)")
        else:
            print(f"[!!] Resposta inesperada")
    except requests.RequestException as e:
        print(f"[!!] Falhou: {e}")


def main():
    parser = argparse.ArgumentParser(description="Gerenciar webhooks Jira -> Telegram")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--register", metavar="RAILWAY_URL", help="Registrar webhook")
    group.add_argument("--list", action="store_true", help="Listar webhooks")
    group.add_argument("--delete", metavar="WEBHOOK_ID", help="Deletar webhook por ID")
    group.add_argument("--test", metavar="RAILWAY_URL", help="Testar servico Railway")
    args = parser.parse_args()

    if args.test:
        test_railway(args.test)
        return

    jira_base, headers = get_config()

    if args.list:
        list_webhooks(jira_base, headers)
    elif args.register:
        register_webhook(jira_base, headers, args.register)
    elif args.delete:
        delete_webhook(jira_base, headers, args.delete)


if __name__ == "__main__":
    main()
