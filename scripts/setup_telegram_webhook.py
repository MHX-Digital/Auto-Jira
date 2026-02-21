#!/usr/bin/env python3
"""
Setup Telegram Bot Webhook.

Registra o webhook do Telegram apontando para o Railway app.

Uso:
  python scripts/setup_telegram_webhook.py --url https://YOUR-APP.up.railway.app
  python scripts/setup_telegram_webhook.py --url https://YOUR-APP.up.railway.app --delete
  python scripts/setup_telegram_webhook.py --info

Requer: requests, python-dotenv (opcional)
"""

import os
import sys
import argparse
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERRO: pip install requests")

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(description="Setup Telegram Bot Webhook")
    parser.add_argument("--url", help="URL base do app (ex: https://app.up.railway.app)")
    parser.add_argument("--delete", action="store_true", help="Remove o webhook")
    parser.add_argument("--info", action="store_true", help="Mostra info do webhook atual")
    args = parser.parse_args()

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    webhook_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

    if not bot_token:
        sys.exit("ERRO: TELEGRAM_BOT_TOKEN nao definido")

    api = f"https://api.telegram.org/bot{bot_token}"

    if args.info:
        r = requests.get(f"{api}/getWebhookInfo", timeout=10)
        print(r.json())
        return

    if args.delete:
        r = requests.post(f"{api}/deleteWebhook", timeout=10)
        data = r.json()
        if data.get("ok"):
            print("[OK] Webhook removido")
        else:
            print(f"[!!] Erro: {data}")
        return

    if not args.url:
        sys.exit("ERRO: --url obrigatorio (ex: --url https://app.up.railway.app)")

    webhook_url = f"{args.url.rstrip('/')}/webhook/telegram"
    payload = {"url": webhook_url}
    if webhook_secret:
        payload["secret_token"] = webhook_secret

    print(f"Registrando webhook: {webhook_url}")
    r = requests.post(f"{api}/setWebhook", json=payload, timeout=10)
    data = r.json()

    if data.get("ok"):
        print("[OK] Webhook registrado com sucesso")
        if webhook_secret:
            print(f"[OK] Secret token configurado")
    else:
        print(f"[!!] Erro: {data}")

    # Verify
    r = requests.get(f"{api}/getWebhookInfo", timeout=10)
    info = r.json().get("result", {})
    print(f"\nWebhook info:")
    print(f"  URL: {info.get('url', '?')}")
    print(f"  Has secret: {info.get('has_custom_certificate', False)}")
    print(f"  Pending updates: {info.get('pending_update_count', 0)}")


if __name__ == "__main__":
    main()
