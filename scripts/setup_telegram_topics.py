#!/usr/bin/env python3
"""
Cria Forum Topics no grupo MHX do Telegram.

Pre-requisitos:
  1. Grupo deve ser Supergrupo com Topics habilitado (Admin > Topics > ON)
  2. Bot deve ser admin com permissao can_manage_topics
  3. Variaveis de ambiente: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Uso:
  python scripts/setup_telegram_topics.py

Saida: lista de topic_name -> message_thread_id para configurar no Railway.
"""

import os
import sys
import json
import requests

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

if not BOT_TOKEN or not CHAT_ID:
    print("ERRO: Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
    sys.exit(1)

# Telegram Forum Topic icon colors (set fixo permitido pela API):
# 0x6FB9F0 (blue), 0xFFD67E (yellow), 0xCB86DB (purple),
# 0x8EEE98 (green), 0xFF93B2 (pink), 0xFB6F5F (red)

TOPICS = [
    {"name": "Jira",          "icon_color": 0x6FB9F0, "env": "TOPIC_JIRA"},
    {"name": "MEV Quant",     "icon_color": 0xFF93B2, "env": "TOPIC_MEV"},
    {"name": "ShieldFinance", "icon_color": 0xCB86DB, "env": "TOPIC_SHIELDFINANCE"},
    {"name": "Chat",          "icon_color": 0x8EEE98, "env": "TOPIC_CHAT"},
    {"name": "News",          "icon_color": 0xFFD67E, "env": "TOPIC_NEWS"},
    {"name": "Whale",         "icon_color": 0x6FB9F0, "env": "TOPIC_WHALE"},
    {"name": "Crypto",        "icon_color": 0xFFD67E, "env": "TOPIC_CRYPTO"},
    {"name": "PanicCrypto",   "icon_color": 0xFB6F5F, "env": "TOPIC_PANIC"},
    {"name": "Clients",       "icon_color": 0x8EEE98, "env": "TOPIC_CLIENTS"},
    {"name": "Docs",          "icon_color": 0xCB86DB, "env": "TOPIC_DOCS"},
]


def create_topic(name, icon_color):
    """Cria um forum topic e retorna o message_thread_id."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createForumTopic"
    r = requests.post(url, json={
        "chat_id": CHAT_ID,
        "name": name,
        "icon_color": icon_color,
    }, timeout=15)

    result = r.json()
    if not result.get("ok"):
        print(f"  ERRO '{name}': {result.get('description', result)}")
        return None

    thread_id = result["result"]["message_thread_id"]
    print(f"  OK: '{name}' -> thread_id = {thread_id}")
    return thread_id


def main():
    print(f"Criando {len(TOPICS)} topicos no grupo {CHAT_ID}...\n")

    results = {}
    for topic in TOPICS:
        tid = create_topic(topic["name"], topic["icon_color"])
        if tid is not None:
            results[topic["env"]] = tid

    print(f"\n{'='*60}")
    print("Copie para o Railway (Settings > Variables):")
    print(f"{'='*60}\n")

    for env_key, tid in results.items():
        print(f"  {env_key}={tid}")

    # Salva JSON para referencia
    out_file = os.path.join(os.path.dirname(__file__), "topic_ids.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSalvo em {out_file}")


if __name__ == "__main__":
    main()
