"""
Jira Executor - Resolver repos pendentes no mapa KAN-128
"""
import json, urllib.request, urllib.error, urllib.parse, time

from jira_config import BASE, PROJECT, HEADERS

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

def search_jql(jql, fields="key,summary,issuetype,components,labels,description,status"):
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

def adf(text):
    paragraphs = text.strip().split("\n")
    content = []
    for line in paragraphs:
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            content.append({
                "type": "bulletList",
                "content": [{
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": line[2:]}]}]
                }]
            })
        else:
            content.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
    return {"type": "doc", "version": 1, "content": content}

def adf_rich(blocks):
    content = []
    for b in blocks:
        btype = b.get("type", "paragraph")
        if btype == "heading":
            content.append({
                "type": "heading", "attrs": {"level": b.get("level", 3)},
                "content": [{"type": "text", "text": b["text"]}]
            })
        elif btype == "paragraph":
            tc = [{"type": "text", "text": b["text"]}]
            if b.get("bold"):
                tc = [{"type": "text", "text": b["text"], "marks": [{"type": "strong"}]}]
            content.append({"type": "paragraph", "content": tc})
        elif btype == "bulletList":
            items = []
            for t in b["items"]:
                items.append({"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": t}]}
                ]})
            content.append({"type": "bulletList", "content": items})
        elif btype == "rule":
            content.append({"type": "rule"})
    return {"type": "doc", "version": 1, "content": content}

