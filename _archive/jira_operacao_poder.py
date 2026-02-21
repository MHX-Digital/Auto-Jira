"""
Jira Executor — Operacao e Realismo + Alinhamento de Poder
Passos 0-4
"""
import json, urllib.request, urllib.error, urllib.parse, time
from jira_config import BASE, PROJECT, HEADERS
CREATED = {}

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
        try: return e.code, json.loads(raw)
        except: return e.code, raw

def search_jql(jql, fields="key,summary,status,issuetype,components,labels,parent"):
    all_issues, token = [], None
    while True:
        params = {"jql": jql, "maxResults": "50", "fields": fields}
        if token: params["nextPageToken"] = token
        qs = urllib.parse.urlencode(params)
        code, data = api("GET", f"/rest/api/3/search/jql?{qs}")
        if code != 200:
            print(f"  ERRO search {code}: {str(data)[:200]}")
            break
        issues = data.get("issues", [])
        all_issues.extend(issues)
        if data.get("isLast", True) or not issues: break
        token = data.get("nextPageToken")
        if not token: break
    return all_issues

# ADF helpers
def _p(text): return {"type": "paragraph", "content": [{"type": "text", "text": text}]}
def _b(text): return {"type": "paragraph", "content": [{"type": "text", "text": text, "marks": [{"type": "strong"}]}]}
def _h(text, lv=3): return {"type": "heading", "attrs": {"level": lv}, "content": [{"type": "text", "text": text}]}
def _ul(items): return {"type": "bulletList", "content": [{"type": "listItem", "content": [_p(t)]} for t in items]}
def _cl(items): return {"type": "taskList", "attrs": {"localId": ""}, "content": [
    {"type": "taskItem", "attrs": {"localId": "", "state": "TODO"}, "content": [{"type": "text", "text": t}]} for t in items]}
