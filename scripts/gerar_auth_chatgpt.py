"""
Gera credencial Base64 para ChatGPT Actions + Jira Cloud.
Carrega do .env automaticamente e salva CHATGPT_AUTH.txt.

Uso:
  python gerar_auth_chatgpt.py
"""
import base64, os, sys, urllib.request, json

DIR = os.path.dirname(os.path.abspath(__file__))

def load_env():
    env_path = os.path.join(DIR, ".env")
    if not os.path.exists(env_path):
        print(f"ERRO: .env nao encontrado em {env_path}")
        sys.exit(1)
    vals = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals

def main():
    env = load_env()
    email = env.get("JIRA_EMAIL")
    token = env.get("JIRA_API_TOKEN")
    base_url = env.get("JIRA_BASE_URL", "https://mhxdigital.atlassian.net")

    if not email or not token:
        print("ERRO: JIRA_EMAIL e JIRA_API_TOKEN devem estar no .env")
        sys.exit(1)

    b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
    auth_value = f"Basic {b64}"

    # Validar contra Jira
    print("Validando credencial...")
    try:
        req = urllib.request.Request(f"{base_url}/rest/api/3/myself")
        req.add_header("Authorization", auth_value)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            user = data.get("displayName", "???")
            acct = data.get("accountId", "???")
            print(f"  OK: {user} ({email}) — accountId: {acct}")
            valido = True
    except Exception as e:
        print(f"  FALHA: {e}")
        valido = False

    # Montar conteudo do TXT
    lines = [
        "=== CHATGPT ACTIONS — JIRA CLOUD ===",
        "",
        "Cole estas configuracoes no ChatGPT > Actions > Authentication:",
        "",
        "  Authentication Type:  API Key",
        "  Auth Type:            Custom",
        "  Custom Header Name:   Authorization",
        f"  API Key:              {auth_value}",
        "",
        "---",
        "",
        f"Base URL:    {base_url}",
        f"Email:       {email}",
        f"Token:       {token[:15]}...{token[-8:]}",
        f"Status:      {'VALIDO' if valido else 'INVALIDO — renovar token'}",
        "",
        "Para renovar: https://id.atlassian.com/manage-profile/security/api-tokens",
    ]
    content = "\n".join(lines) + "\n"

    # Salvar arquivo
    out_path = os.path.join(DIR, "CHATGPT_AUTH.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print()
    print(content)
    print(f"Salvo em: {out_path}")

if __name__ == "__main__":
    main()