def create_issue(summary, issuetype, component, labels, desc_text, parent_key=None):
    fields = {
        "project": {"key": PROJECT},
        "summary": summary,
        "issuetype": {"name": issuetype},
        "components": [{"name": component}],
        "labels": labels,
        "description": adf(desc_text),
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    code, resp = api("POST", "/rest/api/3/issue", {"fields": fields})
    if code == 201:
        return resp.get("key")
    else:
        print(f"  ERRO {code} criando '{summary}': {resp}")
        return None

# ============================================================
# PASSO 1: DETECTAR EPICS EXISTENTES
# ============================================================
print("=" * 70)
print("PASSO 1 - DETECTAR EPICS PARA REPOS PENDENTES")
print("=" * 70)

# Buscar todos os epics
all_epics = search_jql("project = KAN AND issuetype = Epic ORDER BY key ASC")
print(f"\nTotal epics existentes: {len(all_epics)}\n")

# Index for quick lookup
epic_index = {}
for e in all_epics:
    epic_index[e["key"]] = {
        "summary": e["fields"]["summary"],
        "components": [c["name"] for c in e["fields"].get("components", [])],
        "labels": e["fields"].get("labels", []),
    }

# Search for matches
SEARCHES = {
    "MHX-Digital": ["MHX", "Infra", "DevOps", "Automacao"],
    "lfg-adv": ["lfg", "adv", "juridico", "advocacia"],
    "x-golden": ["golden", "x-golden", "cliente"],
    "Kahincorp-AI": ["Kahincorp", "kNN", "Inception", "IA"],
}

print("Buscando matches por similaridade...\n")
matches = {}

for repo, keywords in SEARCHES.items():
    found = None
    for key, info in epic_index.items():
        summ_lower = info["summary"].lower()
        for kw in keywords:
            if kw.lower() in summ_lower:
                found = (key, info["summary"], "MATCH por keyword: " + kw)
                break
        if found:
            break
    matches[repo] = found
    if found:
        print(f"  {repo}: ENCONTRADO -> {found[0]} '{found[1]}' ({found[2]})")
    else:
        print(f"  {repo}: NAO ENCONTRADO -> criar novo epic")

# Kahincorp-AI: check KAN-16 (InceptionPsi) specifically
print("\n  Verificacao especial Kahincorp-AI vs KAN-16 (InceptionPsi):")
kan16 = epic_index.get("KAN-16", {})
print(f"    KAN-16 summary: '{kan16.get('summary', '?')}'")
print(f"    KAN-16 component: {kan16.get('components', [])}")
print(f"    -> InceptionPsi e sobre 'descoberta -> V1', pode nao ser Kahincorp-AI")
print(f"    -> Decisao: criar epic separado para Kahincorp-AI (P&D IA independente)")

# Override: Kahincorp-AI nao e InceptionPsi, criar separado
if matches.get("Kahincorp-AI") and matches["Kahincorp-AI"][0] == "KAN-26":
    # kNN match, mas kNN e outra coisa. Criar separado.
    print(f"    -> kNN (KAN-26) e estrategia de trading, nao Kahincorp-AI. Criar separado.")
    matches["Kahincorp-AI"] = None

# ============================================================
# Criar epics que faltam
# ============================================================
print("\n--- Criando epics novos ---")

NEW_EPICS = {
    "MHX-Digital": {
        "summary": "MHX-Digital — Infra & Automacao Interna",
        "component": "PRODUCT",
        "labels": ["repo_mhx_digital", "infra", "p2"],
        "description": "Objetivo: Manter e evoluir a infraestrutura interna da MHX Digital (CI/CD, automacao, tooling, monitoramento).\nEscopo: Pipelines de deploy, scripts de automacao, infra cloud, monitoramento, documentacao DevOps.\nDone: Infra estavel, pipelines funcionando, documentacao atualizada.",
    },
    "lfg-adv": {
        "summary": "lfg-adv — Entregas / Juridico",
        "component": "DELIVERY",
        "labels": ["repo_lfg_adv", "p3"],
        "description": "Objetivo: Gerenciar entregas e demandas do escritorio LFG Advocacia.\nEscopo: Desenvolvimento de sistemas, automacoes, entregas de tecnologia para o cliente LFG.\nDone: Entregas aceitas pelo cliente, documentadas e faturadas.",
    },
    "x-golden": {
        "summary": "x-golden — Cliente/Entrega",
        "component": "DELIVERY",
        "labels": ["repo_x_golden", "p3"],
        "description": "Objetivo: Gerenciar entregas e demandas do cliente/projeto X-Golden.\nEscopo: Desenvolvimento, integracao, entregas de tecnologia.\nDone: Entregas aceitas, documentadas e faturadas.",
    },
    "Kahincorp-AI": {
        "summary": "Kahincorp-AI — P&D / IA",
        "component": "QUANT",
        "labels": ["repo_kahincorp_ai", "p3"],
        "description": "Objetivo: Pesquisa e desenvolvimento de solucoes de IA (Kahincorp).\nEscopo: Modelos de ML/IA, experimentacao, prototipagem, validacao.\nDone: Modelos validados com metricas, relatorio de viabilidade, decisao go/no-go.",
    },
}

created_epics = {}
reused_epics = {}

for repo, match in matches.items():
    if match:
        reused_epics[repo] = match[0]
        print(f"  {repo}: REUTILIZANDO {match[0]} ('{match[1]}')")
    else:
        cfg = NEW_EPICS[repo]
        key = create_issue(cfg["summary"], "Epic", cfg["component"], cfg["labels"], cfg["description"])
        if key:
            created_epics[repo] = key
            print(f"  {repo}: CRIADO {key} — {cfg['summary']}")
        else:
            print(f"  {repo}: FALHA ao criar!")
        time.sleep(0.3)

# Final map
FINAL_MAP = {}
for repo in ["MHX-Digital", "lfg-adv", "x-golden", "Kahincorp-AI"]:
    FINAL_MAP[repo] = reused_epics.get(repo) or created_epics.get(repo)

print("\nMapa final:")
for repo, key in FINAL_MAP.items():
    print(f"  {repo} -> {key}")


# ============================================================
# PASSO 2: KIT MINIMO (2 tasks por epic novo)
# ============================================================
print()
print("=" * 70)
print("PASSO 2 - KIT MINIMO (2 tasks por epic novo)")
print("=" * 70)

kit_results = []

for repo, epic_key in created_epics.items():
    cfg = NEW_EPICS[repo]
    comp = cfg["component"]
    labels = cfg["labels"]
    print(f"\n  --- {repo} ({epic_key}) ---")

    # Task A: SOP + DoR/DoD
    desc_a = f"DoR (Definition of Ready):\n- Objetivo claro em 1 frase\n- Criterios de aceite (3-7 bullets)\n- Dono responsavel definido\n- Dependencias listadas\n\nDoD (Definition of Done):\n- Criterios de aceite atendidos\n- Teste minimo executado\n- Documentacao atualizada se necessario\n- Deploy ou entrega realizada\n\nChecklist:\n- [ ] Escopo definido\n- [ ] Responsavel atribuido\n- [ ] Prazo definido\n- [ ] Entrega validada"
    k1 = create_issue(f"[{repo}] SOP + DoR/DoD", "Tarefa", comp, labels, desc_a, epic_key)
    kit_results.append(("SOP", repo, epic_key, k1))
    time.sleep(0.3)

    # Task B: Backlog inicial
    desc_b = f"Backlog inicial para {repo} (preencher com itens reais):\n- Mapear estado atual do repositorio\n- Identificar divida tecnica\n- Listar funcionalidades pendentes\n- Definir prioridades de curto prazo\n- Documentar arquitetura atual\n- Configurar CI/CD (se nao existir)\n- Criar README atualizado\n- Definir padrao de branches e commits\n- Mapear dependencias externas\n- Definir metricas de qualidade"
    k2 = create_issue(f"[{repo}] Backlog inicial (ate 10 itens)", "Tarefa", comp, labels, desc_b, epic_key)
    kit_results.append(("Backlog", repo, epic_key, k2))
    time.sleep(0.3)


# ============================================================
# PASSO 3: ATUALIZAR KAN-128
# ============================================================
print()
print("=" * 70)
print("PASSO 3 - ATUALIZAR KAN-128 (Mapa Repo->Epic)")
print("=" * 70)

# Build updated description for KAN-128
updated_desc = adf_rich([
    {"type": "heading", "level": 2, "text": "Mapa Repositorio -> Epic (KAN) — ATUALIZADO"},
    {"type": "paragraph", "text": "Este documento mapeia cada repositorio Git para o Epic correspondente no Jira. Use para saber onde vincular commits e PRs."},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "Repos PRODUCT"},

    {"type": "paragraph", "text": "LexNotify", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-13 — LexNotify AI (V1 -> Beta -> Prod)",
        "Component: PRODUCT",
        "Sprint-0: KAN-100..KAN-107",
    ]},

    {"type": "paragraph", "text": "Hamza Carbon", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-14 — Hamza Carbon (testnet -> mainnet/prod)",
        "Component: PRODUCT",
        "Sprint-0: KAN-108..KAN-113",
    ]},

    {"type": "paragraph", "text": "NexusP2P", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-15 — NexusP2P (conclusao V1)",
        "Component: PRODUCT",
    ]},

    {"type": "paragraph", "text": "MHX-Digital", "bold": True},
    {"type": "bulletList", "items": [
        f"Epic: {FINAL_MAP['MHX-Digital']} — MHX-Digital — Infra & Automacao Interna",
        "Component: PRODUCT",
        "Labels: repo_mhx_digital, infra, p2",
    ]},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "Repos DELIVERY"},

    {"type": "paragraph", "text": "SideWallet", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-10 — Dev - SideWallet",
        "Component: DELIVERY",
    ]},

    {"type": "paragraph", "text": "BahiaGold", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-11 — Dev - BahiaGold",
        "Component: DELIVERY",
    ]},

    {"type": "paragraph", "text": "lfg-adv", "bold": True},
    {"type": "bulletList", "items": [
        f"Epic: {FINAL_MAP['lfg-adv']} — lfg-adv — Entregas / Juridico",
        "Component: DELIVERY",
        "Labels: repo_lfg_adv, p3",
    ]},

    {"type": "paragraph", "text": "x-golden", "bold": True},
    {"type": "bulletList", "items": [
        f"Epic: {FINAL_MAP['x-golden']} — x-golden — Cliente/Entrega",
        "Component: DELIVERY",
        "Labels: repo_x_golden, p3",
    ]},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "Repos LIQUIDATION"},

    {"type": "paragraph", "text": "VotoMap", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-20 — Venda VotoMap",
        "Component: LIQUIDATION",
        "Nota: se for dev ativo (nao venda), criar epic separado",
    ]},

    {"type": "paragraph", "text": "APP Fintech", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-18 — Venda APP Fintech",
        "Component: LIQUIDATION",
        "Sprint-0: KAN-120..KAN-126",
    ]},

    {"type": "paragraph", "text": "Vrumm", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-19 — Venda Vrumm",
        "Component: LIQUIDATION",
    ]},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "Repos QUANT / P&D"},

    {"type": "paragraph", "text": "Kahincorp-AI", "bold": True},
    {"type": "bulletList", "items": [
        f"Epic: {FINAL_MAP['Kahincorp-AI']} — Kahincorp-AI — P&D / IA",
        "Component: QUANT",
        "Labels: repo_kahincorp_ai, p3",
    ]},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "Repos OTC"},

    {"type": "paragraph", "text": "OTC Compliance", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-6 — OTC e KYT Compliance",
        "Component: OTC",
        "Sprint-0: KAN-114..KAN-119",
    ]},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "Regra para repos sem epic"},
    {"type": "bulletList", "items": [
        "Use KAN-12 (Dev - Avulsos / intake) como catch-all SOMENTE para repos novos sem epic",
        "Assim que o repo ganhar relevancia, crie um epic dedicado",
        "Nunca commite sem referencia a algum KAN-xxx",
    ]},
])

