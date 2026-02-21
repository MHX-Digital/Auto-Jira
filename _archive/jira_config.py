"""
Configuracao centralizada para scripts Jira KAN.
Carrega credenciais do .env (sem dependencias externas).
"""
import base64, os, sys

def _load_env(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        print(f"ERRO: .env nao encontrado em {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

BASE = os.environ["JIRA_BASE_URL"]
EMAIL = os.environ["JIRA_EMAIL"]
TOKEN = os.environ["JIRA_API_TOKEN"]
PROJECT = os.environ.get("JIRA_PROJECT_KEY", "KAN")

CRED = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {CRED}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}
