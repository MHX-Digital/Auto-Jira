"""
Jira Executor - Passos 2, 3 e 4
"""
import json, urllib.request, urllib.error, urllib.parse
from jira_config import BASE, PROJECT, HEADERS

def api_post(path, data):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def adf_rich(blocks):
    """Build ADF from list of block dicts: {type: paragraph|heading|bulletList|rule, ...}"""
    content = []
    for b in blocks:
        btype = b.get("type", "paragraph")

        if btype == "heading":
            content.append({
                "type": "heading",
                "attrs": {"level": b.get("level", 3)},
                "content": [{"type": "text", "text": b["text"]}]
            })

        elif btype == "paragraph":
            text_content = []
            if b.get("bold"):
                text_content.append({"type": "text", "text": b["text"], "marks": [{"type": "strong"}]})
            elif b.get("code"):
                text_content.append({"type": "text", "text": b["text"], "marks": [{"type": "code"}]})
            else:
                text_content.append({"type": "text", "text": b["text"]})
            content.append({"type": "paragraph", "content": text_content})

        elif btype == "bulletList":
            items = []
            for item_text in b["items"]:
                items.append({
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": item_text}]}]
                })
            content.append({"type": "bulletList", "content": items})

        elif btype == "codeBlock":
            content.append({
                "type": "codeBlock",
                "attrs": {"language": b.get("language", "")},
                "content": [{"type": "text", "text": b["text"]}]
            })

        elif btype == "rule":
            content.append({"type": "rule"})

        elif btype == "taskList":
            items = []
            for item_text in b["items"]:
                items.append({
                    "type": "taskItem",
                    "attrs": {"localId": "", "state": "TODO"},
                    "content": [{"type": "text", "text": item_text}]
                })
            content.append({"type": "taskList", "attrs": {"localId": ""}, "content": items})

    return {"type": "doc", "version": 1, "content": content}

def create_issue(summary, issuetype, component, labels, description_adf, parent_key=None):
    fields = {
        "project": {"key": PROJECT},
        "summary": summary,
        "issuetype": {"name": issuetype},
        "components": [{"name": component}],
        "labels": labels,
        "description": description_adf,
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    code, resp = api_post("/rest/api/3/issue", {"fields": fields})
    if code == 201:
        key = resp.get("key", "???")
        print(f"  CRIADO: {key} | {summary}")
        return key
    else:
        print(f"  ERRO {code}: {resp}")
        return None


# ============================================================
# PASSO 2: GIT<->JIRA PLAYBOOK
# ============================================================
print("=" * 70)
print("PASSO 2 - GIT<->JIRA PLAYBOOK")
print("=" * 70)

playbook_desc = adf_rich([
    {"type": "heading", "level": 2, "text": "Playbook de Integracao Git <-> Jira (KAN)"},

    {"type": "heading", "level": 3, "text": "1. Padrao de Branch"},
    {"type": "paragraph", "text": "Formato obrigatorio:"},
    {"type": "codeBlock", "language": "", "text": "KAN-<id>/<slug-descritivo>\n\nExemplos:\n  KAN-100/supabase-auth-setup\n  KAN-114/modelo-contrato-otc\n  KAN-120/deal-room-fintech"},
    {"type": "bulletList", "items": [
        "Sempre comece com KAN-<id> para vincular automaticamente ao issue",
        "Use / como separador (nao hifen duplo)",
        "Slug curto e descritivo em kebab-case",
        "1 issue = 1 branch (nunca misture issues na mesma branch)",
    ]},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "2. Padrao de Commit"},
    {"type": "paragraph", "text": "Formato obrigatorio:"},
    {"type": "codeBlock", "language": "", "text": "KAN-<id> <tipo>: <mensagem curta>\n\nExemplos:\n  KAN-100 feat: configurar supabase auth e RLS\n  KAN-100 fix: corrigir migration de tabela users\n  KAN-114 docs: adicionar template de contrato OTC"},
    {"type": "bulletList", "items": [
        "Tipos: feat, fix, refactor, docs, test, chore, hotfix",
        "KAN-<id> DEVE ser a primeira coisa no commit",
        "Mensagem em portugues ou ingles (consistente por repo)",
        "Commits atomicos (1 mudanca logica por commit)",
    ]},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "3. Padrao de Pull Request"},
    {"type": "paragraph", "text": "Formato obrigatorio do titulo:"},
    {"type": "codeBlock", "language": "", "text": "KAN-<id> <descricao curta>\n\nExemplos:\n  KAN-100 Configurar Supabase (auth + db + storage)\n  KAN-114 Modelo de contrato de intermediacao OTC"},
    {"type": "bulletList", "items": [
        "Titulo DEVE comecar com KAN-<id>",
        "Corpo do PR deve conter: o que mudou, por que, como testar",
        "Referenciar criterios de aceite do card",
        "PRs pequenos (< 400 linhas). Se maior, quebrar em partes",
    ]},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "4. Regras Lean"},
    {"type": "bulletList", "items": [
        "WIP maximo: 2 issues em 'Doing' por desenvolvedor",
        "Terminar antes de comecar (nao abrir nova branch se ja tem 2 em andamento)",
        "PR aberto = issue em 'Review' (mover o card)",
        "PR merged = issue em 'Done' (ou 'Deploy' se tiver pipeline)",
        "Nao pular etapas do workflow (Backlog -> Ready -> Doing -> Review -> Done)",
    ]},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "5. Validacao da Integracao"},
    {"type": "paragraph", "text": "Como confirmar que o Git esta linkado ao Jira:"},
    {"type": "bulletList", "items": [
        "Abra qualquer issue no Jira (ex: KAN-100)",
        "No painel lateral direito, procure a secao 'Development'",
        "Deve aparecer: branches, commits e PRs vinculados automaticamente",
        "Se nao aparecer: verificar se o commit/branch tem 'KAN-xxx' no nome",
        "Testar com 1 commit de teste: git commit --allow-empty -m 'KAN-100 test: validar integracao git-jira'",
    ]},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "6. Checklist de PR (copiar para cada PR)"},
    {"type": "taskList", "items": [
        "Titulo do PR comeca com KAN-xxx",
        "Descricao inclui criterios de aceite do card",
        "Referencia ao card do Jira no corpo",
        "Plano de rollback descrito (se afeta deploy)",
        "Testes executados localmente",
        "Sem secrets/credenciais no codigo",
        "Menos de 400 linhas de diff",
    ]},
])

