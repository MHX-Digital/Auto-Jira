"""
NexusP2P — Atualizacao completa do Jira (KAN-15)
- Atualiza tasks existentes (KAN-61, 62, 63) como Concluidas
- Atualiza descricao do Epic KAN-15
- Cria 26 novas tasks do POST_BETA_SOW para Junho/2026
- Concluidas ficam em "Concluido", pendentes em "A fazer"
"""
import os, sys, json, base64, urllib.request, urllib.error, time

# --- Auth ---
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()
BASE = os.environ['JIRA_BASE_URL']
EMAIL = os.environ['JIRA_EMAIL']
TOKEN = os.environ['JIRA_API_TOKEN']
CREDS = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
HEADERS = {
    'Authorization': f'Basic {CREDS}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}
DRY_RUN = '--dry-run' in sys.argv

def api(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        resp = urllib.request.urlopen(req)
        raw = resp.read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"  [ERRO] {method} {path}: {e.code} {err[:300]}")
        return None

def adf_doc(blocks):
    return {"type": "doc", "version": 1, "content": blocks}

def adf_heading(text, level=3):
    return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}

def adf_paragraph(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

def adf_bold_text(text):
    return {"type": "text", "text": text, "marks": [{"type": "strong"}]}

def adf_paragraph_mixed(items):
    return {"type": "paragraph", "content": items}

def adf_bullet_list(items):
    list_items = []
    for item in items:
        list_items.append({
            "type": "listItem",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": item}]}]
        })
    return {"type": "bulletList", "content": list_items}

def adf_status(text, color="neutral"):
    """color: neutral, blue, green, yellow, red"""
    return {"type": "status", "attrs": {"text": text, "color": color}}

def adf_rule():
    return {"type": "rule"}

# --- Transitions ---
def get_transitions(issue_key):
    data = api('GET', f'/rest/api/3/issue/{issue_key}/transitions')
    return data.get('transitions', []) if data else []

def transition_to(issue_key, target_status):
    transitions = get_transitions(issue_key)
    for t in transitions:
        if target_status.lower() in t['name'].lower():
            if DRY_RUN:
                print(f"  [DRY] Transicao {issue_key} -> {t['name']} (id={t['id']})")
                return True
            result = api('POST', f'/rest/api/3/issue/{issue_key}/transitions', {"transition": {"id": t['id']}})
            if result is not None:
                print(f"  [OK] {issue_key} -> {t['name']}")
                return True
    print(f"  [!!] Nao encontrou transicao para '{target_status}' em {issue_key}")
    print(f"       Disponiveis: {[t['name'] for t in transitions]}")
    return False

def update_issue(issue_key, fields):
    if DRY_RUN:
        print(f"  [DRY] Update {issue_key}: {list(fields.keys())}")
        return True
    result = api('PUT', f'/rest/api/3/issue/{issue_key}', {"fields": fields})
    if result is not None:
        print(f"  [OK] {issue_key} atualizado")
        return True
    return False

def create_issue(summary, description_adf, parent_key, labels=None, due_date=None):
    fields = {
        "project": {"key": "KAN"},
        "parent": {"key": parent_key},
        "issuetype": {"name": "Tarefa"},
        "summary": summary,
        "description": description_adf,
    }
    if labels:
        fields["labels"] = labels
    if due_date:
        fields["duedate"] = due_date
    if DRY_RUN:
        print(f"  [DRY] Criar: {summary} (parent={parent_key}, due={due_date})")
        return "KAN-DRY"
    result = api('POST', '/rest/api/3/issue', {"fields": fields})
    if result and 'key' in result:
        print(f"  [OK] Criada: {result['key']} - {summary}")
        return result['key']
    else:
        print(f"  [ERRO] Falha ao criar: {summary}")
        return None

# ============================================================
# 1. ATUALIZAR EPIC KAN-15
# ============================================================
print("=" * 60)
print("NEXUSP2P - ATUALIZACAO JIRA")
print("=" * 60)

print("\n[1/4] Atualizando Epic KAN-15...")
epic_desc = adf_doc([
    adf_heading("NexusP2P - Plataforma P2P de Criptomoedas", 2),
    adf_paragraph("Plataforma web completa para compra e venda P2P de criptomoedas com integracao Bitstamp/CoinGecko, PIX estatico, KYC 3 niveis, notificacoes Telegram."),
    adf_rule(),
    adf_heading("Stack", 3),
    adf_bullet_list([
        "Frontend: React 18 + Vite + Tailwind CSS + Framer Motion",
        "Backend: Express.js + TypeScript 5",
        "Banco: Supabase (PostgreSQL) com RLS",
        "Cache: Redis (ioredis) + BullMQ",
        "Auth: Supabase Auth (JWT)",
        "Monitoramento: Sentry + Winston + Telegram Bot",
        "Deploy: Railway (backend + frontend)",
    ]),
    adf_rule(),
    adf_heading("URLs", 3),
    adf_bullet_list([
        "Frontend: https://www.nexusp2p.finance",
        "Backend: https://nexus-p2p-backend-nexus-p2p-api.up.railway.app",
        "Ativos: BTC, ETH, SOL, USDT, USDC",
    ]),
    adf_rule(),
    adf_heading("Status (20/02/2026)", 3),
    adf_paragraph("Beta concluido (~85% do SOW). Faltam 26 itens para producao (POST_BETA_SOW). Deadline: Junho 2026."),
    adf_heading("Fases Concluidas", 4),
    adf_bullet_list([
        "[DONE] Fase 1: Setup e Infra",
        "[DONE] Fase 2: Autenticacao e Landing Page",
        "[DONE] Fase 3: Dashboard Base",
        "[DONE] Fase 4: Sistema de Negociacao",
        "[DONE] Fase 5: KYC (3 niveis)",
        "[DONE] Fase 10: Deploy (Railway)",
        "[PARCIAL] Fase 6: Configuracoes e Seguranca (falta 2FA, sessoes)",
        "[PARCIAL] Fase 7: Notificacoes (falta email, SMS)",
        "[PENDENTE] Fase 8: Polimento e Otimizacao",
        "[PENDENTE] Fase 9: Testes e Homologacao",
    ]),
])
update_issue("KAN-15", {"description": epic_desc})

# ============================================================
# 2. ATUALIZAR TASKS EXISTENTES COMO CONCLUIDAS
# ============================================================
print("\n[2/4] Atualizando tasks existentes...")

# KAN-61: SOP + DoR/DoD — Concluida (processos definidos no PROJECT_STATUS)
desc_61 = adf_doc([
    adf_heading("SOP + DoR/DoD + Checklists", 3),
    adf_paragraph("[CONCLUIDA] Processos definidos e documentados no PROJECT_STATUS.md e SOW."),
    adf_rule(),
    adf_heading("DoR (Definition of Ready)", 4),
    adf_bullet_list([
        "[OK] Objetivo em 1 frase",
        "[OK] Criterios de aceite (3-7 bullets)",
        "[OK] Ambiente/stack definido (React+Vite+Express+Supabase+Railway)",
        "[OK] Onde sera deployado (Railway)",
    ]),
    adf_heading("DoD (Definition of Done)", 4),
    adf_bullet_list([
        "[OK] Criterios de aceitacao atendidos",
        "[OK] Deploy realizado (Railway prod)",
        "[OK] Rollback definido (Railway rollback)",
        "[OK] PROJECT_STATUS.md atualizado",
    ]),
])
update_issue("KAN-61", {"description": desc_61})
transition_to("KAN-61", "conclu")
time.sleep(0.3)

# KAN-62: Backlog inicial — Concluida (8/10 itens done)
desc_62 = adf_doc([
    adf_heading("Backlog Inicial (10 itens)", 3),
    adf_paragraph("[CONCLUIDA] 8/10 itens implementados no beta. Itens pendentes movidos para POST_BETA_SOW."),
    adf_rule(),
    adf_bullet_list([
        "[DONE] Setup do ambiente de desenvolvimento",
        "[DONE] Definir arquitetura base (React+Vite+Express+Supabase+Railway)",
        "[DONE] Implementar autenticacao e autorizacao (Supabase Auth)",
        "[DONE] Criar CRUD das entidades principais (orders, KYC, bank accounts)",
        "[DONE] Integrar com servicos externos (Bitstamp, CoinGecko, Telegram)",
        "[DONE] Implementar fluxo principal do usuario (compra/venda P2P)",
        "[PENDENTE -> POST_BETA] Escrever testes unitarios e de integracao",
        "[DONE] Configurar deploy automatizado (Railway)",
        "[PARCIAL -> POST_BETA] Criar documentacao tecnica (falta Swagger)",
        "[PENDENTE -> POST_BETA] Definir metricas de produto (falta APM)",
    ]),
])
update_issue("KAN-62", {"description": desc_62})
transition_to("KAN-62", "conclu")
time.sleep(0.3)

# KAN-63: Riscos & Dependencias — Concluida (riscos mapeados)
desc_63 = adf_doc([
    adf_heading("Riscos e Dependencias", 3),
    adf_paragraph("[CONCLUIDA] Riscos mapeados e mitigados no beta. Dependencias externas documentadas no POST_BETA_SOW."),
    adf_rule(),
    adf_heading("Riscos Mitigados", 4),
    adf_bullet_list([
        "[MITIGADO] Atraso no dev -> Beta entregue em 85%",
        "[MITIGADO] Bug critico -> Sentry + Telegram alerts ativos",
        "[MITIGADO] API externa instavel -> Fallback Bitstamp/CoinGecko implementado",
        "[MITIGADO] Falta de testes -> Identificado como item POST_BETA",
    ]),
    adf_heading("Dependencias Externas (Pendentes)", 4),
    adf_bullet_list([
        "[PENDENTE] BB API (PIX dinamico) -> Aguardando cadastro/aprovacao",
        "[PENDENTE] Resend/SendGrid (email transacional)",
        "[PENDENTE] Twilio/SNS (SMS verificacao)",
        "[PENDENTE] Google reCAPTCHA v3",
        "[OK] Supabase Cloud -> Configurado",
        "[OK] Railway (hosting) -> Configurado",
        "[OK] Telegram Bot -> Configurado",
    ]),
])
update_issue("KAN-63", {"description": desc_63})
transition_to("KAN-63", "conclu")
time.sleep(0.3)

# ============================================================
# 3. CRIAR NOVAS TASKS DO POST_BETA_SOW
# ============================================================
print("\n[3/4] Criando tasks POST_BETA_SOW...")

# Deadline: Junho 2026
# Sprint 1 (Seguranca): marco
# Sprint 2 (Pagamentos): abril
# Sprint 3 (Comunicacao): abril-maio
# Sprint 4 (Tecnico): maio
# Sprint 5 (Admin+Polish): junho

SPRINT_DATES = {
    "sprint1": "2026-03-31",  # Seguranca
    "sprint2": "2026-04-30",  # Pagamentos
    "sprint3": "2026-05-15",  # Comunicacao
    "sprint4": "2026-05-31",  # Tecnico
    "sprint5": "2026-06-30",  # Admin + Polish
}

new_tasks = [
    # ---- SEGURANCA (Sprint 1) ----
    {
        "summary": "[NexusP2P] S1 - 2FA (TOTP) via Google Authenticator/Authy",
        "labels": ["p1", "security"],
        "sprint": "sprint1",
        "desc_blocks": [
            adf_heading("2FA - Autenticacao de Dois Fatores (TOTP)", 3),
            adf_paragraph("Implementar autenticacao de dois fatores via app (Google Authenticator, Authy). PRIORIDADE CRITICA."),
            adf_rule(),
            adf_heading("Escopo", 4),
            adf_bullet_list([
                "Gerar QR Code para registro no app authenticator",
                "Gerar backup codes (8-10 codigos de uso unico)",
                "Validar codigo TOTP em operacoes financeiras (compra/venda)",
                "Opcao de ativar/desativar nas configuracoes de seguranca",
                "Lib sugerida: speakeasy + qrcode",
            ]),
            adf_heading("Criterios de Aceite", 4),
            adf_bullet_list([
                "Usuario consegue ativar 2FA via QR Code",
                "Backup codes gerados e exibidos uma unica vez",
                "Operacoes financeiras exigem codigo 2FA quando ativo",
                "Desativar 2FA requer senha + codigo valido",
            ]),
            adf_paragraph("Esforco estimado: 3-5 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] S2 - Sessoes ativas (listar/revogar dispositivos)",
        "labels": ["p1", "security"],
        "sprint": "sprint1",
        "desc_blocks": [
            adf_heading("Sessoes Ativas", 3),
            adf_paragraph("Listar dispositivos conectados com opcao de revogar sessao."),
            adf_rule(),
            adf_heading("Escopo", 4),
            adf_bullet_list([
                "Listar sessoes: IP, browser/OS, ultimo acesso, geolocalizacao",
                "Badge 'Atual' na sessao ativa",
                "Botao 'Encerrar' para cada sessao",
                "Botao 'Encerrar Todas as Outras Sessoes'",
                "Registrar em security_events",
            ]),
            adf_heading("Criterios de Aceite", 4),
            adf_bullet_list([
                "Usuario ve todas sessoes ativas com detalhes",
                "Revogar sessao invalida o token JWT correspondente",
                "Notificacao Telegram quando sessao e revogada",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] S3 - Historico de logins (tabela com IP/device/status)",
        "labels": ["p2", "security"],
        "sprint": "sprint1",
        "desc_blocks": [
            adf_heading("Historico de Logins", 3),
            adf_paragraph("Tabela com historico completo de tentativas de login."),
            adf_rule(),
            adf_heading("Campos", 4),
            adf_bullet_list([
                "Data/hora",
                "IP de origem",
                "Device (browser + SO)",
                "Status (sucesso/falha)",
                "Geolocalizacao (via ip-api.com)",
            ]),
            adf_heading("Criterios de Aceite", 4),
            adf_bullet_list([
                "Tabela paginada com filtros (periodo, status)",
                "Alerta visual para tentativas falhadas recentes (>3)",
                "Dados reais do security_events",
            ]),
            adf_paragraph("Esforco estimado: 1-2 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] S4 - reCAPTCHA v3 (login/registro/recuperacao)",
        "labels": ["p2", "security"],
        "sprint": "sprint1",
        "desc_blocks": [
            adf_heading("reCAPTCHA v3", 3),
            adf_paragraph("Protecao anti-bot no login, registro e recuperacao de senha."),
            adf_rule(),
            adf_bullet_list([
                "Google reCAPTCHA v3 (invisible, score-based)",
                "Threshold: score < 0.5 bloqueia",
                "Backend valida token com API Google",
                "Aplicar em: /auth/login, /auth/register, /auth/forgot-password",
            ]),
            adf_paragraph("Esforco estimado: 1 dia"),
        ],
    },

    # ---- PAGAMENTOS (Sprint 2) ----
    {
        "summary": "[NexusP2P] P1 - PIX Dinamico via BB API",
        "labels": ["p1", "infra"],
        "sprint": "sprint2",
        "desc_blocks": [
            adf_heading("PIX Dinamico - API Banco do Brasil", 3),
            adf_paragraph("Integracao com API BB para gerar QR Codes dinamicos com valor pre-definido e vencimento. PRIORIDADE ALTA."),
            adf_rule(),
            adf_heading("Escopo", 4),
            adf_bullet_list([
                "Cadastro na plataforma BB Developers",
                "Gerar QR Code dinamico com valor exato da ordem",
                "Vencimento do QR Code = 30 minutos",
                "Identificacao automatica do pagador via txid",
                "Substituir PIX estatico atual pelo dinamico",
            ]),
            adf_heading("Dependencia", 4),
            adf_paragraph("Requer cadastro/aprovacao na plataforma BB Developers (responsavel: MH Tecnologia)."),
            adf_paragraph("Esforco estimado: 5-8 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] P2 - Webhook confirmacao PIX automatica",
        "labels": ["p1", "infra"],
        "sprint": "sprint2",
        "desc_blocks": [
            adf_heading("Webhook Confirmacao PIX", 3),
            adf_paragraph("Receber notificacao automatica quando pagamento PIX e confirmado. Elimina processamento manual."),
            adf_rule(),
            adf_bullet_list([
                "Endpoint webhook: POST /api/webhooks/pix",
                "Validar assinatura do BB API",
                "Atualizar status da ordem: AWAITING_PAYMENT -> PAYMENT_RECEIVED",
                "Disparar notificacao Telegram + in-app",
                "Retry com backoff exponencial via BullMQ",
            ]),
            adf_paragraph("Esforco estimado: 3-5 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] P3 - PIX automatico para vendas (payout)",
        "labels": ["p1", "infra"],
        "sprint": "sprint2",
        "desc_blocks": [
            adf_heading("PIX Automatico para Vendas (Payout)", 3),
            adf_paragraph("Transferencia PIX automatica para conta do usuario apos admin aprovar venda."),
            adf_rule(),
            adf_bullet_list([
                "Usar BB API para iniciar transferencia PIX",
                "Debitar saldo interno NexusP2P",
                "Creditar na chave PIX do usuario",
                "Status: PROCESSING -> COMPLETED",
                "Fallback: se PIX falhar, manter BRL na conta e notificar",
            ]),
            adf_paragraph("Esforco estimado: 3-5 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] P4 - WebSocket tracking status de ordens",
        "labels": ["p2", "infra"],
        "sprint": "sprint2",
        "desc_blocks": [
            adf_heading("WebSocket - Tracking de Status em Tempo Real", 3),
            adf_paragraph("Atualizacao em tempo real do status da ordem no frontend via Socket.io."),
            adf_rule(),
            adf_bullet_list([
                "Backend ja tem Socket.io configurado (pricing)",
                "Adicionar canal: order:{orderId} com eventos de status",
                "Frontend: conectar Socket.io client no PixPaymentModal",
                "Status: AWAITING_PAYMENT -> PAYMENT_RECEIVED -> PROCESSING -> COMPLETED",
                "Eliminar polling de status no frontend",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },

    # ---- COMUNICACAO (Sprint 3) ----
    {
        "summary": "[NexusP2P] C1 - Email transacional (Resend/SendGrid)",
        "labels": ["p2"],
        "sprint": "sprint3",
        "desc_blocks": [
            adf_heading("Email Transacional", 3),
            adf_paragraph("Integrar servico de email para envio de emails transacionais."),
            adf_rule(),
            adf_heading("Emails a implementar", 4),
            adf_bullet_list([
                "Confirmacao de conta (verificacao de email)",
                "Reset de senha",
                "Comprovante de transacao (compra/venda)",
                "Alerta de seguranca (novo login, alteracao de senha)",
                "Atualizacao de status KYC",
            ]),
            adf_heading("Dependencia", 4),
            adf_paragraph("Escolher provider: Resend (recomendado, mais simples) ou SendGrid."),
            adf_paragraph("Esforco estimado: 3-5 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] C2 - SMS verificacao telefone (Twilio/SNS)",
        "labels": ["p2"],
        "sprint": "sprint3",
        "desc_blocks": [
            adf_heading("SMS Verificacao de Telefone", 3),
            adf_paragraph("Verificacao de telefone via SMS no KYC Level 1."),
            adf_rule(),
            adf_bullet_list([
                "Enviar codigo de 6 digitos via SMS",
                "Validar codigo no backend (expira em 5 min)",
                "Reenviar codigo (rate limit: 1/60s)",
                "Provider: Twilio (recomendado) ou AWS SNS",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] C3 - Pagina completa de historico de notificacoes",
        "labels": ["p3"],
        "sprint": "sprint3",
        "desc_blocks": [
            adf_heading("Pagina de Historico de Notificacoes", 3),
            adf_paragraph("Pagina completa com filtros, paginacao e busca. Atualmente so existe dropdown."),
            adf_rule(),
            adf_bullet_list([
                "Rota: /dashboard/notifications",
                "Tabela paginada (20 itens/pagina)",
                "Filtros: tipo (transacao, seguranca, KYC, sistema)",
                "Busca por texto",
                "Marcar como lida / Marcar todas como lidas",
                "Limpar notificacoes antigas",
            ]),
            adf_paragraph("Esforco estimado: 2 dias"),
        ],
    },

    # ---- TECNICO (Sprint 4) ----
    {
        "summary": "[NexusP2P] T1 - Migrar state management para Zustand",
        "labels": ["p2"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("Migracao para Zustand", 3),
            adf_paragraph("Migrar state management de Context API para Zustand (performance, devtools)."),
            adf_rule(),
            adf_bullet_list([
                "Criar stores: authStore, cryptoStore, uiStore, tradeStore",
                "Substituir AuthContext por useAuthStore",
                "Substituir SidebarContext por useUIStore",
                "Manter compatibilidade com hooks existentes",
                "Habilitar Zustand devtools em dev",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] T2 - Migrar para TanStack Query (cache/refetch)",
        "labels": ["p2"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("Migracao para TanStack Query", 3),
            adf_paragraph("Substituir fetch manual por TanStack Query para cache, refetch, optimistic updates."),
            adf_rule(),
            adf_bullet_list([
                "QueryClientProvider no root",
                "Migrar hooks: useWallet, useTransactions, useBankAccounts, useNotifications",
                "Configurar staleTime e cacheTime por query",
                "Optimistic updates para operacoes CRUD",
                "Prefetch de dados do dashboard",
            ]),
            adf_paragraph("Esforco estimado: 3-5 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] T3 - React Hook Form + Zod (validacao)",
        "labels": ["p3"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("React Hook Form + Zod", 3),
            adf_paragraph("Migrar formularios para React Hook Form com validacao Zod."),
            adf_rule(),
            adf_bullet_list([
                "Formularios alvo: KYC Level 1/2/3, Trade (Buy/Sell), Settings, Bank Accounts",
                "Schemas Zod para cada formulario",
                "Validacao client-side + server-side",
                "Mensagens de erro em portugues",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] T4 - Socket.io-client no frontend (cotacoes real-time)",
        "labels": ["p2"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("Socket.io Client - Frontend", 3),
            adf_paragraph("Conectar frontend ao WebSocket do backend para cotacoes em tempo real."),
            adf_rule(),
            adf_bullet_list([
                "Backend ja tem Socket.io configurado para pricing",
                "Criar hook: useSocketPrice (substitui polling atual)",
                "Atualizar CryptoTicker na landing page via WS",
                "Atualizar TradePanel com preco ao vivo",
                "Reconexao automatica com backoff",
            ]),
            adf_paragraph("Esforco estimado: 1-2 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] T5 - Swagger/OpenAPI documentacao da API",
        "labels": ["p3"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("Swagger/OpenAPI Docs", 3),
            adf_paragraph("Documentar todos os endpoints da API com swagger-jsdoc."),
            adf_rule(),
            adf_bullet_list([
                "Instalar swagger-jsdoc + swagger-ui-express",
                "Documentar: Auth, P2P, Trade, User, KYC, History, Notifications, Admin",
                "Exemplos de request/response para cada endpoint",
                "Acessivel em: /api/docs",
                "Schemas TypeScript -> OpenAPI schemas",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] T6 - Code splitting e lazy loading de rotas",
        "labels": ["p3"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("Code Splitting", 3),
            adf_paragraph("Lazy loading de rotas para reduzir bundle size (atualmente ~1MB)."),
            adf_rule(),
            adf_bullet_list([
                "React.lazy() para todas as rotas do dashboard",
                "Suspense com loading skeleton",
                "Separar chunks: auth, dashboard, settings, crypto",
                "Meta: bundle principal < 300KB",
            ]),
            adf_paragraph("Esforco estimado: 1 dia"),
        ],
    },

    # ---- KYC AVANCADO (Sprint 5) ----
    {
        "summary": "[NexusP2P] K1 - Validacao CPF via Receita Federal (Serpro)",
        "labels": ["p3"],
        "sprint": "sprint5",
        "desc_blocks": [
            adf_heading("Validacao CPF - Receita Federal", 3),
            adf_paragraph("Integrar API de consulta CPF (Serpro ou similar) para validar nome x CPF automaticamente."),
            adf_rule(),
            adf_bullet_list([
                "Validar se CPF esta ativo na Receita Federal",
                "Conferir nome do titular vs nome cadastrado",
                "Cache resultado por 24h no Redis",
                "Atualmente: validacao apenas algoritmica (digitos verificadores)",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] K2 - OCR de documentos KYC (RG/CNH)",
        "labels": ["p3"],
        "sprint": "sprint5",
        "desc_blocks": [
            adf_heading("OCR de Documentos", 3),
            adf_paragraph("Leitura automatica de RG/CNH via OCR para agilizar aprovacao KYC Level 2."),
            adf_rule(),
            adf_bullet_list([
                "Provider: Google Vision API ou Amazon Textract",
                "Extrair: nome, CPF, data de nascimento, numero do documento",
                "Comparar dados extraidos com formulario KYC",
                "Flag automatico se houver divergencia",
                "Resultado salvo em user_kyc_profiles",
            ]),
            adf_paragraph("Esforco estimado: 3-5 dias"),
        ],
    },

    # ---- PRODUCAO (Sprint 4-5) ----
    {
        "summary": "[NexusP2P] A1 - Testes automatizados (Jest + Vitest, cobertura 70%)",
        "labels": ["p1"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("Testes Automatizados", 3),
            adf_paragraph("Implementar suite de testes com cobertura minima de 70%."),
            adf_rule(),
            adf_heading("Backend (Jest)", 4),
            adf_bullet_list([
                "Testes unitarios: services (pricing, pix, p2p, auth)",
                "Testes de integracao: rotas API",
                "Mocks: Supabase, Redis, APIs externas",
            ]),
            adf_heading("Frontend (Vitest + Testing Library)", 4),
            adf_bullet_list([
                "Testes de componentes: TradePanel, KYC forms, Dashboard",
                "Testes de hooks: useWallet, useAuth, usePrice",
                "E2E: Playwright para fluxo completo (login -> compra -> historico)",
            ]),
            adf_paragraph("Esforco estimado: 5-8 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] A2 - CI/CD pipeline (GitHub Actions)",
        "labels": ["p1", "infra"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("CI/CD Pipeline", 3),
            adf_paragraph("GitHub Actions com lint, test, build e deploy automatico."),
            adf_rule(),
            adf_bullet_list([
                "Trigger: push para main e PRs",
                "Steps: lint (ESLint) -> test (Jest/Vitest) -> build -> deploy (Railway)",
                "Deploy automatico apenas se testes passarem",
                "Notificacao Telegram no resultado",
                "Separar pipelines: backend e frontend",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] A3 - Monitoramento APM (metricas de performance)",
        "labels": ["p2", "infra"],
        "sprint": "sprint5",
        "desc_blocks": [
            adf_heading("Monitoramento APM", 3),
            adf_paragraph("Metricas de performance: response times, error rates, throughput."),
            adf_rule(),
            adf_bullet_list([
                "Sentry Performance (ja tem Sentry para errors)",
                "Metricas: p50/p95/p99 response time por endpoint",
                "Alertas: error rate > 5%, response time > 2s",
                "Dashboard de metricas acessivel",
            ]),
            adf_paragraph("Esforco estimado: 1-2 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] A4 - Backup automatico Supabase (daily, 30 dias retencao)",
        "labels": ["p2", "infra"],
        "sprint": "sprint5",
        "desc_blocks": [
            adf_heading("Backup Automatico", 3),
            adf_paragraph("Rotina de backup diario do Supabase com retencao de 30 dias."),
            adf_rule(),
            adf_bullet_list([
                "Supabase Pro inclui backups automaticos",
                "Verificar plano atual e ativar se necessario",
                "Backup manual via pg_dump como fallback",
                "Testar restore em ambiente staging",
            ]),
            adf_paragraph("Esforco estimado: 1 dia"),
        ],
    },
    {
        "summary": "[NexusP2P] A5 - Rate limiter distribuido (Redis)",
        "labels": ["p2", "infra"],
        "sprint": "sprint1",
        "desc_blocks": [
            adf_heading("Rate Limiter Redis", 3),
            adf_paragraph("Migrar rate limiter de in-memory Map para Redis (distribuido)."),
            adf_rule(),
            adf_bullet_list([
                "Atualmente: Map em memoria (perde estado no restart)",
                "Migrar para Redis com sliding window",
                "Manter mesmos limites por endpoint",
                "Lib: rate-limiter-flexible com RedisStore",
                "Ja tem Redis configurado (ioredis)",
            ]),
            adf_paragraph("Esforco estimado: 1 dia"),
        ],
    },
    {
        "summary": "[NexusP2P] A6 - Compliance LGPD (exportar/excluir dados)",
        "labels": ["p2", "legal"],
        "sprint": "sprint4",
        "desc_blocks": [
            adf_heading("Compliance LGPD", 3),
            adf_paragraph("Funcionalidades para atender a Lei Geral de Protecao de Dados."),
            adf_rule(),
            adf_bullet_list([
                "Exportar dados pessoais do usuario (JSON/CSV)",
                "Excluir conta e dados pessoais (direito ao esquecimento)",
                "Anonimizar dados de transacoes (manter para auditoria)",
                "Registrar consentimento explicito para uso de dados",
                "Botao nas configuracoes: 'Exportar Meus Dados' e 'Excluir Minha Conta'",
            ]),
            adf_paragraph("Esforco estimado: 2-3 dias"),
        ],
    },
    {
        "summary": "[NexusP2P] A7 - Painel admin frontend (gestao web)",
        "labels": ["p2"],
        "sprint": "sprint5",
        "desc_blocks": [
            adf_heading("Painel Admin - Frontend", 3),
            adf_paragraph("Interface web para administracao. Atualmente admin e apenas via API."),
            adf_rule(),
            adf_heading("Paginas", 4),
            adf_bullet_list([
                "Dashboard: stats, transacoes em tempo real, volume",
                "Usuarios: lista, detalhes, alterar nivel KYC",
                "KYC: fila de aprovacao, aprovar/rejeitar com motivo",
                "Ordens: lista, detalhes, alterar status",
                "Configuracoes: pricing (buffer, comissao), ativos habilitados",
                "Logs: security events, audit trail",
            ]),
            adf_heading("Acesso", 4),
            adf_paragraph("Rota: /admin (requer role admin no Supabase)"),
            adf_paragraph("Esforco estimado: 5-8 dias"),
        ],
    },
]

created_keys = []
for task in new_tasks:
    desc = adf_doc(task["desc_blocks"])
    due = SPRINT_DATES[task["sprint"]]
    key = create_issue(
        summary=task["summary"],
        description_adf=desc,
        parent_key="KAN-15",
        labels=task["labels"],
        due_date=due,
    )
    if key:
        created_keys.append((key, task["summary"], task["sprint"]))
    time.sleep(0.5)  # rate limit

# ============================================================
# 4. RESUMO
# ============================================================
print("\n" + "=" * 60)
print("[4/4] RESUMO")
print("=" * 60)

print("\nTasks atualizadas como CONCLUIDAS:")
print("  KAN-61 - SOP + DoR/DoD + Checklists")
print("  KAN-62 - Backlog inicial (8/10 itens done)")
print("  KAN-63 - Riscos & Dependencias (mapeados)")

print(f"\nNovas tasks criadas: {len(created_keys)}")
for key, summary, sprint in created_keys:
    print(f"  {key} - {summary} (due: {SPRINT_DATES[sprint]})")

print("\nSprints planejadas:")
print("  Sprint 1 (Seguranca):    ate 2026-03-31  [S1-S4, A5]")
print("  Sprint 2 (Pagamentos):   ate 2026-04-30  [P1-P4]")
print("  Sprint 3 (Comunicacao):  ate 2026-05-15  [C1-C3]")
print("  Sprint 4 (Tecnico):      ate 2026-05-31  [T1-T6, A1-A2, A6]")
print("  Sprint 5 (Admin+Polish): ate 2026-06-30  [K1-K2, A3-A4, A7]")

if DRY_RUN:
    print("\n[!!] MODO DRY-RUN — nenhuma alteracao foi feita no Jira")
print("\nConcluido!")
