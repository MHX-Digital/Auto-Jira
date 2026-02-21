"""
Jira Audit v2 - Usa /rest/api/3/search/jql com nextPageToken
"""
import json, urllib.request, urllib.error, urllib.parse, sys
from jira_config import BASE, HEADERS

def search_jql(jql, fields="key,summary,status,issuetype,components,labels,parent", max_results=50):
    """Paginated search using /rest/api/3/search/jql with nextPageToken"""
    all_issues = []
    token = None
    while True:
        params = {"jql": jql, "maxResults": str(max_results), "fields": fields}
        if token:
            params["nextPageToken"] = token
        qs = urllib.parse.urlencode(params)
        url = f"{BASE}/rest/api/3/search/jql?{qs}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        issues = d.get("issues", [])
        all_issues.extend(issues)
        if d.get("isLast", True) or not issues:
            break
        token = d.get("nextPageToken")
        if not token:
            break
    return all_issues

def get_issue(key, fields="summary,issuetype,components,labels,parent,status"):
    url = f"{BASE}/rest/api/3/issue/{key}?fields={fields}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# ============================================================
# PASSO 1: AUDITORIA
# ============================================================
print("=" * 70)
print("PASSO 1 - AUDITORIA DE CONSISTENCIA")
print("=" * 70)

# 1a) Total de issues
print("\n--- 1a) Contagem total ---")
all_issues = search_jql("project = KAN ORDER BY key ASC")
print(f"Total issues no KAN: {len(all_issues)}")

# Count by type
types = {}
comps = {}
labels_count = {}
for i in all_issues:
    f = i["fields"]
    t = f["issuetype"]["name"]
    types[t] = types.get(t, 0) + 1
    for c in f.get("components", []):
        comps[c["name"]] = comps.get(c["name"], 0) + 1
    for l in f.get("labels", []):
        labels_count[l] = labels_count.get(l, 0) + 1

print("\nPor tipo:")
for t, c in sorted(types.items()):
    print(f"  {t}: {c}")

# 1b) Por componente
print("\nPor componente:")
for comp in ["GOV", "OTC", "DELIVERY", "PRODUCT", "LIQUIDATION", "QUANT"]:
    print(f"  {comp}: {comps.get(comp, 0)}")

no_comp = sum(1 for i in all_issues if not i["fields"].get("components"))
if no_comp:
    print(f"  (sem componente): {no_comp}")

# 1c) P1
print("\nPor label:")
for l in ["p1", "p2", "legal", "infra"]:
    print(f"  {l}: {labels_count.get(l, 0)}")

# 2) Listar todas P1
print("\n--- 1b) Issues P1 ---")
p1_issues = [i for i in all_issues if "p1" in i["fields"].get("labels", [])]
print(f"Total P1: {len(p1_issues)}\n")
for i in sorted(p1_issues, key=lambda x: x["key"]):
    f = i["fields"]
    comp = f["components"][0]["name"] if f.get("components") else "-"
    parent = f.get("parent", {}).get("key", "-") if f.get("parent") else "-"
    status = f["status"]["name"]
    lbls = ",".join(f.get("labels", []))
    print(f"  {i['key']:8} | {comp:12} | parent={parent:8} | {status:12} | {lbls:15} | {f['summary'][:55]}")

# 3) Verificar Sprint-0 tasks (KAN-100..KAN-126)
print("\n--- 1c) Verificacao Sprint-0 (KAN-100..KAN-126) ---")

EXPECTED_SPRINT0 = {
    # LexNotify (KAN-13, PRODUCT, p1)
    "KAN-100": ("KAN-13", "PRODUCT", ["p1"]),
    "KAN-101": ("KAN-13", "PRODUCT", ["p1"]),
    "KAN-102": ("KAN-13", "PRODUCT", ["p1"]),
    "KAN-103": ("KAN-13", "PRODUCT", ["p1"]),
    "KAN-104": ("KAN-13", "PRODUCT", ["p1"]),
    "KAN-105": ("KAN-13", "PRODUCT", ["p1"]),
    "KAN-106": ("KAN-13", "PRODUCT", ["p1"]),
    "KAN-107": ("KAN-13", "PRODUCT", ["p1"]),
    # Hamza (KAN-14, PRODUCT, p1)
    "KAN-108": ("KAN-14", "PRODUCT", ["p1"]),
    "KAN-109": ("KAN-14", "PRODUCT", ["p1"]),
    "KAN-110": ("KAN-14", "PRODUCT", ["p1"]),
    "KAN-111": ("KAN-14", "PRODUCT", ["p1"]),
    "KAN-112": ("KAN-14", "PRODUCT", ["p1"]),
    "KAN-113": ("KAN-14", "PRODUCT", ["p1"]),
    # OTC (KAN-6, OTC, p1+legal)
    "KAN-114": ("KAN-6", "OTC", ["p1", "legal"]),
    "KAN-115": ("KAN-6", "OTC", ["p1", "legal"]),
    "KAN-116": ("KAN-6", "OTC", ["p1", "legal"]),
    "KAN-117": ("KAN-6", "OTC", ["p1", "legal"]),
    "KAN-118": ("KAN-6", "OTC", ["p1", "legal"]),
    "KAN-119": ("KAN-6", "OTC", ["p1", "legal"]),
    # Fintech (KAN-18, LIQUIDATION, p1)
    "KAN-120": ("KAN-18", "LIQUIDATION", ["p1"]),
    "KAN-121": ("KAN-18", "LIQUIDATION", ["p1"]),
    "KAN-122": ("KAN-18", "LIQUIDATION", ["p1"]),
    "KAN-123": ("KAN-18", "LIQUIDATION", ["p1"]),
    "KAN-124": ("KAN-18", "LIQUIDATION", ["p1"]),
    "KAN-125": ("KAN-18", "LIQUIDATION", ["p1"]),
    "KAN-126": ("KAN-18", "LIQUIDATION", ["p1"]),
}

issues_map = {i["key"]: i for i in all_issues}
ok_count = 0
fail_count = 0

for key, (exp_parent, exp_comp, exp_labels) in sorted(EXPECTED_SPRINT0.items()):
    issue = issues_map.get(key)
    if not issue:
        print(f"  {key}: NAO ENCONTRADA!")
        fail_count += 1
        continue

    f = issue["fields"]
    actual_parent = f.get("parent", {}).get("key", "-") if f.get("parent") else "-"
    actual_comp = f["components"][0]["name"] if f.get("components") else "-"
    actual_labels = set(f.get("labels", []))

    errors = []
    if actual_parent != exp_parent:
        errors.append(f"parent={actual_parent} (esperado {exp_parent})")
    if actual_comp != exp_comp:
        errors.append(f"comp={actual_comp} (esperado {exp_comp})")
    for el in exp_labels:
        if el not in actual_labels:
            errors.append(f"falta label '{el}'")

    if errors:
        print(f"  {key}: ERRO - {'; '.join(errors)}")
        fail_count += 1
    else:
        ok_count += 1

print(f"\n  Resultado: {ok_count} OK, {fail_count} ERROS de {len(EXPECTED_SPRINT0)} verificadas")
print()
print("=" * 70)
print("FIM PASSO 1")
print("=" * 70)