k_playbook = create_issue(
    "[GIT] Playbook de Integracao Git<->Jira (KAN)",
    "Tarefa", "PRODUCT", ["p1"],
    playbook_desc
)


# ============================================================
# PASSO 3: REPO EPIC MAPPING
# ============================================================
print()
print("=" * 70)
print("PASSO 3 - REPO EPIC MAPPING")
print("=" * 70)

# Known epic keys from audit
repo_map_desc = adf_rich([
    {"type": "heading", "level": 2, "text": "Mapa Repositorio -> Epic (KAN)"},
    {"type": "paragraph", "text": "Este documento mapeia cada repositorio Git para o Epic correspondente no Jira. Use para saber onde vincular commits e PRs."},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "Repos com Epic definido"},

    {"type": "paragraph", "text": "LexNotify (todos os repos do produto LexNotify AI)", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-13 — LexNotify AI (V1 -> Beta -> Prod)",
        "Component: PRODUCT",
        "Sprint-0 tasks: KAN-100..KAN-107",
    ]},

    {"type": "paragraph", "text": "Hamza Carbon (repos do Hamza Carbon)", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-14 — Hamza Carbon (testnet -> mainnet/prod)",
        "Component: PRODUCT",
        "Sprint-0 tasks: KAN-108..KAN-113",
    ]},

    {"type": "paragraph", "text": "NexusP2P", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-15 — NexusP2P (conclusao V1)",
        "Component: PRODUCT",
    ]},

    {"type": "paragraph", "text": "SideWallet", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-10 — Dev - SideWallet",
        "Component: DELIVERY",
    ]},

    {"type": "paragraph", "text": "VotoMap", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: KAN-20 — Venda VotoMap",
        "Component: LIQUIDATION",
        "Nota: se for desenvolvimento ativo (nao venda), considerar epic separado",
    ]},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "Repos PENDENTES (sem Epic especifico)"},

    {"type": "paragraph", "text": "MHX-Digital (org/repo principal)", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: PENDENTE — sugestao: criar epic 'Infra & DevOps MHX' no component PRODUCT ou DELIVERY",
        "Enquanto nao tiver epic, usar prefixo KAN-12 (Dev - Avulsos) como catch-all",
    ]},

    {"type": "paragraph", "text": "lfg-adv", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: PENDENTE — mapear se e produto, delivery ou consultoria",
        "Sugestao: vincular a KAN-12 (Dev - Avulsos) temporariamente",
    ]},

    {"type": "paragraph", "text": "x-golden", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: PENDENTE — verificar se e relacionado a QUANT (trading)",
        "Se for trading: vincular a KAN-21 (Pool de Liquidez) ou criar epic especifico",
        "Se for produto: vincular a KAN-12 (Dev - Avulsos)",
    ]},

    {"type": "paragraph", "text": "Kahincorp-AI", "bold": True},
    {"type": "bulletList", "items": [
        "Epic: PENDENTE — verificar se e produto AI interno",
        "Sugestao: vincular a KAN-16 (InceptionPsi) se relacionado, ou KAN-12 (Avulsos)",
    ]},

    {"type": "rule"},

    {"type": "heading", "level": 3, "text": "Regra geral para repos sem epic"},
    {"type": "bulletList", "items": [
        "Use KAN-12 (Dev - Avulsos / intake) como catch-all temporario",
        "Assim que o repo ganhar relevancia, crie um epic dedicado e migre as tasks",
        "Nunca commite sem referencia a algum KAN-xxx",
    ]},
])