def _hr(): return {"type": "rule"}
def _doc(blocks): return {"type": "doc", "version": 1, "content": blocks}
def _tbl(headers, rows):
    hr = {"type": "tableRow", "content": [
        {"type": "tableHeader", "attrs": {}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": h, "marks": [{"type": "strong"}]}]}]} for h in headers]}
    dr = [{"type": "tableRow", "content": [
        {"type": "tableCell", "attrs": {}, "content": [_p(str(c))]} for c in row]} for row in rows]
    return {"type": "table", "attrs": {"isNumberColumnEnabled": False, "layout": "wide"}, "content": [hr] + dr}

SUBTASK_TYPE = "Subtarefa"

def create_issue(summary, issuetype, component, labels, desc_blocks, parent_key=None, duedate=None):
    fields = {"project": {"key": PROJECT}, "summary": summary, "issuetype": {"name": issuetype},
              "components": [{"name": component}], "labels": labels, "description": _doc(desc_blocks)}
    if parent_key: fields["parent"] = {"key": parent_key}
    if duedate: fields["duedate"] = duedate
    code, resp = api("POST", "/rest/api/3/issue", {"fields": fields})
    if code == 201:
        key = resp.get("key", "???")
        print(f"  CRIADO: {key} | {summary[:65]}")
        CREATED[key] = summary
        return key
    else:
        print(f"  ERRO {code}: {str(resp)[:200]}")
        if code == 400 and issuetype == SUBTASK_TYPE:
            print(f"  Retentando com 'Subtask'...")
            fields["issuetype"] = {"name": "Subtask"}
            code2, resp2 = api("POST", "/rest/api/3/issue", {"fields": fields})
            if code2 == 201:
                key = resp2.get("key", "???")
                print(f"  CRIADO: {key} | {summary[:65]}")
                CREATED[key] = summary
                return key
            print(f"  ERRO Subtask {code2}: {str(resp2)[:200]}")
        return None

def update_issue(key, fields):
    code, resp = api("PUT", f"/rest/api/3/issue/{key}", {"fields": fields})
    if code in (200, 204): print(f"  ATUALIZADO: {key}")
    else: print(f"  ERRO update {key}: {code} — {str(resp)[:150]}")
    return code in (200, 204)

# ============================================================
# PASSO 0: AUDITORIA
# ============================================================
print("=" * 70)
print("PASSO 0 — AUDITORIA")
print("=" * 70)

print("\n--- 0a) Boards ---")
code, bd = api("GET", "/rest/agile/1.0/board?projectKeyOrId=KAN")
for b in bd.get("values", []):
    print(f"  Board {b['id']}: {b['name']} (type={b.get('type','?')})")

print("\n--- 0b) Issue types ---")
code, td = api("GET", f"/rest/api/3/issue/createmeta/{PROJECT}/issuetypes")
for it in td.get("issueTypes", td.get("values", [])):
    n, s, h = it.get("name","?"), it.get("subtask",False), it.get("hierarchyLevel","?")
    print(f"  {n} (subtask={s}, hier={h})")
    if s: SUBTASK_TYPE = n
print(f"  -> Subtask type: {SUBTASK_TYPE}")

print("\n--- 0c) P1 por Epic ---")
p1 = search_jql("project = KAN AND labels = p1 ORDER BY key ASC")
print(f"Total P1: {len(p1)}")
by_epic = {}
for i in p1:
    f = i["fields"]
    pk = f.get("parent",{}).get("key","SEM_EPIC") if f.get("parent") else "SEM_EPIC"
    ps = f.get("parent",{}).get("fields",{}).get("summary","???") if f.get("parent") else "Sem Epic"
    c = f["components"][0]["name"] if f.get("components") else "-"
    by_epic.setdefault(pk, {"s": ps, "c": c, "i": []})
    by_epic[pk]["i"].append({"k": i["key"], "s": f["summary"], "st": f["status"]["name"]})
for ek in sorted(by_epic):
    info = by_epic[ek]
    print(f"\n  EPIC {ek} — {info['s']} [{info['c']}]")
    for t in info["i"]:
        print(f"    {t['k']:8} | {t['st']:12} | {t['s'][:55]}")

print("\n--- 0d) Anchor issues ---")
for name in ["Stack Tecnol", "Roadmap Atual", "Tese de Poder"]:
    found = search_jql(f'project = KAN AND summary ~ "{name}"')
    if found:
        for x in found: print(f"  EXISTE: {x['key']} — {x['fields']['summary']}")
    else:
        print(f"  NAO EXISTE: '{name}' -> sera criado")

time.sleep(0.5)

# ============================================================
# PASSO 1: OPERACAO E REALISMO
# ============================================================
print("\n" + "=" * 70)
print("PASSO 1 — OPERACAO E REALISMO")
print("=" * 70)

epic1 = create_issue("OPERACAO — Realismo: Stack + Roadmap (MVP)", "Epic", "PRODUCT", ["p1", "infra"], [
    _h("OPERACAO — Realismo: Stack + Roadmap (MVP)", 2),
    _p("Epic ancora para padronizar stack tecnologica e roadmap de execucao."),
    _hr(), _b("Objetivo:"), _p("Definir padrao tecnico (stack) e mapa de execucao (roadmap) para todos os projetos MHX."),
    _b("Stack padrao alvo:"), _ul(["Supabase/Postgres + Supabase Auth + Meta Cloud API + GitHub Actions CI/CD + Sentry + dev/staging/prod + vault/backups"]),
    _b("Contexto:"), _ul([
        "Meta de caixa: R$150.000 em 3-4 entradas", "Receitas prioritarias: OTC e Licitacao",
        "Custos infra: R$0 (placeholder)", "Kill-switch: 30% (por estrategia/mes)",
        "Parcelas empresas: dia 20", "Deps externas: Foxbit/contador/banco/parceiro",
        "Carnaval 2026: evitar prazos 16/02-18/02"]),
    _b("Done:"), _ul(["Stack documentada e validada", "Roadmap publicado no Jira", "Regras WIP e rotina diaria aplicadas"]),
])
time.sleep(0.3)

# Task 1: Stack
print("\n--- Task 1: Stack Tecnologica ---")
t_stack = create_issue("Stack Tecnologica Atual (MVP) — padrao de produto", "Tarefa", "PRODUCT", ["p1", "infra"], [
    _h("Stack Tecnologica Atual (MVP)", 2),
    _p("Definir e padronizar a stack tecnologica para todos os produtos MHX."),
    _hr(), _b("Stack padrao alvo:"), _ul([
        "Supabase/Postgres (banco + RLS + storage)", "Supabase Auth (autenticacao + autorizacao)",
        "Meta Cloud API (WhatsApp: stub + webhooks + retries)", "GitHub Actions CI/CD (build/test/deploy: dev/staging/prod)",
        "Sentry (error tracking + logs estruturados)", "Ambientes: dev / staging / prod",
        "Seguranca: vault + backups + rotacao secrets"]),
    _b("Custos infra atuais: R$0 (placeholder)"),
    _hr(), _b("DoD:"), _cl([
        "Padrao de repositorio definido (monorepo vs multi)", "Supabase baseline configurado",
        "Meta Cloud API integrada (stub + webhooks)", "CI/CD operacional (3 envs)",
        "Sentry configurado", "Vault + backups implementados",
        "Runbook deploy/rollback publicado", "Registro de custos atualizado"]),
], epic1, "2026-02-20")
time.sleep(0.3)

# Stack subtasks
print("  Criando subtasks Stack...")
stack_subs_data = [
    ("Definir padrao de repositorio (monorepo vs multi) e convencao KAN-xxx",
     ["Monorepo ou multi-repo por produto?", "Convencao branch: KAN-xxx/<slug>", "Convencao commit: KAN-xxx <tipo>: <msg>", "Template .gitignore, .editorconfig, README"]),
    ("Padronizar Supabase (auth/db/storage) e RLS baseline",
     ["Auth com email/password + OAuth", "Postgres com RLS habilitado", "Storage para uploads", "Migrations versionadas"]),
    ("Padronizar Meta Cloud API (stub + webhooks + retries)",
     ["Stub envio/recebimento funcionando", "Webhook endpoint configurado", "Retry: 3x exponential backoff", "Template de mensagem registrado"]),
    ("CI/CD GitHub Actions: build/test/deploy por env (dev/staging/prod)",
     ["Workflow: build -> test -> deploy", "3 envs: dev (push main), staging (tag), prod (release)", "Secrets via GitHub Secrets", "Notificacao de falha"]),
    ("Observabilidade: Sentry + logs padrao",
     ["Sentry por projeto", "Source maps frontend", "Structured logging (JSON) backend", "Alertas configurados"]),
    ("Seguranca: vault + backups + rotacao secrets",
     ["Vault para secrets", "Backup Postgres diario", "Rotacao tokens 90 dias", "Auditoria de acessos"]),
    ("Template de Runbook Deploy/Rollback",
     ["Pre-deploy checklist", "Deploy passo-a-passo", "Rollback < 5 min", "Pos-deploy verificacao"]),
    ("Registro de custos infra (placeholder R$0)",
     ["Campos: servico|tier|custo mensal|previsao upgrade", "Servicos: Supabase, Sentry, GitHub, Vercel, dominios", "Trigger: revisar ao sair do free tier"]),
]
stack_subs = []
for summ, items in stack_subs_data:
    k = create_issue(summ, SUBTASK_TYPE, "PRODUCT", ["p1", "infra"],
        [_p(summ), _hr(), _b("Checklist:"), _ul(items), _b("DoD:"), _cl(items)], t_stack)
    stack_subs.append(k)
    time.sleep(0.2)

# Task 2: Roadmap
print("\n--- Task 2: Roadmap ---")
roadmap_table = _tbl(
    ["Projeto", "Epic", "Fase", "Prior.", "ROI", "Risco", "Deps", "Proximo Marco"],
    [["OTC Compliance", "KAN-6", "F5", "P1", "Alto", "Legal", "Foxbit/banco", "Contrato validado"],
     ["Licitacoes", "(novo)", "F1", "P1", "Alto", "Legal", "Parceiro", "Primeiro edital"],
     ["Dispensa", "(novo)", "F1", "P1", "Medio", "Baixo", "Governo", "Primeira venda"],
     ["Dev Tech", "KAN-12", "F3", "P2", "Medio", "Baixo", "-", "Stack padronizada"],
     ["Hamza Carbon", "KAN-14", "F2", "P1", "Alto", "Tecnico", "Mainnet", "Deploy mainnet"],
     ["NexusP2P", "KAN-15", "F3", "P2", "Medio", "Tecnico", "-", "V1 concluida"],
     ["LexNotify", "KAN-13", "F1", "P1", "Alto", "Tecnico", "Supabase/WA", "MVP beta"],
     ["InceptionPsi", "KAN-16", "F0", "P3", "Baixo", "Alto", "-", "Go/no-go"],
     ["MHX/Ativos", "KAN-129", "F1", "P2", "Medio", "Baixo", "-", "Infra padronizada"],
     ["Quants", "KAN-21..27", "F1", "P2", "Alto", "Alto", "Capital", "Backtest (12-24m)"]])

t_roadmap = create_issue("Roadmap Atual (MVP) — matriz Projeto/Fase/ROI/Risco", "Tarefa", "PRODUCT", ["p1"], [
    _h("Roadmap Atual (MVP)", 2),
    _p("Mapa de execucao de todos os projetos MHX. Atualizar semanalmente."),
    _hr(), _b("Fases:"), _ul(["F0=Ideia", "F1=Setup/Fundacao", "F2=Dev ativo", "F3=Beta/Testes", "F4=Producao", "F5=Operacao madura"]),
    _hr(), _b("Matriz:"), roadmap_table,
    _hr(), _b("Regras:"), _ul([
        "Corte: sem retorno monetario em 3 meses -> congelar/pivotar",
        "WIP max: 2 cards Doing por board por pessoa",
        "Rotina diaria (5 min): revisar blocked/waiting + puxar 2 cards",
        "Parcelas: dia 20 (lembrete)", "Deps externas: Foxbit, contador, banco, parceiro"]),
    _b("Meta: R$150.000 em 3-4 entradas. Prioridade: OTC + Licitacao."),
], epic1, "2026-02-21")
time.sleep(0.3)

# Roadmap subtasks
print("  Criando subtasks Roadmap...")
road_subs_data = [
    ("Criar tabela roadmap (Projeto|Epic|Fase|ROI|Risco|Deps|Marco|Dono)",
     ["Todas as colunas preenchidas", "Publicada no Jira", "Update semanal (sexta)"]),
    ("Inserir estagios atuais (OTC F5, Licitacoes F1, Hamza F2, etc.)",
     ["10 projetos registrados com fase correta", "Validado pelo dono"]),
    ("Definir regra de corte: sem retorno monetario em 3m -> congelar",
     ["Regra documentada", "Excecao P&D documentada", "Revisao trimestral"]),
    ("Definir WIP: max 2 cards Doing por board por pessoa",
     ["Regra comunicada", "Lembrete no board"]),
    ("Definir rotina diaria (5 min): revisar blocked/waiting + puxar 2 cards",
     ["Rotina documentada", "Executada 5 dias consecutivos"]),
]
road_subs = []
for summ, items in road_subs_data:
    k = create_issue(summ, SUBTASK_TYPE, "PRODUCT", ["p1"],
        [_p(summ), _hr(), _b("DoD:"), _cl(items)], t_roadmap)
    road_subs.append(k)
    time.sleep(0.2)

# ============================================================
# PASSO 2: ALINHAMENTO DE PODER
# ============================================================
print("\n" + "=" * 70)
print("PASSO 2 — ALINHAMENTO DE PODER")
print("=" * 70)

epic2 = create_issue("GOV — Tese de Poder & Patrimonio (MVP)", "Epic", "GOV", ["p1", "legal"], [
    _h("GOV — Tese de Poder & Patrimonio (MVP)", 2),
    _p("Epic ancora: tese estrategica, politica de risco e regras de compliance."),
    _hr(), _b("Objetivo:"), _p("Maximizar caixa + patrimonio liquido. Meta: R$150.000 em 3-4 entradas."),
    _b("Horizonte:"), _ul(["12 meses: caixa via OTC + Licitacao", "3 anos: patrimonio + escala tech"]),
    _b("Premissas:"), _ul([
        "Limite societario: 49% maximo", "Foco juridico: compliance-first",
        "Modelo hibrido: tech house + cripto infra", "NexusP2P: possibilidade de venda",
        "Alavancagem: limites seguros (ver Politica de Risco)"]),
    _b("Done:"), _ul(["Tese 1 pagina publicada", "Politica de risco com kill-switch", "Regras compliance documentadas"]),
])
time.sleep(0.3)

# Task A: Tese
print("\n--- Task A: Tese de Poder ---")
t_tese = create_issue("Tese de Poder & Patrimonio — 1 pagina", "Tarefa", "GOV", ["p1", "legal"], [
    _h("Tese de Poder & Patrimonio — 1 pagina", 2),
    _p("Documento estrategico de 1 pagina com direcao do portfolio MHX."),
    _hr(), _b("Conteudo:"), _ul([
        "Visao: maximizar caixa + patrimonio liquido",
        "Meta: R$150.000 em 3-4 entradas. Receitas: OTC + Licitacao",
        "Horizonte: 12m (caixa) / 3y (patrimonio + escala)",
        "Limite societario: 49% maximo em qualquer venture",
        "Compliance-first em todas as operacoes",
        "Modelo hibrido: tech house + cripto infra",
        "NexusP2P: avaliar venda se oferta > custo oportunidade",
        "Alavancagem: regra segura (ver Task B)"]),
    _b("DoD:"), _cl(["Documento 1 pagina redigido", "Validado", "Publicado no Jira", "PDF exportado"]),
], epic2, "2026-02-20")
time.sleep(0.3)

# Task B: Risco
print("\n--- Task B: Politica de Risco ---")
t_risco = create_issue("Politica de Risco (quant + operacao) — kill-switch", "Tarefa", "GOV", ["p1", "security"], [
    _h("Politica de Risco — kill-switch", 2),
    _p("Limites de risco para estrategias quant e operacoes."),
    _hr(), _b("Regras:"), _ul([
        "Kill-switch: acima de 30% de perda POR ESTRATEGIA e POR MES",
        "Risco aceito: 30-40% limite maximo por estrategia/carteira",
        "Alocacao inicial: US$100 por estrategia",
        "Mercados: spot + futuros",
        "Registro: planilha (entrada, saida, P&L, motivo)",
        "Kill-switch automatico: via API exchange ou alerta manual"]),
    _b("Operacional:"), _ul([
        "Revisar P&L diariamente", "Perda >30% estrategia: PARAR",
        "Perda >30% mes total: PARAR 48h + revisar",
        "Alavancagem: max 2x futuros, 1x spot (regra segura)"]),
    _b("DoD:"), _cl(["Politica documentada", "Kill-switch definido (30%)", "Alocacao definida (US$100)",
        "Planilha criada", "Regra alavancagem definida", "Publicada"]),
], epic2, "2026-02-21")
time.sleep(0.3)

# Task C: Compliance
print("\n--- Task C: Compliance ---")
t_compl = create_issue("Regras de Compliance e Reputacao Bancaria", "Tarefa", "GOV", ["p1", "legal"], [
    _h("Regras de Compliance e Reputacao Bancaria", 2),
    _p("Regras nao-negociaveis de compliance para todas as operacoes MHX."),
    _hr(), _b("Regra #1 — NAO NEGOCIAVEL:"), _p("Nao lavar dinheiro. Zero tolerancia."),
    _hr(), _b("Regra #2 — OTC por faixa:"), _ul([
        "> R$50.000: contrato + KYT/KYC completo + evidencias",
        "R$10.000-R$50.000: contrato simplificado + KYC basico",
        "< R$10.000: regra simplificada (registro + ID basica)"]),
    _hr(), _b("Regra #3 — Evidencias:"), _ul([
        "Registrar: data, valor, contraparte, hash tx",
        "Conciliacao semanal", "Prints + comprovantes + hashes on-chain",
        "Armazenamento minimo 5 anos"]),
    _b("Regra #4 — Reputacao bancaria:"), _ul([
        "Conta PJ limpa", "Separar cripto vs fiat", "Nao misturar PF/PJ",
        "Manter relacionamento com gerente"]),
    _b("DoD:"), _cl(["Regras documentadas", "Checklist por faixa publicado",
        "Template registro criado", "Conciliacao semanal definida", "Comunicado"]),
], epic2, "2026-02-24")
time.sleep(0.3)

# ============================================================
# PASSO 3: LIMPEZA
# ============================================================
print("\n" + "=" * 70)
print("PASSO 3 — LIMPEZA")
print("=" * 70)

# 3a) Issues sem component
print("\n--- 3a) Sem component ---")
no_comp = search_jql("project = KAN AND component is EMPTY ORDER BY key ASC")
if no_comp:
    for i in no_comp:
        f = i["fields"]
        print(f"  {i['key']:8} | {f['issuetype']['name']:10} | {f['summary'][:50]}")
        update_issue(i["key"], {"components": [{"name": "GOV"}]})
        time.sleep(0.2)
else:
    print("  Nenhum. OK!")

# 3b) Orfaos sem parent
print("\n--- 3b) Orfaos (sem parent, nao-Epic) ---")
all_non_epic = search_jql("project = KAN AND issuetype != Epic ORDER BY key ASC",
    "key,summary,issuetype,parent,components,labels")
orphans = []
for i in all_non_epic:
    f = i["fields"]
    if not f.get("parent"):
        comp = f["components"][0]["name"] if f.get("components") else "-"
        it = f["issuetype"]["name"]
        # Skip subtasks that might have lost parent reference
        if it in ("Subtarefa", "Subtask"): continue
        orphans.append(i)
        print(f"  ORFAO: {i['key']:8} | {it:10} | {comp:10} | {f['summary'][:50]}")

# Try to assign orphans to appropriate epics
COMP_TO_EPIC = {"GOV": None, "OTC": "KAN-6", "DELIVERY": "KAN-12", "PRODUCT": None, "LIQUIDATION": "KAN-18", "QUANT": None}
for i in orphans:
    f = i["fields"]
    comp = f["components"][0]["name"] if f.get("components") else None
    # Only auto-assign if we have a clear mapping
    if comp and COMP_TO_EPIC.get(comp):
        print(f"  -> Vinculando {i['key']} ao Epic {COMP_TO_EPIC[comp]}")
        update_issue(i["key"], {"parent": {"key": COMP_TO_EPIC[comp]}})
        time.sleep(0.2)

if not orphans:
    print("  Nenhum orfao. OK!")
else:
    print(f"  Total orfaos: {len(orphans)}")

# 3c) Labels
print("\n--- 3c) Labels em uso ---")
all_issues = search_jql("project = KAN ORDER BY key ASC", "key,labels")
lbl_count = {}
for i in all_issues:
    for l in i["fields"].get("labels", []):
        lbl_count[l] = lbl_count.get(l, 0) + 1
for l, c in sorted(lbl_count.items()):
    print(f"  {l}: {c}")
standard = {"p1","p2","p3","infra","legal","security","blocked","waiting_partner","waiting_client"}
non_std = {l for l in lbl_count if l not in standard and not l.startswith("repo_")}
if non_std:
    print(f"  Labels nao-padrao: {sorted(non_std)}")

# ============================================================
# PASSO 4: RELATORIO FINAL
# ============================================================
print("\n" + "=" * 70)
print("PASSO 4 — RELATORIO FINAL")
print("=" * 70)

print("\n--- Epics ---")
print(f"  {epic1} | PRODUCT | OPERACAO — Realismo: Stack + Roadmap (MVP) | p1,infra")
print(f"  {epic2} | GOV     | GOV — Tese de Poder & Patrimonio (MVP)    | p1,legal")

print("\n--- Tasks ---")
print(f"  {t_stack}    | Stack Tecnologica Atual (MVP)         | parent={epic1} | due=2026-02-20")
print(f"  {t_roadmap}  | Roadmap Atual (MVP)                   | parent={epic1} | due=2026-02-21")
print(f"  {t_tese}     | Tese de Poder & Patrimonio             | parent={epic2} | due=2026-02-20")
print(f"  {t_risco}    | Politica de Risco — kill-switch        | parent={epic2} | due=2026-02-21")
print(f"  {t_compl}    | Compliance e Reputacao Bancaria        | parent={epic2} | due=2026-02-24")

print(f"\n--- Subtasks Stack ({len([k for k in stack_subs if k])}) ---")
for k in stack_subs:
    if k: print(f"  {k} | parent={t_stack}")

print(f"\n--- Subtasks Roadmap ({len([k for k in road_subs if k])}) ---")
for k in road_subs:
    if k: print(f"  {k} | parent={t_roadmap}")

print("\n--- Due Dates (pos-Carnaval) ---")
print("  Stack Tecnologica  -> 2026-02-20 (sexta)")
print("  Roadmap Atual      -> 2026-02-21 (sabado)")
print("  Tese de Poder      -> 2026-02-20 (sexta)")
print("  Politica de Risco  -> 2026-02-21 (sabado)")
print("  Compliance         -> 2026-02-24 (terca)")
print("  Carnaval 16-18/02: EVITADO")

print("\n--- JQLs ---")
jqls = [
    ("P1 Board PRODUCT",     'project = KAN AND labels = p1 AND component in (PRODUCT, LIQUIDATION, QUANT) ORDER BY key ASC'),
    ("P1 Board OPERATIONS",  'project = KAN AND labels = p1 AND component in (GOV, OTC, DELIVERY) ORDER BY key ASC'),
    ("P1 Todos",             'project = KAN AND labels = p1 ORDER BY component ASC, key ASC'),
    ("Due date esta semana", 'project = KAN AND duedate >= startOfWeek() AND duedate <= endOfWeek() ORDER BY duedate ASC'),
    ("Due date 7 dias",      'project = KAN AND duedate >= now() AND duedate <= 7d ORDER BY duedate ASC'),
    ("Orfaos (sem parent)",  'project = KAN AND issuetype not in (Epic) AND parent is EMPTY ORDER BY key ASC'),
    ("Sem component",        'project = KAN AND component is EMPTY ORDER BY key ASC'),
    ("Blocked/Waiting",      'project = KAN AND labels in (blocked, waiting_partner, waiting_client) ORDER BY key ASC'),
    ("Infra",                'project = KAN AND labels = infra ORDER BY key ASC'),
    ("Legal",                'project = KAN AND labels = legal ORDER BY key ASC'),
    ("Security",             'project = KAN AND labels = security ORDER BY key ASC'),
]
for name, jql in jqls:
    print(f"\n  {name}:")
    print(f"    {jql}")

print(f"\n--- Resumo ---")
print(f"  Epics criados: 2")
print(f"  Tasks criadas: 5")
print(f"  Subtasks criadas: {len([k for k in stack_subs+road_subs if k])}")
print(f"  Total novos issues: {len(CREATED)}")

print("\n" + "=" * 70)
print("EXECUCAO COMPLETA")
print("=" * 70)
