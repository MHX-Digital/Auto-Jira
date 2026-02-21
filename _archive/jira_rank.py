"""
Jira Rank - Listar P1, propor ordem, ranquear boards
"""
import json, urllib.request, urllib.error, urllib.parse, time
from jira_config import BASE, HEADERS

def api(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except:
            return e.code, raw

def search_jql(jql, fields="key,summary,status,issuetype,components,labels,parent"):
    all_issues = []
    token = None
    while True:
        params = {"jql": jql, "maxResults": "50", "fields": fields}
        if token:
            params["nextPageToken"] = token
        qs = urllib.parse.urlencode(params)
        code, data = api("GET", f"/rest/api/3/search/jql?{qs}")
        issues = data.get("issues", [])
        all_issues.extend(issues)
        if data.get("isLast", True) or not issues:
            break
        token = data.get("nextPageToken")
        if not token:
            break
    return all_issues

# ============================================================
# PASSO 1: LISTAR P1 AGRUPADOS POR EPIC
# ============================================================
print("=" * 70)
print("PASSO 1 — ISSUES P1 AGRUPADOS POR EPIC")
print("=" * 70)

p1_issues = search_jql("project = KAN AND labels = p1 ORDER BY key ASC")
print(f"\nTotal P1: {len(p1_issues)}\n")

# Agrupar por epic parent
by_epic = {}
for i in p1_issues:
    f = i["fields"]
    parent_key = f.get("parent", {}).get("key", "SEM_EPIC") if f.get("parent") else "SEM_EPIC"
    parent_summary = f.get("parent", {}).get("fields", {}).get("summary", "???") if f.get("parent") else "Sem Epic"
    comp = f["components"][0]["name"] if f.get("components") else "-"

    if parent_key not in by_epic:
        by_epic[parent_key] = {"summary": parent_summary, "component": comp, "issues": []}

    by_epic[parent_key]["issues"].append({
        "key": i["key"],
        "summary": f["summary"],
        "status": f["status"]["name"],
        "labels": f.get("labels", []),
        "component": comp,
    })

for epic_key in sorted(by_epic.keys()):
    info = by_epic[epic_key]
    print(f"  EPIC {epic_key} — {info['summary']} [{info['component']}]")
    for t in info["issues"]:
        lbls = ",".join(t["labels"])
        print(f"    {t['key']:8} | {t['status']:12} | {lbls:15} | {t['summary'][:55]}")
    print()

# Also fetch the playbook (KAN-127) which is p1
playbook = search_jql("project = KAN AND key = KAN-127", "key,summary,labels,components,parent")
if playbook:
    pk = playbook[0]
    pf = pk["fields"]
    has_p1 = "p1" in pf.get("labels", [])
    if has_p1:
        print(f"  STANDALONE (sem epic pai)")
        print(f"    {pk['key']:8} | {'A fazer':12} | p1              | {pf['summary'][:55]}")
        print()

# ============================================================
# PASSO 2: ORDEM DE EXECUCAO (TOP 10)
# ============================================================
print("=" * 70)
print("PASSO 2 — ORDEM DE EXECUCAO TOP 10 (por dependencia)")
print("=" * 70)

# Dependency reasoning:
# 1. KAN-127 (Git Playbook) - MUST BE FIRST: defines how all devs work
# 2. KAN-100 (Supabase auth) - FOUNDATION: everything in LexNotify depends on auth+db
# 3. KAN-108 (Mainnet checklist) - GATE: blocks all Hamza prod work
# 4. KAN-114 (Contrato OTC) - LEGAL GATE: blocks all OTC operations
# 5. KAN-102 (Kanban CRUD) - CORE: main feature of LexNotify, depends on KAN-100
# 6. KAN-101 (WhatsApp) - CORE: second pillar of LexNotify, depends on KAN-100
# 7. KAN-115 (KYT/KYC checklist) - depends on KAN-114 (contract model)
# 8. KAN-109 (Hamza buy/sell) - depends on KAN-108 (mainnet readiness)
# 9. KAN-120 (Deal room fintech) - INDEPENDENT: can start anytime, high value
# 10. KAN-106 (Deploy+rollback) - depends on KAN-100+102, needed before go-live

TOP10 = [
    (1, "KAN-127", "PRODUCT",      "[GIT] Playbook Git<->Jira",                    "Fundacao: define como todo dev trabalha. Zero dependencias. Deve ser lido antes de qualquer commit."),
    (2, "KAN-100", "PRODUCT",      "Integracao Supabase (auth+db+storage)",         "Fundacao tecnica do LexNotify. Auth, banco, storage. Tudo depende disso."),
    (3, "KAN-108", "PRODUCT",      "Checklist mainnet readiness (Hamza)",           "Gate de producao: enquanto nao passar, nenhum deploy em mainnet. Bloqueia KAN-109..113."),
    (4, "KAN-114", "OTC",          "Modelo contrato intermediacao (Pix+banco)",     "Gate juridico: sem contrato validado, nenhuma operacao OTC pode rodar. Bloqueia KAN-115..119."),
    (5, "KAN-102", "PRODUCT",      "Kanban + tarefas (CRUD + transicoes)",          "Feature principal do LexNotify. Depende de KAN-100 (Supabase). Alto valor de negocio."),
    (6, "KAN-101", "PRODUCT",      "Integracao WhatsApp (stub+fluxo)",             "Segundo pilar do LexNotify. Depende de KAN-100. Pode rodar em paralelo com KAN-102."),
    (7, "KAN-115", "OTC",          "Checklist KYT/KYC e evidencias",               "Compliance. Depende de KAN-114 (contrato). Necessario antes de qualquer op real."),
    (8, "KAN-109", "PRODUCT",      "Fluxo compra/venda real Hamza (UI+backend)",   "Feature principal do Hamza. Depende de KAN-108 (mainnet ready). Alto valor."),
    (9, "KAN-120", "LIQUIDATION",  "Deal room 1-pager (Venda Fintech)",            "Independente. Pode comecar a qualquer momento. Potencial de receita rapida."),
    (10,"KAN-106", "PRODUCT",      "Deploy + rollback + runbook (LexNotify)",       "Infraestrutura de deploy. Depende de KAN-100+102. Necessario antes de go-live."),
]

print()
print(f"{'#':>2} | {'Key':8} | {'Board':12} | {'Summary':50} | Justificativa")
print("-" * 140)
for rank, key, comp, summ, reason in TOP10:
    board = "OPERATIONS" if comp in ("OTC", "GOV", "DELIVERY") else "PRODUCT"
    print(f"{rank:>2} | {key:8} | {board:12} | {summ:50} | {reason[:60]}")

print()
print("Dependencias:")
print("  KAN-127 -> (nenhuma)")
print("  KAN-100 -> (nenhuma)")
print("  KAN-108 -> (nenhuma)")
print("  KAN-114 -> (nenhuma)")
print("  KAN-102 -> KAN-100")
print("  KAN-101 -> KAN-100")
print("  KAN-115 -> KAN-114")
print("  KAN-109 -> KAN-108")
print("  KAN-120 -> (nenhuma)")
print("  KAN-106 -> KAN-100, KAN-102")

# Split into boards
BOARD3_TOP6 = ["KAN-127", "KAN-100", "KAN-108", "KAN-102", "KAN-101", "KAN-109"]  # PRODUCT board
BOARD2_TOP4 = ["KAN-114", "KAN-115", "KAN-120", "KAN-106"]  # Wait - KAN-106 and KAN-120...

# Actually let me reconsider: Board 2 = OPERATIONS (GOV+OTC+DELIVERY), Board 3 = PRODUCT (PRODUCT+LIQUIDATION+QUANT)
# KAN-114, KAN-115 = OTC -> Board 2
# KAN-120 = LIQUIDATION -> Board 3
# KAN-106 = PRODUCT -> Board 3

# Correct split:
# Board 3 (PRODUCT): KAN-127, KAN-100, KAN-108, KAN-102, KAN-101, KAN-106 (6 items, all PRODUCT component)
# Board 2 (OPERATIONS): KAN-114, KAN-115 (OTC), and we need 2 more from OTC/DELIVERY/GOV...
# Actually from the top10, only KAN-114 and KAN-115 are OPERATIONS.
# Let me include KAN-116 (fluxo operacional OTC) and KAN-117 (pendencias Foxbit) as next OTC priorities.

BOARD3_ORDER = ["KAN-127", "KAN-100", "KAN-108", "KAN-102", "KAN-101", "KAN-106"]
BOARD2_ORDER = ["KAN-114", "KAN-115", "KAN-116", "KAN-117"]

print()
print(f"Board 3 (PRODUCT) - Top 6: {BOARD3_ORDER}")
print(f"Board 2 (OPERATIONS) - Top 4: {BOARD2_ORDER}")

# ============================================================
# PASSO 3: RANQUEAR BOARDS
# ============================================================
print()
print("=" * 70)
print("PASSO 3 — RANQUEAR BACKLOG DOS BOARDS")
print("=" * 70)

# Jira Agile ranking: PUT /rest/agile/1.0/issue/rank
# Payload: { "issues": ["KAN-100", ...], "rankBeforeIssue": "KAN-xxx" }
# Or: { "issues": ["KAN-100"], "rankBeforeIssue": "FIRST" } -- doesn't exist
# Actually the API is: POST /rest/agile/1.0/issue/rank
# with: { "issues": ["KAN-100"], "rankBeforeIssue": "KAN-xxx" }
# To put at top, we rank before the current first issue in the board.

# Strategy: get current first issue of each board, then rank our items before it.

def get_board_first_issue(board_id):
    """Get the first issue in the board backlog"""
    code, data = api("GET", f"/rest/agile/1.0/board/{board_id}/backlog?maxResults=1&fields=key")
    issues = data.get("issues", [])
    if issues:
        return issues[0]["key"]
    # If backlog is empty, try board issues
    code, data = api("GET", f"/rest/agile/1.0/board/{board_id}/issue?maxResults=1&fields=key")
    issues = data.get("issues", [])
    return issues[0]["key"] if issues else None

def rank_issues(issue_keys, board_id):
    """Rank issues at the top of the board, in order.
    We rank them in REVERSE order, each 'before' the previous, so the first ends up on top."""

    # First, get current top issue to rank before
    code, data = api("GET", f"/rest/agile/1.0/board/{board_id}/issue?maxResults=1&fields=key")
    board_issues = data.get("issues", [])

    if not board_issues:
        print(f"  Board {board_id}: sem issues, pulando ranking")
        return

    current_first = board_issues[0]["key"]
    print(f"  Board {board_id}: issue atual no topo = {current_first}")

    # Rank in reverse order so first item ends at position 1
    for key in reversed(issue_keys):
        payload = {
            "issues": [key],
            "rankBeforeIssue": current_first
        }
        code, resp = api("PUT", "/rest/agile/1.0/issue/rank", payload)
        if code in (200, 204):
            print(f"    {key} ranqueado ANTES de {current_first}: OK")
            current_first = key  # This is now the new top
        else:
            print(f"    {key}: ERRO {code} — {str(resp)[:100]}")
        time.sleep(0.2)

print("\n--- Board 3 (PRODUCT) — Top 6 ---")
rank_issues(BOARD3_ORDER, 3)

print("\n--- Board 2 (OPERATIONS) — Top 4 ---")
rank_issues(BOARD2_ORDER, 2)

# ============================================================
# VERIFICACAO
# ============================================================
print()
print("=" * 70)
print("VERIFICACAO — Top issues de cada board apos ranking")
print("=" * 70)

for board_id, board_name, expected_count in [(3, "PRODUCT", 6), (2, "OPERATIONS", 4)]:
    code, data = api("GET", f"/rest/agile/1.0/board/{board_id}/issue?maxResults={expected_count + 2}&fields=key,summary,labels,components")
    issues = data.get("issues", [])
    print(f"\n  Board {board_id} ({board_name}) — Top {len(issues)} issues:")
    for idx, i in enumerate(issues, 1):
        f = i["fields"]
        comp = f["components"][0]["name"] if f.get("components") else "-"
        lbls = ",".join(f.get("labels", []))
        print(f"    #{idx:2} {i['key']:8} | {comp:12} | {lbls:15} | {f['summary'][:50]}")

print()
print("=" * 70)
print("CONCLUIDO")
print("=" * 70)