code = api("PUT", "/rest/api/3/issue/KAN-128", {"fields": {"description": updated_desc}})
print(f"  KAN-128 atualizado: HTTP {code[0]}")


# ============================================================
# PASSO 4: RELATORIO FINAL
# ============================================================
print()
print("=" * 70)
print("PASSO 4 - RELATORIO FINAL")
print("=" * 70)

print("\n--- Epics reutilizados ---")
if reused_epics:
    for repo, key in reused_epics.items():
        info = epic_index.get(key, {})
        print(f"  {repo} -> {key} '{info.get('summary', '?')}'")
else:
    print("  (nenhum)")

print("\n--- Epics criados ---")
for repo, key in created_epics.items():
    cfg = NEW_EPICS[repo]
    print(f"  {repo}:")
    print(f"    Epic: {key} — {cfg['summary']}")
    print(f"    Component: {cfg['component']}")
    print(f"    Labels: {cfg['labels']}")

print("\n--- Tasks filhas criadas ---")
for task_type, repo, epic_key, task_key in kit_results:
    print(f"  {task_key} | [{repo}] {task_type} | parent={epic_key}")

print("\n--- Mapa final completo ---")
FULL_MAP = {
    "LexNotify": "KAN-13",
    "Hamza Carbon": "KAN-14",
    "NexusP2P": "KAN-15",
    "SideWallet": "KAN-10",
    "BahiaGold": "KAN-11",
    "VotoMap": "KAN-20",
    "APP Fintech": "KAN-18",
    "Vrumm": "KAN-19",
}
FULL_MAP.update(FINAL_MAP)
for repo, key in sorted(FULL_MAP.items()):
    print(f"  {repo:20} -> {key}")

print(f"\nKAN-128 atualizado com mapa completo.")
print()
print("=" * 70)
print("EXECUCAO COMPLETA")
print("=" * 70)