k_repomap = create_issue(
    "[JIRA] Mapa Repo->Epic (Opcao A)",
    "Tarefa", "PRODUCT", ["p2"],
    repo_map_desc
)


# ============================================================
# PASSO 4: QUICK FILTERS (JQL pronto, impresso no console)
# ============================================================
print()
print("=" * 70)
print("PASSO 4 - QUICK FILTERS (JQL pronto para usar)")
print("=" * 70)

FILTERS = [
    ("Sprint-0 (tudo P1)",
     'project = KAN AND labels = p1 ORDER BY component ASC, key ASC'),

    ("Sprint-0: LexNotify",
     'project = KAN AND labels = p1 AND parent = KAN-13 ORDER BY key ASC'),

    ("Sprint-0: Hamza Carbon",
     'project = KAN AND labels = p1 AND parent = KAN-14 ORDER BY key ASC'),

    ("Sprint-0: OTC Compliance",
     'project = KAN AND labels = p1 AND parent = KAN-6 ORDER BY key ASC'),

    ("Sprint-0: Venda Fintech",
     'project = KAN AND labels = p1 AND parent = KAN-18 ORDER BY key ASC'),

    ("Board OPERATIONS (GOV+OTC+DELIVERY)",
     'project = KAN AND component in (GOV, OTC, DELIVERY) ORDER BY priority DESC, key ASC'),

    ("Board PRODUCT (PRODUCT+LIQUIDATION+QUANT)",
     'project = KAN AND component in (PRODUCT, LIQUIDATION, QUANT) ORDER BY priority DESC, key ASC'),

    ("Todos os Epics",
     'project = KAN AND issuetype = Epic ORDER BY component ASC, key ASC'),

    ("Kit Controle (SOP/DoR/DoD)",
     'project = KAN AND summary ~ "SOP + DoR" ORDER BY component ASC'),

    ("Kit Controle (Riscos)",
     'project = KAN AND summary ~ "Riscos & Dependencias" ORDER BY component ASC'),

    ("Bloqueados",
     'project = KAN AND labels = blocked ORDER BY priority DESC'),

    ("Esperando parceiro",
     'project = KAN AND labels = waiting_partner ORDER BY priority DESC'),

    ("Esperando cliente",
     'project = KAN AND labels = waiting_client ORDER BY priority DESC'),

    ("Legal/Compliance",
     'project = KAN AND labels = legal ORDER BY priority DESC, key ASC'),

    ("Infra/Deploy",
     'project = KAN AND labels = infra ORDER BY priority DESC, key ASC'),

    ("Hotfixes",
     'project = KAN AND labels = hotfix ORDER BY priority DESC'),

    ("Sem componente (orfaos)",
     'project = KAN AND component is EMPTY ORDER BY key ASC'),

    ("QUANT em producao",
     'project = KAN AND component = QUANT AND summary ~ "producao" ORDER BY key ASC'),

    ("LIQUIDATION (ativos a venda)",
     'project = KAN AND component = LIQUIDATION ORDER BY key ASC'),

    ("WIP atual (Em andamento)",
     'project = KAN AND status = "Em andamento" ORDER BY priority DESC'),

    ("Meu trabalho (assignee = currentUser)",
     'project = KAN AND assignee = currentUser() AND status != "Concluido" ORDER BY priority DESC'),

    ("Criados esta semana",
     'project = KAN AND created >= startOfWeek() ORDER BY created DESC'),

    ("Atualizados hoje",
     'project = KAN AND updated >= startOfDay() ORDER BY updated DESC'),
]

for name, jql in FILTERS:
    print(f"\n  --- {name} ---")
    print(f"  {jql}")

print()
print("=" * 70)
print("EXECUCAO COMPLETA")
print("=" * 70)
print()
print(f"  Playbook Git: {k_playbook}")
print(f"  Repo Map:     {k_repomap}")
