"""
Fix: Criar epic separado para Kahincorp-AI e atualizar KAN-128
"""
import json, urllib.request, urllib.error, time
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
        return e.code, e.read().decode()

def adf(text):
    content = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            content.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": line[2:]}]}
                ]}
            ]})
        else:
            content.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
    return {"type": "doc", "version": 1, "content": content}

def create_issue(summary, issuetype, component, labels, desc_text, parent_key=None):
    fields = {
        "project": {"key": PROJECT}, "summary": summary, "issuetype": {"name": issuetype},
        "components": [{"name": component}], "labels": labels, "description": adf(desc_text),
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    code, resp = api("POST", "/rest/api/3/issue", {"fields": fields})
    if code == 201:
        return resp.get("key")
    print(f"  ERRO {code}: {resp}")
    return None

# 1) Criar epic Kahincorp-AI
print("=== CORRECAO: Criar epic Kahincorp-AI ===")
k_epic = create_issue(
    "Kahincorp-AI — P&D / IA",
    "Epic", "QUANT", ["repo_kahincorp_ai", "p3"],
    "Objetivo: Pesquisa e desenvolvimento de solucoes de IA (Kahincorp).\nEscopo: Modelos de ML/IA, experimentacao, prototipagem, validacao.\nDone: Modelos validados com metricas, relatorio de viabilidade, decisao go/no-go."
)
print(f"  Epic criado: {k_epic}")
time.sleep(0.3)

# 2) Criar 2 tasks filhas
print("\n=== Kit minimo ===")
k_sop = create_issue(
    "[Kahincorp-AI] SOP + DoR/DoD", "Tarefa", "QUANT", ["repo_kahincorp_ai", "p3"],
    "DoR:\n- Hipotese definida com metricas-alvo\n- Dados disponiveis\n- Ambiente de experimentacao pronto\n\nDoD:\n- Experimento concluido com resultados documentados\n- Decisao go/no-go registrada\n- Codigo versionado e documentado\n\nChecklist:\n- [ ] Hipotese documentada\n- [ ] Experimento executado\n- [ ] Resultados analisados\n- [ ] Relatorio de viabilidade",
    k_epic
)
print(f"  SOP: {k_sop}")
time.sleep(0.3)

k_backlog = create_issue(
    "[Kahincorp-AI] Backlog inicial (ate 10 itens)", "Tarefa", "QUANT", ["repo_kahincorp_ai", "p3"],
    "Backlog inicial Kahincorp-AI:\n- Mapear estado atual do repositorio\n- Documentar modelos existentes\n- Identificar datasets necessarios\n- Definir metricas de avaliacao\n- Configurar ambiente de treinamento\n- Implementar pipeline de dados\n- Experimentar modelo baseline\n- Avaliar frameworks (PyTorch/TF/JAX)\n- Definir criterios de deploy\n- Documentar arquitetura",
    k_epic
)
print(f"  Backlog: {k_backlog}")

# 3) Atualizar KAN-128 com Kahincorp corrigido
print("\n=== Atualizando KAN-128 ===")

def adf_rich(blocks):
    content = []
    for b in blocks:
        btype = b.get("type", "paragraph")
        if btype == "heading":
            content.append({"type": "heading", "attrs": {"level": b.get("level", 3)},
                "content": [{"type": "text", "text": b["text"]}]})
        elif btype == "paragraph":
            tc = [{"type": "text", "text": b["text"]}]
            if b.get("bold"):
                tc = [{"type": "text", "text": b["text"], "marks": [{"type": "strong"}]}]
            content.append({"type": "paragraph", "content": tc})
        elif btype == "bulletList":
            items = [{"type": "listItem", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": t}]}
            ]} for t in b["items"]]
            content.append({"type": "bulletList", "content": items})
        elif btype == "rule":
            content.append({"type": "rule"})
    return {"type": "doc", "version": 1, "content": content}

