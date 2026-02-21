"""
Jira Executor - Padronizacao e criacao em massa
"""
import json, time, sys
import urllib.request, urllib.error
from jira_config import BASE, EMAIL, TOKEN, PROJECT, CRED, HEADERS

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
        return e.code, raw

def adf(text):
    """Converte texto simples para Atlassian Document Format"""
    paragraphs = text.strip().split("\n\n")
    content = []
    for p in paragraphs:
        lines = p.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("- "):
                content.append({
                    "type": "bulletList",
                    "content": [{
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": line[2:]}]
                        }]
                    }]
                })
            elif line.startswith("**") and line.endswith("**"):
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": line.strip("*"), "marks": [{"type": "strong"}]}]
                })
            else:
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": line}]
                })
    return {"type": "doc", "version": 1, "content": content}

def adf_simple(text):
    """ADF com paragrafo unico"""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
    }

def update_issue(key, fields=None, update=None):
    payload = {}
    if fields:
        payload["fields"] = fields
    if update:
        payload["update"] = update
    code, resp = api("PUT", f"/rest/api/3/issue/{key}", payload)
    return code

def create_issue(summary, issuetype, component, labels, description_text, parent_key=None):
    fields = {
        "project": {"key": PROJECT},
        "summary": summary,
        "issuetype": {"name": issuetype},
        "components": [{"name": component}],
        "labels": labels,
        "description": adf(description_text),
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    code, resp = api("POST", "/rest/api/3/issue", {"fields": fields})
    if code == 201:
        return resp.get("key", "???")
    else:
        print(f"  ERRO {code} criando '{summary}': {resp}")
        return None

# ============================================================
# PASSO 1: Padronizar descricoes dos epics
# ============================================================

EPIC_DESCRIPTIONS = {
    "KAN-4": "Objetivo: Manter a PJ 24.409 regularizada e em compliance.\nEscopo: Atualizacao cadastral, obrigacoes acessorias, certidoes, procuracoes.\nDone: Todas as pendencias resolvidas, certidoes negativas emitidas, nenhum debito aberto.",
    "KAN-5": "Objetivo: Gestao financeira e contabil completa da PJ 57.435.\nEscopo: Balancetes mensais, DAS/DARF, conciliacao bancaria, obrigacoes fiscais.\nDone: Contabilidade em dia ate o mes corrente, impostos pagos, balanco disponivel.",
    "KAN-6": "Objetivo: Garantir compliance total nas operacoes OTC (KYT/KYC).\nEscopo: Integracao Foxbit, contratos padrao, comunicacao bancaria, evidencias.\nDone: Fluxo KYT documentado, contratos prontos, checklist de compliance validado.",
    "KAN-7": "Objetivo: Executar intermediacao de 1 BTC com fluxo completo.\nEscopo: Contrato, KYT, execucao, liquidacao, comprovantes, conciliacao.\nDone: Operacao executada, conciliada, documentada e arquivada.",
    "KAN-8": "Objetivo: Vencer licitacao de intermediacao (dispensa 300k) e preparar proximas 2.\nEscopo: Documentacao, proposta tecnica/comercial, habilitacao, recursos.\nDone: Dispensa adjudicada, proximas 2 licitacoes mapeadas e em preparacao.",
    "KAN-9": "Objetivo: Pipeline de licitacoes de tecnologia com cadencia de 1-2 por mes.\nEscopo: Monitoramento portais, preparacao de propostas, submissao, acompanhamento.\nDone: Pipeline ativo, pelo menos 2 licitacoes submetidas por mes.",
    "KAN-10": "Objetivo: Desenvolver e entregar o projeto SideWallet.\nEscopo: Backend, frontend, integracao blockchain, testes, deploy.\nDone: MVP funcional deployado, testes passando, documentacao minima.",
    "KAN-11": "Objetivo: Desenvolver e entregar o projeto BahiaGold.\nEscopo: Backend, frontend, regras de negocio, testes, deploy.\nDone: MVP funcional deployado, testes passando, documentacao minima.",
    "KAN-12": "Objetivo: Gerenciar intake de demandas avulsas de desenvolvimento.\nEscopo: Triagem, estimativa, priorizacao, execucao, entrega.\nDone: Cada demanda entregue com aceite do solicitante.",
    "KAN-13": "Objetivo: Levar o LexNotify AI do V1 ao Beta e depois a Producao.\nEscopo: Auth, notificacoes, kanban, docs, automacoes, integracoes (Supabase, WhatsApp), deploy.\nDone: App em producao com usuarios reais, onboarding funcional, monitoramento ativo.",
    "KAN-14": "Objetivo: Migrar Hamza Carbon de testnet para mainnet/producao.\nEscopo: Smart contracts, UI compra/venda, wallet, integracao liquidez, seguranca, deploy.\nDone: Contratos em mainnet, fluxo real funcionando, monitoramento ativo.",
    "KAN-15": "Objetivo: Concluir a versao 1 do NexusP2P.\nEscopo: Matching engine, escrow, reputacao, UI, testes, deploy.\nDone: V1 funcional em producao, fluxo P2P completo operacional.",
    "KAN-16": "Objetivo: Levar InceptionPsi da descoberta ao V1.\nEscopo: Pesquisa, validacao de hipotese, prototipo, MVP, testes.\nDone: V1 funcional com metricas de validacao definidas.",
    "KAN-17": "Objetivo: Descoberta e analise regulatoria do Shadpay.\nEscopo: Pesquisa regulatoria, viabilidade tecnica, modelo de negocio, riscos.\nDone: Documento de viabilidade completo com decisao go/no-go.",
    "KAN-18": "Objetivo: Vender o ativo APP Fintech.\nEscopo: Deal room, demo, video, proposta comercial, handover, suporte pos-venda.\nDone: Ativo vendido ou em negociacao avancada com buyer qualificado.",
    "KAN-19": "Objetivo: Vender o ativo Vrumm.\nEscopo: Deal room, demo, video, proposta comercial, handover, suporte pos-venda.\nDone: Ativo vendido ou em negociacao avancada com buyer qualificado.",
    "KAN-20": "Objetivo: Vender o ativo VotoMap.\nEscopo: Deal room, demo, video, proposta comercial, handover, suporte pos-venda.\nDone: Ativo vendido ou em negociacao avancada com buyer qualificado.",
    "KAN-21": "Objetivo: Operar pool de liquidez em producao com rentabilidade.\nEscopo: Deploy de posicoes, monitoramento, rebalanceamento, metricas.\nDone: Pool ativo, P&L positivo, dashboard de monitoramento funcional.",
    "KAN-22": "Objetivo: Operar estrategia de Funding Rate Arbitrage em producao.\nEscopo: Bot de execucao, monitoramento, gestao de risco, metricas.\nDone: Bot ativo 24/7, P&L positivo, alertas configurados.",
    "KAN-23": "Objetivo: Operar HLP Vault em producao.\nEscopo: Deploy vault, gestao de risco, monitoramento, rebalanceamento.\nDone: Vault ativo, metricas de performance, alertas configurados.",
    "KAN-24": "Objetivo: Pesquisar e validar estrategia de Arbitragem Stable/Spread.\nEscopo: Backtesting, paper trading, analise de viabilidade, custos.\nDone: Relatorio de viabilidade com decisao go/no-go para producao.",
    "KAN-25": "Objetivo: Rebuild do modelo Nadaraya-Watson com gestao de risco.\nEscopo: Refatoracao, backtesting, validacao, integracao com risk engine.\nDone: Modelo rodando com risk limits, metricas de accuracy documentadas.",
    "KAN-26": "Objetivo: Pesquisar e desenvolver modelo kNN para trading.\nEscopo: Feature engineering, treinamento, backtesting, validacao.\nDone: Modelo validado com metricas, relatorio de viabilidade.",
    "KAN-27": "Objetivo: Levar MEV Quant Fund de P&D para producao.\nEscopo: Pesquisa MEV, implementacao, backtesting, paper trading, deploy.\nDone: Fund operacional em producao, metricas de P&L, gestao de risco ativa.",
}

def passo1_padronizar_epics():
    print("=" * 60)
    print("PASSO 1: Padronizando descricoes dos epics")
    print("=" * 60)
    results = []
    for key, desc in EPIC_DESCRIPTIONS.items():
        code = update_issue(key, fields={"description": adf(desc)})
        status = "OK" if code == 204 else f"ERRO({code})"
        results.append((key, status))
        print(f"  {key}: {status}")
        time.sleep(0.3)
    return results

# ============================================================
# PASSO 2: Kit de controle (3 tasks por epic)
# ============================================================

EPICS_DATA = [
    ("KAN-4", "GOV", "Regularizar PJ 24.409"),
    ("KAN-5", "GOV", "Financeiro/Contabil PJ 57.435"),
    ("KAN-6", "OTC", "OTC e KYT Compliance"),
    ("KAN-7", "OTC", "Intermediacao 1 BTC"),
    ("KAN-8", "DELIVERY", "Licitacao - Intermediacao"),
    ("KAN-9", "DELIVERY", "Licitacao - Tecnologia"),
    ("KAN-10", "DELIVERY", "Dev - SideWallet"),
    ("KAN-11", "DELIVERY", "Dev - BahiaGold"),
    ("KAN-12", "DELIVERY", "Dev - Avulsos"),
    ("KAN-13", "PRODUCT", "LexNotify AI"),
    ("KAN-14", "PRODUCT", "Hamza Carbon"),
    ("KAN-15", "PRODUCT", "NexusP2P"),
    ("KAN-16", "PRODUCT", "InceptionPsi"),
    ("KAN-17", "PRODUCT", "Shadpay"),
    ("KAN-18", "LIQUIDATION", "Venda APP Fintech"),
    ("KAN-19", "LIQUIDATION", "Venda Vrumm"),
    ("KAN-20", "LIQUIDATION", "Venda VotoMap"),
    ("KAN-21", "QUANT", "Pool de Liquidez"),
    ("KAN-22", "QUANT", "Funding Rate Arbitrage"),
    ("KAN-23", "QUANT", "HLP Vault"),
    ("KAN-24", "QUANT", "Arbitragem Stable/Spread"),
    ("KAN-25", "QUANT", "Nadaraya-Watson"),
    ("KAN-26", "QUANT", "kNN"),
    ("KAN-27", "QUANT", "MEV Quant Fund"),
]

DOR_DOD_TEMPLATE = {
    "GOV": "DoR:\n- Pendencia identificada com prazo\n- Responsavel definido (interno ou contador)\n- Documentos necessarios listados\n\nDoD:\n- Pendencia resolvida e evidencia anexada\n- Comprovante ou certidao disponivel\n- Sem debitos ou obrigacoes em aberto\n\nChecklist:\n- [ ] Escopo definido\n- [ ] Responsavel atribuido\n- [ ] Prazo definido\n- [ ] Evidencia anexada ao concluir",
    "OTC": "DoR:\n- Operacao com valor, par e canal definidos\n- KYT/KYC do cliente verificado\n- Contrato modelo selecionado\n\nDoD:\n- Contrato assinado e arquivado\n- Evidencia KYT/KYC anexada\n- Operacao conciliada (valores + taxas + comprovantes)\n- Comunicacao bancaria preparada quando necessario\n\nChecklist:\n- [ ] Cliente verificado (KYT/KYC)\n- [ ] Contrato assinado\n- [ ] Comprovantes anexados\n- [ ] Conciliacao feita",
    "DELIVERY": "DoR:\n- Escopo do entregavel definido\n- Prazo e orcamento estimados\n- Dependencias listadas\n\nDoD:\n- Entregavel validado (aceite, protocolo ou evidencia)\n- Custos/receita registrados\n- Proximo passo comercial definido\n\nChecklist:\n- [ ] Escopo documentado\n- [ ] Aceite do cliente\n- [ ] Custos registrados\n- [ ] Proximo passo definido",
    "PRODUCT": "DoR:\n- Objetivo em 1 frase\n- Criterios de aceite (3-7 bullets)\n- Ambiente/stack definido\n- Onde sera deployado\n\nDoD:\n- Criterios de aceitacao atendidos\n- Teste minimo executado\n- Deploy realizado (ou release preparado)\n- Rollback definido\n- Nota de release (5-10 linhas)\n\nChecklist:\n- [ ] Code review aprovado\n- [ ] Testes passando\n- [ ] Deploy em staging OK\n- [ ] Deploy em prod OK\n- [ ] Rollback testado",
    "LIQUIDATION": "DoR:\n- Ativo identificado com preco-alvo\n- Demo/video disponivel ou em preparacao\n- Escopo do que inclui definido\n\nDoD:\n- Deal room completo (1-pager, demo, video)\n- Proposta comercial enviada\n- Checklist de transferencia pronto\n\nChecklist:\n- [ ] 1-pager pronto\n- [ ] Demo funcional\n- [ ] Video gravado\n- [ ] Proposta enviada\n- [ ] Checklist de handover",
    "QUANT": "DoR:\n- Hipotese definida com metricas-alvo\n- Dados historicos disponveis\n- Ambiente de backtesting pronto\n\nDoD:\n- Backtest concluido com resultados documentados\n- Decisao go/no-go registrada\n- Se go: deploy em producao com monitoramento\n\nChecklist:\n- [ ] Hipotese documentada\n- [ ] Backtest executado\n- [ ] Resultados analisados\n- [ ] Risk limits definidos\n- [ ] Monitoramento configurado",
}

BACKLOG_TEMPLATE = {
    "GOV": "Backlog inicial (preencher com itens reais):\n- Levantar certidoes pendentes\n- Atualizar cadastro na Receita Federal\n- Verificar obrigacoes acessorias em atraso\n- Pagar guias/impostos pendentes\n- Emitir certidao negativa atualizada\n- Revisar procuracoes ativas\n- Atualizar contrato social se necessario\n- Conciliar extrato bancario PJ\n- Revisar alvara/licencas\n- Arquivar documentos do periodo",
    "OTC": "Backlog inicial (preencher com itens reais):\n- Mapear fluxo KYT com Foxbit\n- Criar template de contrato de intermediacao\n- Definir processo de comunicacao bancaria\n- Montar checklist de compliance por operacao\n- Preparar modelo de relatorio de conciliacao\n- Documentar processo de onboarding de cliente\n- Definir SLA com parceiros (Foxbit, banco)\n- Criar playbook de incidentes\n- Mapear riscos regulatorios\n- Treinar equipe no fluxo",
    "DELIVERY": "Backlog inicial (preencher com itens reais):\n- Montar proposta tecnica padrao\n- Preparar documentacao de habilitacao\n- Mapear portais de licitacao relevantes\n- Definir checklist de submissao\n- Criar template de orcamento\n- Mapear concorrentes por segmento\n- Definir criterios de go/no-go por licitacao\n- Preparar portfolio de cases\n- Definir processo de acompanhamento pos-submissao\n- Criar dashboard de pipeline",
    "PRODUCT": "Backlog inicial (preencher com itens reais):\n- Setup do ambiente de desenvolvimento\n- Definir arquitetura base (stack, infra, CI/CD)\n- Implementar autenticacao e autorizacao\n- Criar CRUD das entidades principais\n- Integrar com servicos externos\n- Implementar fluxo principal do usuario\n- Escrever testes unitarios e de integracao\n- Configurar deploy automatizado\n- Criar documentacao tecnica minima\n- Definir metricas de produto",
    "LIQUIDATION": "Backlog inicial (preencher com itens reais):\n- Preparar 1-pager da oferta\n- Fazer deploy simples para demo\n- Gravar video de demonstracao\n- Listar features + stack + o que inclui\n- Definir preco e condicoes comerciais\n- Preparar checklist de transferencia\n- Identificar buyers potenciais\n- Preparar NDA se necessario\n- Definir escopo de suporte pos-venda\n- Criar timeline de handover",
    "QUANT": "Backlog inicial (preencher com itens reais):\n- Definir hipotese e metricas-alvo\n- Coletar dados historicos necessarios\n- Configurar ambiente de backtesting\n- Implementar estrategia base\n- Executar backtesting inicial\n- Analisar resultados e ajustar parametros\n- Definir risk limits e stop-loss\n- Paper trading por X dias\n- Deploy em producao com capital minimo\n- Configurar monitoramento e alertas",
}

RISKS_TEMPLATE = {
    "GOV": "Riscos:\n- Multas por atraso em obrigacoes fiscais\n- Bloqueio de certidao negativa\n- Contador nao entregar no prazo\n- Mudanca de legislacao\n\nDependencias:\n- Contador externo\n- Receita Federal (prazos fixos)\n- Documentos de socios",
    "OTC": "Riscos:\n- Bloqueio bancario por falta de compliance\n- Foxbit alterar requisitos de KYT\n- Cliente nao fornecer documentos a tempo\n- Risco regulatorio (BACEN, CVM)\n\nDependencias:\n- Foxbit (KYT/KYC)\n- Banco (comunicacao e liquidacao)\n- Assessoria juridica (contratos)\n- Cliente (documentos)",
    "DELIVERY": "Riscos:\n- Perder prazo de submissao\n- Documentacao incompleta na habilitacao\n- Preco abaixo do custo\n- Recurso de concorrente\n\nDependencias:\n- Portais de licitacao\n- Documentos de habilitacao atualizados\n- Orcamento aprovado\n- Equipe tecnica disponivel",
    "PRODUCT": "Riscos:\n- Atraso no desenvolvimento\n- Bug critico em producao\n- Dependencia de API externa instavel\n- Falta de testes causa regressao\n\nDependencias:\n- Infra cloud (AWS/GCP/Vercel)\n- APIs externas (Supabase, WhatsApp, etc)\n- Equipe de desenvolvimento\n- Ambiente de staging/prod",
    "LIQUIDATION": "Riscos:\n- Nenhum buyer interessado\n- Preco abaixo do esperado\n- Ativo com bugs ou divida tecnica alta\n- Processo de handover complexo\n\nDependencias:\n- Deploy funcional para demo\n- Documentacao tecnica minima\n- Tempo para gravar video\n- Assessoria juridica para contrato de venda",
    "QUANT": "Riscos:\n- Perda de capital em producao\n- Modelo com overfitting no backtest\n- Mudanca de regime de mercado\n- Latencia/infra causa slippage\n\nDependencias:\n- Dados de mercado em tempo real\n- Infra de execucao (API exchanges)\n- Capital alocado\n- Monitoramento 24/7",
}

def passo2_kit_controle():
    print()
    print("=" * 60)
    print("PASSO 2: Kit de controle (3 tasks por epic)")
    print("=" * 60)
    results = []
    for epic_key, comp, epic_name in EPICS_DATA:
        print(f"\n  --- {epic_key} ({comp}) {epic_name} ---")
        labels_base = ["p2"]
        if comp == "OTC":
            labels_base.append("legal")

        # Task A: SOP + DoR/DoD
        desc_a = DOR_DOD_TEMPLATE.get(comp, DOR_DOD_TEMPLATE["PRODUCT"])
        k1 = create_issue(
            f"[{epic_name}] SOP + DoR/DoD + Checklists",
            "Tarefa", comp, labels_base,
            desc_a, epic_key
        )
        print(f"    A) {k1}")
        results.append(("Task-A", epic_key, k1))
        time.sleep(0.3)

        # Task B: Backlog inicial
        desc_b = BACKLOG_TEMPLATE.get(comp, BACKLOG_TEMPLATE["PRODUCT"])
        k2 = create_issue(
            f"[{epic_name}] Backlog inicial (ate 10 itens)",
            "Tarefa", comp, labels_base,
            desc_b, epic_key
        )
        print(f"    B) {k2}")
        results.append(("Task-B", epic_key, k2))
        time.sleep(0.3)

        # Task C: Riscos & Dependencias
        labels_c = list(labels_base)
        if comp == "PRODUCT":
            labels_c.append("infra")
        desc_c = RISKS_TEMPLATE.get(comp, RISKS_TEMPLATE["PRODUCT"])
        k3 = create_issue(
            f"[{epic_name}] Riscos & Dependencias",
            "Tarefa", comp, labels_c,
            desc_c, epic_key
        )
        print(f"    C) {k3}")
        results.append(("Task-C", epic_key, k3))
        time.sleep(0.3)

    return results


# ============================================================
# PASSO 3: Sprint-0 backlog real (4 epics prioritarias)
# ============================================================

def passo3_sprint0():
    print()
    print("=" * 60)
    print("PASSO 3: Sprint-0 (backlog real em 4 epics)")
    print("=" * 60)
    results = []

    # --- EPIC KAN-13: LexNotify AI ---
    print("\n  --- KAN-13: LexNotify AI ---")
    lexnotify_items = [
        ("Integracao Supabase (auth + db + storage)",
         "Configurar Supabase como backend: autenticacao (email/magic link), banco de dados (tabelas principais), storage para arquivos.\n\nCriterios de aceite:\n- Auth funcional com login/logout/registro\n- Tabelas principais criadas (users, tasks, docs, notifications)\n- Upload de arquivos funcional (ate 10MB)\n- Row Level Security configurado\n- Variaveis de ambiente em .env (nao hardcoded)"),
        ("Integracao WhatsApp (stub + fluxo de notificacao)",
         "Implementar integracao com WhatsApp para envio de notificacoes aos clientes.\n\nCriterios de aceite:\n- Stub de envio funcional (API oficial ou Evolution API)\n- Template de mensagem padrao definido\n- Fila de envio implementada (nao sincrono)\n- Retry em caso de falha (ate 3 tentativas)\n- Log de envios (sucesso/falha) persistido"),
        ("Kanban + tarefas (CRUD completo + transicoes de status)",
         "Implementar modulo de kanban com CRUD de tarefas e transicoes de status.\n\nCriterios de aceite:\n- CRUD de tarefas (criar, ler, atualizar, deletar)\n- Board kanban com drag-and-drop\n- Status: A fazer, Fazendo, Feito\n- Filtro por responsavel e prioridade\n- Persistencia no Supabase em tempo real"),
        ("Upload e gestao de documentos (PDF/DOCX/imagens)",
         "Implementar upload, visualizacao e gestao de documentos.\n\nCriterios de aceite:\n- Upload de PDF, DOCX e imagens (JPG/PNG)\n- Preview inline de PDFs e imagens\n- Limite de tamanho (10MB por arquivo)\n- Organizacao por pasta/categoria\n- Download funcional\n- Exclusao com confirmacao"),
        ("Automacoes basicas (triagem inicial de demandas)",
         "Implementar regras de automacao para triagem inicial de demandas recebidas.\n\nCriterios de aceite:\n- Regra: nova demanda recebida -> notificacao para responsavel\n- Regra: demanda sem resposta em 24h -> escalar prioridade\n- Regra: demanda concluida -> notificar cliente\n- Interface para ativar/desativar regras\n- Log de automacoes executadas"),
        ("Testes minimos (unitarios + integracao)",
         "Escrever testes minimos para garantir estabilidade.\n\nCriterios de aceite:\n- Testes unitarios para funcoes de negocio criticas\n- Teste de integracao para fluxo de auth\n- Teste de integracao para CRUD de tarefas\n- Cobertura minima de 40% no core\n- CI rodando testes automaticamente"),
        ("Deploy + rollback + runbook",
         "Configurar pipeline de deploy com rollback e documentar runbook.\n\nCriterios de aceite:\n- Deploy automatizado (Vercel/Railway/Docker)\n- Rollback funcional em menos de 5 minutos\n- Runbook documentado (como deployar, como reverter, como debugar)\n- Variaveis de ambiente configuradas em producao\n- Health check endpoint funcionando\n- SSL configurado"),
        ("Onboarding cliente (checklist + fluxo primeiro acesso)",
         "Criar fluxo de onboarding para primeiro acesso do cliente.\n\nCriterios de aceite:\n- Wizard de primeiro acesso (3-5 passos)\n- Checklist de configuracao inicial\n- Email de boas-vindas automatico\n- Tour guiado das funcionalidades principais\n- Documentacao de ajuda inline"),
    ]
    for summary, desc in lexnotify_items:
        k = create_issue(summary, "Tarefa", "PRODUCT", ["p1"], desc, "KAN-13")
        print(f"    {k}: {summary[:50]}")
        results.append(("Sprint0-LexNotify", k))
        time.sleep(0.3)

    # --- EPIC KAN-14: Hamza Carbon ---
    print("\n  --- KAN-14: Hamza Carbon ---")
    hamza_items = [
        ("Checklist mainnet readiness",
         "Validar que todos os requisitos para deploy em mainnet estao atendidos.\n\nCriterios de aceite:\n- Smart contracts auditados (ou revisao interna documentada)\n- Gas costs estimados e documentados\n- Fallback/pause mechanism implementado\n- Chaves de deploy seguras (multisig ou hardware wallet)\n- Testnet funcional sem bugs criticos por 7+ dias"),
        ("Fluxo compra/venda real (UI + backend)",
         "Implementar fluxo completo de compra e venda de creditos de carbono.\n\nCriterios de aceite:\n- UI de compra com selecao de quantidade e preco\n- UI de venda com listagem de ativos do usuario\n- Backend processando transacoes on-chain\n- Confirmacao de transacao com hash\n- Historico de transacoes visivel\n- Tratamento de erros (saldo insuficiente, gas alto)"),
        ("Wallet auto-criacao hardening",
         "Endurecer o sistema de criacao automatica de wallets.\n\nCriterios de aceite:\n- Wallet criada automaticamente no registro do usuario\n- Chave privada nunca exposta no frontend\n- Backup/recovery documentado\n- Rate limiting na criacao\n- Logs de criacao para auditoria"),
        ("Integracao liquidez (Foxbit - preparar docs e fluxo)",
         "Preparar documentacao e fluxo para integracao de liquidez com Foxbit.\n\nCriterios de aceite:\n- Documentacao da API Foxbit mapeada\n- Fluxo de on-ramp/off-ramp desenhado\n- Requisitos regulatorios listados\n- Contrato/acordo de parceria em preparacao\n- Estimativa de volume e custos"),
        ("Seguranca basica + logs estruturados",
         "Implementar camada minima de seguranca e logging.\n\nCriterios de aceite:\n- Rate limiting nas APIs\n- Input validation em todos os endpoints\n- Logs estruturados (JSON) com correlationId\n- Alertas para erros criticos\n- CORS configurado corretamente\n- Headers de seguranca (CSP, HSTS)"),
        ("Deploy prod + monitoramento",
         "Configurar deploy em producao com monitoramento.\n\nCriterios de aceite:\n- Deploy automatizado em producao\n- Monitoramento de uptime (healthcheck)\n- Dashboard de metricas basicas\n- Alertas para downtime e erros 5xx\n- Runbook de incidentes documentado\n- Backup de dados configurado"),
    ]
    for summary, desc in hamza_items:
        k = create_issue(summary, "Tarefa", "PRODUCT", ["p1"], desc, "KAN-14")
        print(f"    {k}: {summary[:50]}")
        results.append(("Sprint0-Hamza", k))
        time.sleep(0.3)

    # --- EPIC KAN-6: OTC Compliance ---
    print("\n  --- KAN-6: OTC Compliance ---")
    otc_items = [
        ("Modelo contrato intermediacao (Pix + comunicacao banco)",
         "Criar modelo padrao de contrato para intermediacao de criptoativos.\n\nCriterios de aceite:\n- Template de contrato revisado por assessoria juridica\n- Clausulas de risco e responsabilidade definidas\n- Fluxo Pix documentado (entrada e saida)\n- Modelo de comunicacao bancaria padrao\n- Versao PDF e DOCX disponivel\n- Checklist de preenchimento por operacao"),
        ("Checklist KYT/KYC e evidencias",
         "Criar checklist padrao de KYT/KYC para cada operacao.\n\nCriterios de aceite:\n- Lista de documentos obrigatorios por tipo de cliente (PF/PJ)\n- Template de analise de risco\n- Processo de verificacao documentado\n- Modelo de relatorio de evidencias\n- Arquivo padrao para armazenar evidencias\n- SLA de verificacao definido (ex: 24h)"),
        ("Fluxo operacional de intermediacao 1 BTC",
         "Documentar e validar o fluxo completo de intermediacao de 1 BTC.\n\nCriterios de aceite:\n- Diagrama de fluxo do inicio ao fim\n- Checklist por etapa (KYT, contrato, execucao, liquidacao)\n- Pontos de controle e aprovacao definidos\n- Estimativa de tempo por etapa\n- Riscos por etapa documentados\n- Fluxo testado em operacao simulada"),
        ("Pendencias Foxbit (documentos) + SLA",
         "Resolver pendencias documentais com Foxbit e definir SLAs.\n\nCriterios de aceite:\n- Lista de documentos pendentes levantada com Foxbit\n- Documentos enviados e confirmados\n- SLA de resposta definido (ex: 3 dias uteis)\n- Contato direto estabelecido (nome + email + telefone)\n- Processo de escalonamento definido"),
        ("Rotina de conciliacao e comprovacao",
         "Implementar rotina de conciliacao pos-operacao.\n\nCriterios de aceite:\n- Template de conciliacao (valores, taxas, spread, comprovantes)\n- Processo de conferencia de comprovantes bancarios\n- Arquivo de operacoes conciliadas (planilha ou sistema)\n- Frequencia definida (diaria ou por operacao)\n- Responsavel definido"),
        ("Playbook de incidentes (banco/travamento/bloqueio)",
         "Criar playbook para tratar incidentes operacionais.\n\nCriterios de aceite:\n- Cenarios mapeados: bloqueio bancario, travamento Foxbit, cliente nao paga\n- Procedimento passo-a-passo para cada cenario\n- Contatos de emergencia listados (banco, Foxbit, juridico)\n- Template de comunicacao para cada tipo de incidente\n- Tempo maximo de resposta definido por severidade"),
    ]
    for summary, desc in otc_items:
        k = create_issue(summary, "Tarefa", "OTC", ["p1", "legal"], desc, "KAN-6")
        print(f"    {k}: {summary[:50]}")
        results.append(("Sprint0-OTC", k))
        time.sleep(0.3)

    # --- EPIC KAN-18: Venda APP Fintech ---
    print("\n  --- KAN-18: Venda APP Fintech ---")
    fintech_items = [
        ("Deal room 1-pager (oferta comercial)",
         "Criar documento 1-pager com proposta de venda do ativo.\n\nCriterios de aceite:\n- Resumo do produto (o que faz, para quem)\n- Stack tecnologico listado\n- Metricas do produto (se houver: usuarios, transacoes)\n- Preco pedido e condicoes\n- O que esta incluido na venda\n- Contato para negociacao"),
        ("Demo (deploy simples) ou video demo",
         "Preparar demonstracao funcional do produto.\n\nCriterios de aceite:\n- App deployado em URL publica para demo\n- Dados de demonstracao carregados\n- Credenciais de acesso para demo\n- OU: video de 3-5 minutos mostrando funcionalidades\n- Roteiro do demo documentado"),
        ("Lista de features + stack + o que inclui",
         "Documentar tudo que o buyer recebe na compra.\n\nCriterios de aceite:\n- Lista completa de features implementadas\n- Stack tecnologico (linguagens, frameworks, banco, infra)\n- Repositorios incluidos (listados)\n- Documentacao tecnica existente\n- Licencas de terceiros listadas\n- Divida tecnica conhecida documentada"),
        ("Checklist de transferencia (handover)",
         "Criar checklist completo para transferencia do ativo ao comprador.\n\nCriterios de aceite:\n- Acesso aos repositorios (GitHub/GitLab)\n- Transfer de dominio (se aplicavel)\n- Credenciais de servicos (cloud, APIs)\n- Documentacao de ambiente\n- Sessao de handover tecnico (2-4h agendada)\n- Periodo de suporte pos-venda definido"),
        ("Definir preco e condicoes comerciais",
         "Definir precificacao e termos de venda.\n\nCriterios de aceite:\n- Preco minimo e preco-alvo definidos\n- Condicoes de pagamento (a vista, parcelado)\n- O que inclui e o que nao inclui\n- Suporte pos-venda: escopo e duracao\n- Clausula de nao-competicao (se aplicavel)\n- Garantias oferecidas"),
        ("Identificar e abordar buyers potenciais",
         "Mapear e fazer primeiro contato com potenciais compradores.\n\nCriterios de aceite:\n- Lista de 5-10 buyers potenciais identificados\n- Criterios de qualificacao definidos\n- Template de abordagem (email/LinkedIn) criado\n- Primeiro contato realizado com pelo menos 3 buyers\n- Pipeline de vendas atualizado"),
        ("Preparar NDA e contrato de venda",
         "Preparar documentacao juridica para venda.\n\nCriterios de aceite:\n- Template de NDA pronto\n- Template de contrato de compra e venda de software\n- Clausulas de propriedade intelectual definidas\n- Revisao juridica realizada\n- Versoes PDF e DOCX disponiveis"),
    ]
    for summary, desc in fintech_items:
        k = create_issue(summary, "Tarefa", "LIQUIDATION", ["p1"], desc, "KAN-18")
        print(f"    {k}: {summary[:50]}")
        results.append(("Sprint0-Fintech", k))
        time.sleep(0.3)

    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("Jira Executor - Inicio")
    print()

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "1"):
        passo1_padronizar_epics()

    if mode in ("all", "2"):
        passo2_kit_controle()

    if mode in ("all", "3"):
        passo3_sprint0()

    print()
    print("=" * 60)
    print("EXECUCAO CONCLUIDA")
    print("=" * 60)