updated_desc = adf_rich([
    {"type": "heading", "level": 2, "text": "Mapa Repositorio -> Epic (KAN) — FINAL"},
    {"type": "paragraph", "text": "Documento oficial de mapeamento. Atualizado com todos os repos resolvidos."},
    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "PRODUCT"},
    {"type": "paragraph", "text": "LexNotify -> KAN-13 (PRODUCT) | Sprint-0: KAN-100..KAN-107", "bold": True},
    {"type": "paragraph", "text": "Hamza Carbon -> KAN-14 (PRODUCT) | Sprint-0: KAN-108..KAN-113", "bold": True},
    {"type": "paragraph", "text": "NexusP2P -> KAN-15 (PRODUCT)", "bold": True},
    {"type": "paragraph", "text": "InceptionPsi -> KAN-16 (PRODUCT)", "bold": True},
    {"type": "paragraph", "text": "Shadpay -> KAN-17 (PRODUCT)", "bold": True},
    {"type": "paragraph", "text": f"MHX-Digital -> KAN-129 (PRODUCT) | Labels: repo_mhx_digital, infra", "bold": True},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "DELIVERY"},
    {"type": "paragraph", "text": "SideWallet -> KAN-10 (DELIVERY)", "bold": True},
    {"type": "paragraph", "text": "BahiaGold -> KAN-11 (DELIVERY)", "bold": True},
    {"type": "paragraph", "text": "Dev Avulsos (catch-all) -> KAN-12 (DELIVERY)", "bold": True},
    {"type": "paragraph", "text": "lfg-adv -> KAN-130 (DELIVERY) | Labels: repo_lfg_adv", "bold": True},
    {"type": "paragraph", "text": "x-golden -> KAN-131 (DELIVERY) | Labels: repo_x_golden", "bold": True},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "LIQUIDATION"},
    {"type": "paragraph", "text": "Venda APP Fintech -> KAN-18 (LIQUIDATION) | Sprint-0: KAN-120..KAN-126", "bold": True},
    {"type": "paragraph", "text": "Venda Vrumm -> KAN-19 (LIQUIDATION)", "bold": True},
    {"type": "paragraph", "text": "Venda VotoMap -> KAN-20 (LIQUIDATION)", "bold": True},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "QUANT / P&D"},
    {"type": "paragraph", "text": f"Kahincorp-AI -> {k_epic} (QUANT) | Labels: repo_kahincorp_ai", "bold": True},
    {"type": "paragraph", "text": "Pool de Liquidez -> KAN-21 (QUANT)", "bold": True},
    {"type": "paragraph", "text": "Funding Rate Arb -> KAN-22 (QUANT)", "bold": True},
    {"type": "paragraph", "text": "HLP Vault -> KAN-23 (QUANT)", "bold": True},
    {"type": "paragraph", "text": "Arb Stable/Spread -> KAN-24 (QUANT)", "bold": True},
    {"type": "paragraph", "text": "Nadaraya-Watson -> KAN-25 (QUANT)", "bold": True},
    {"type": "paragraph", "text": "kNN -> KAN-26 (QUANT)", "bold": True},
    {"type": "paragraph", "text": "MEV Quant Fund -> KAN-27 (QUANT)", "bold": True},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "OTC"},
    {"type": "paragraph", "text": "OTC Compliance -> KAN-6 (OTC) | Sprint-0: KAN-114..KAN-119", "bold": True},
    {"type": "paragraph", "text": "Intermediacao 1 BTC -> KAN-7 (OTC)", "bold": True},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "GOV"},
    {"type": "paragraph", "text": "Regularizar PJ 24.409 -> KAN-4 (GOV)", "bold": True},
    {"type": "paragraph", "text": "Financeiro/Contabil PJ 57.435 -> KAN-5 (GOV)", "bold": True},

    {"type": "rule"},
    {"type": "heading", "level": 3, "text": "Regra para repos novos sem epic"},
    {"type": "bulletList", "items": [
        "Use KAN-12 (Dev - Avulsos) como catch-all temporario",
        "Crie epic dedicado quando o repo ganhar relevancia",
        "Nunca commite sem KAN-xxx no commit",
    ]},
])

code, _ = api("PUT", "/rest/api/3/issue/KAN-128", {"fields": {"description": updated_desc}})
print(f"  KAN-128: HTTP {code}")

# Final summary
print()
print("=" * 70)
print("RELATORIO FINAL CORRIGIDO")
print("=" * 70)
print()
print("Epics CRIADOS:")
print(f"  KAN-129 | PRODUCT   | MHX-Digital — Infra & Automacao Interna")
print(f"  KAN-130 | DELIVERY  | lfg-adv — Entregas / Juridico")
print(f"  KAN-131 | DELIVERY  | x-golden — Cliente/Entrega")
print(f"  {k_epic:6} | QUANT     | Kahincorp-AI — P&D / IA")
print()
print("Tasks CRIADAS:")
print(f"  KAN-132 | [MHX-Digital] SOP + DoR/DoD      | parent=KAN-129")
print(f"  KAN-133 | [MHX-Digital] Backlog inicial     | parent=KAN-129")
print(f"  KAN-134 | [lfg-adv] SOP + DoR/DoD           | parent=KAN-130")
print(f"  KAN-135 | [lfg-adv] Backlog inicial          | parent=KAN-130")
print(f"  KAN-136 | [x-golden] SOP + DoR/DoD          | parent=KAN-131")
print(f"  KAN-137 | [x-golden] Backlog inicial         | parent=KAN-131")
print(f"  {k_sop:6} | [Kahincorp-AI] SOP + DoR/DoD    | parent={k_epic}")
print(f"  {k_backlog:6} | [Kahincorp-AI] Backlog inicial | parent={k_epic}")
print()
print("Epics REUTILIZADOS: nenhum (falso positivo corrigido)")
print()
print("MAPA FINAL COMPLETO (todos os repos):")
full = {
    "LexNotify": "KAN-13", "Hamza Carbon": "KAN-14", "NexusP2P": "KAN-15",
    "InceptionPsi": "KAN-16", "Shadpay": "KAN-17", "MHX-Digital": "KAN-129",
    "SideWallet": "KAN-10", "BahiaGold": "KAN-11", "Dev Avulsos": "KAN-12",
    "lfg-adv": "KAN-130", "x-golden": "KAN-131",
    "APP Fintech": "KAN-18", "Vrumm": "KAN-19", "VotoMap": "KAN-20",
    "Kahincorp-AI": k_epic, "Pool Liquidez": "KAN-21", "Funding Rate": "KAN-22",
    "HLP Vault": "KAN-23", "Arb Stable": "KAN-24", "Nadaraya-Watson": "KAN-25",
    "kNN": "KAN-26", "MEV Quant Fund": "KAN-27",
    "OTC Compliance": "KAN-6", "Interm. 1BTC": "KAN-7",
    "PJ 24.409": "KAN-4", "PJ 57.435": "KAN-5",
}
for repo, key in sorted(full.items()):
    print(f"  {repo:20} -> {key}")

print()
print(f"KAN-128 atualizado com mapa FINAL (zero pendentes).")
