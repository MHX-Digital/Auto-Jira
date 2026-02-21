# Integração Jira Cloud — Documentação Operacional Completa

**Projeto:** KAN | **Instância:** https://mhxdigital.atlassian.net
**Data:** 2026-02-14

---

## A) AUDITORIA — O QUE FOI EXECUTADO VIA API

### A.1) Endpoints utilizados

| # | Método | Endpoint | Finalidade |
|---|--------|----------|-----------|
| 1 | GET | `/rest/api/3/myself` | Validar autenticação (retorna dados do usuário logado) |
| 2 | GET | `/rest/api/3/project` | Listar projetos acessíveis |
| 3 | GET | `/rest/api/3/project/KAN` | Detalhes do projeto KAN (issue types, componentes, roles) |
| 4 | GET | `/rest/api/3/project/KAN/statuses` | Listar status disponíveis por issue type |
| 5 | POST | `/rest/api/3/component` | Criar componente no projeto |
| 6 | POST | `/rest/api/3/issue` | Criar issue (Epic, Task, Story, Bug) |
| 7 | GET | `/rest/api/3/search/jql?jql=...` | Buscar issues via JQL |
| 8 | POST | `/rest/api/3/filter` | Criar filtro salvo (JQL persistido) |
| 9 | POST | `/rest/api/3/statuses` | Criar status em lote (project-scoped) |
| 10 | GET | `/rest/api/3/workflow/search` | Listar workflows do projeto |
| 11 | GET | `/rest/agile/1.0/board?projectKeyOrId=KAN` | Listar boards do projeto |
| 12 | GET | `/rest/agile/1.0/board/{boardId}/configuration` | Ver configuração de colunas do board |
| 13 | POST | `/rest/agile/1.0/board` | Criar board Kanban |

### A.2) Exemplos de payload e headers

**Headers (todas as chamadas):**
```
Accept: application/json
Content-Type: application/json
Authorization: Basic <base64(EMAIL:API_TOKEN)>
```

Usando curl, o `-u EMAIL:API_TOKEN` gera o header Authorization automaticamente.
Formato real:
```
-u "neomaike@gmail.com:<API_TOKEN>"
```
O curl converte isso internamente para:
```
Authorization: Basic bmVvbWFpa2VAZ21haWwuY29tOkFUQVRU...
```

**Payload — Criar Componente:**
```json
{
  "name": "GOV",
  "project": "KAN",
  "description": "Componente GOV",
  "leadAccountId": "70121:b8e9df32-fac4-4bad-9ef2-c2c3712ed776"
}
```

**Payload — Criar Epic:**
```json
{
  "fields": {
    "project": { "key": "KAN" },
    "summary": "LexNotify AI (V1 -> Beta -> Prod)",
    "issuetype": { "name": "Epic" },
    "components": [{ "name": "PRODUCT" }],
    "labels": ["p2"],
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            { "type": "text", "text": "Epic PRODUCT: LexNotify AI - do V1 ao Beta ate Producao." }
          ]
        }
      ]
    }
  }
}
```

**Payload — Criar Filtro:**
```json
{
  "name": "OPERATIONS - OTC/DELIVERY/GOV",
  "description": "Filtro para board OPERATIONS",
  "jql": "project = KAN AND component in (OTC, DELIVERY, GOV) ORDER BY priority DESC",
  "favourite": true
}
```

**Payload — Criar Board:**
```json
{
  "name": "OPERATIONS (OTC/DELIVERY/GOV)",
  "type": "kanban",
  "filterId": 10001,
  "location": {
    "type": "project",
    "projectKeyOrId": "KAN"
  }
}
```

**Payload — Criar Status em lote:**
```json
{
  "statuses": [
    { "name": "Intake", "statusCategory": "TODO", "description": "Entrada de demanda" },
    { "name": "Ready", "statusCategory": "TODO", "description": "Pronto para iniciar" },
    { "name": "Doing", "statusCategory": "IN_PROGRESS", "description": "Em execucao" },
    { "name": "Waiting", "statusCategory": "IN_PROGRESS", "description": "Aguardando dependencia" },
    { "name": "Done", "statusCategory": "DONE", "description": "Concluido" }
  ],
  "scope": {
    "type": "PROJECT",
    "project": { "id": "10000" }
  }
}
```

### A.3) Permissões necessárias no Jira

| Ação | Permissão Jira | Role mínimo |
|------|---------------|-------------|
| Ler projeto | Browse Projects | Viewer |
| Criar issue | Create Issues | Member |
| Atualizar issue | Edit Issues | Member |
| Transicionar issue | Transition Issues | Member |
| Criar componente | Administer Projects | Administrator |
| Ler board/backlog | Browse Projects | Viewer |
| Criar board | Administer Projects | Administrator |
| Criar status | Administer Projects | Administrator |
| Criar filtro | Qualquer usuário autenticado | Viewer |

**API Token scopes:** O API Token do Atlassian herda TODAS as permissões do usuário. Não tem scopes granulares como OAuth. Se o usuário é admin do projeto, o token pode fazer tudo que o admin faz.

---

## B) AUTENTICAÇÃO PARA CHATGPT ACTIONS

### B.1) Método recomendado: Basic Auth (email + API Token)

| Método | Compatível com ChatGPT Actions? | Complexidade | Recomendação |
|--------|--------------------------------|-------------|-------------|
| Basic Auth (email:token) | SIM (via API Key) | Baixa | RECOMENDADO |
| Bearer Token | NÃO (Jira Cloud não aceita API Token como Bearer) | N/A | NÃO USAR |
| OAuth 2.0 (3LO) | SIM (mas complexo) | Alta | Só se precisar de multi-tenant |

**Por que Basic Auth?**
O Jira Cloud aceita `Authorization: Basic base64(email:api_token)` em todas as chamadas REST. O ChatGPT Actions suporta "API Key" que permite injetar um header customizado.

### B.2) Configuração exata no ChatGPT Actions

**Passo 1 — Gerar o valor Base64:**

No terminal (bash/PowerShell):
```bash
echo -n "neomaike@gmail.com:SEU_API_TOKEN_AQUI" | base64
```
Resultado (exemplo): `bmVvbWFpa2VAZ21haWwuY29tOkFUQVRU...`

**Passo 2 — No ChatGPT, criar uma Action:**

1. Vá em **GPTs** > **Configure** > **Actions** > **Create new action**
2. Cole o schema OpenAPI (seção C abaixo)
3. Em **Authentication**, configure:

| Campo | Valor |
|-------|-------|
| Authentication Type | **API Key** |
| API Key | `Basic bmVvbWFpa2VAZ21haWwuY29tOkFU...` (o valor base64 completo, COM o prefixo "Basic ") |
| Auth Type | **Custom** |
| Custom Header Name | `Authorization` |

**IMPORTANTE:** O valor do API Key deve ser EXATAMENTE:
```
Basic <base64_do_email:token>
```
Com o prefixo "Basic " (com espaço) incluído.

**Passo 3 — Testar:**

Após salvar, peça ao ChatGPT: "Chame o endpoint /myself para validar"

### B.3) Checklist de testes (em ordem)

```
[ ] 1. GET /rest/api/3/myself
     Esperado: 200 + JSON com displayName, emailAddress
     Valida: autenticação funciona

[ ] 2. GET /rest/api/3/project/search
     Esperado: 200 + lista de projetos
     Valida: permissão de leitura

[ ] 3. GET /rest/api/3/search/jql?jql=project=KAN&maxResults=5
     Esperado: 200 + issues do projeto KAN
     Valida: JQL funciona + acesso ao projeto

[ ] 4. GET /rest/api/3/project/KAN
     Esperado: 200 + detalhes com issueTypes
     Valida: acesso ao projeto específico

[ ] 5. POST /rest/api/3/issue (criar uma Task de teste)
     Esperado: 201 + key (ex: KAN-28)
     Valida: permissão de escrita

[ ] 6. GET /rest/api/3/issue/KAN-28
     Esperado: 200 + detalhes da issue criada
     Valida: leitura de issue específica

[ ] 7. DELETE a issue de teste ou mova para Done
```

### B.4) Erros comuns e correções

| Erro | Causa | Correção |
|------|-------|----------|
| `401 "Client must be authenticated"` | Header Authorization ausente ou malformado | Verificar se o base64 inclui email:token (não só o token). Verificar se tem o prefixo "Basic " |
| `401 "Client must be authenticated"` | Token expirado ou revogado | Gerar novo token em id.atlassian.com/manage-profile/security/api-tokens |
| `401` com token OAuth (ATCTT3x...) | Tokens OAuth não funcionam como API Token | Usar API Token (começa com ATATT3x...), não OAuth token |
| `403 "Forbidden"` | Usuário não tem permissão na ação | Verificar role do usuário no projeto (precisa ser Member ou Admin) |
| `400 "Field X is required"` | Payload incompleto | Verificar campos obrigatórios: project, summary, issuetype |
| `400 "Issue type not found"` | Nome do issuetype diferente do cadastrado | Chamar GET /project/KAN para ver nomes exatos (ex: "Tarefa" vs "Task") |
| `404 "Issue does not exist"` | Key errada ou sem permissão | Verificar se a key existe e se o usuário tem Browse Projects |
| `400 "description: invalid"` | Description em texto simples | Jira v3 exige Atlassian Document Format (ADF) para description |

**Dica sobre Description (ADF):**
A API v3 do Jira NÃO aceita texto simples no campo `description`. Precisa ser Atlassian Document Format:
```json
{
  "type": "doc",
  "version": 1,
  "content": [
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "Seu texto aqui" }
      ]
    }
  ]
}
```

---

## C) SCHEMA OPENAPI 3.1.1 PARA CHATGPT ACTIONS

O schema está no arquivo separado: `JIRA_OPENAPI_SCHEMA.yaml`

---

## D) CONTRATO OPERACIONAL: ChatGPT + Claude CLI

### D.1) Fluxo de trabalho proposto

```
CHATGPT (Planejador)                    CLAUDE CLI (Executor)
─────────────────────                   ─────────────────────
1. Analisa requisitos
2. Define DoR/DoD/WIP
3. Gera MANIFESTO (YAML)         -->   4. Recebe manifesto
                                        5. Valida estrutura
                                        6. Executa via API Jira
                                        7. Gera RELATÓRIO (IDs/keys)
8. Recebe relatório              <--
9. Valida no board
10. Ajusta se necessário         -->   11. Executa ajustes
```

### D.2) Formato do Manifesto

```yaml
# manifesto-jira.yaml
version: "1.0"
metadata:
  project_key: "KAN"
  base_url: "https://mhxdigital.atlassian.net"
  generated_by: "ChatGPT"
  generated_at: "2026-02-14T12:00:00Z"
  description: "Manifesto de criação de itens no Jira"

components:
  - name: "NOME_COMPONENTE"
    description: "Descrição do componente"

epics:
  - summary: "Título do Epic"
    component: "NOME_COMPONENTE"
    labels: ["p1"]
    description: "Descrição em texto (Claude converte para ADF)"
    tasks:
      - summary: "Título da Task"
        type: "Task"          # Task | Story | Bug | Subtask
        labels: ["p2"]
        description: "Descrição da task"
        assignee: null         # accountId ou null
      - summary: "Outra Task"
        type: "Story"
        labels: ["p2", "security"]
        description: "Descrição da story"
        acceptance_criteria:
          - "Critério 1"
          - "Critério 2"
          - "Critério 3"

transitions:
  - issue_key: "KAN-XX"
    to_status: "Ready"

updates:
  - issue_key: "KAN-XX"
    fields:
      labels:
        add: ["p1", "blocked"]
        remove: ["p2"]
      priority: "Highest"
```

**Regras do manifesto:**
1. `component` deve existir previamente (ou estar na seção `components`)
2. `type` deve ser um issue type válido do projeto
3. `labels` são criadas automaticamente se não existirem
4. `description` é texto simples — o Claude CLI converte para ADF ao enviar
5. `tasks` são filhas do epic — criadas com `epic link` apontando para o epic pai
6. `transitions` referem issues já existentes que devem mudar de status
7. `updates` referem issues já existentes que devem ser atualizadas

### D.3) Exemplo de manifesto para KAN

```yaml
version: "1.0"
metadata:
  project_key: "KAN"
  base_url: "https://mhxdigital.atlassian.net"
  generated_by: "ChatGPT"
  generated_at: "2026-02-14T15:00:00Z"
  description: "Sprint 1 - Setup inicial de 3 epics com tasks"

epics:
  - summary: "LexNotify - Configurar infra de notificacoes"
    component: "PRODUCT"
    labels: ["p1"]
    description: "Configurar toda a infraestrutura de notificacoes push, email e webhook para o LexNotify AI."
    tasks:
      - summary: "Definir stack de mensageria (SQS vs RabbitMQ vs Redis Streams)"
        type: "Task"
        labels: ["p1", "infra"]
        description: "Spike de 2 dias para definir qual sistema de fila usar. Critérios: custo, latencia, persistencia."
        acceptance_criteria:
          - "Documento comparativo com pelo menos 3 opcoes"
          - "Recomendacao final com justificativa"
          - "Estimativa de custo mensal"
      - summary: "Implementar servico de dispatch de notificacoes"
        type: "Story"
        labels: ["p2"]
        description: "Criar microservico que recebe evento da fila e despacha para o canal correto (email/push/webhook)."
        acceptance_criteria:
          - "Servico deployado em staging"
          - "Teste de integracao com pelo menos 1 canal"
          - "Retry automatico em caso de falha"
          - "Logs estruturados"

  - summary: "OTC - Fluxo de intermediacao completo"
    component: "OTC"
    labels: ["p1"]
    description: "Implementar o fluxo completo de intermediacao OTC: recebimento, KYT, execucao, liquidacao."
    tasks:
      - summary: "Mapear fluxo de KYT com Foxbit"
        type: "Task"
        labels: ["p1", "legal"]
        description: "Documentar o fluxo de verificacao KYT exigido pela Foxbit para operacoes OTC."
        acceptance_criteria:
          - "Diagrama de fluxo do processo KYT"
          - "Lista de documentos necessarios"
          - "Contato do responsavel na Foxbit"
      - summary: "Template de contrato de intermediacao"
        type: "Task"
        labels: ["p2", "legal"]
        description: "Criar template de contrato para operacoes de intermediacao de criptoativos."
        acceptance_criteria:
          - "Template revisado por assessoria juridica"
          - "Clausulas de risco e responsabilidade definidas"
          - "Modelo disponivel em PDF e DOCX"

  - summary: "GOV - Regularizacao contabil Q1 2026"
    component: "GOV"
    labels: ["p1"]
    description: "Regularizar toda a parte contabil das PJs para o primeiro trimestre de 2026."
    tasks:
      - summary: "Levantar pendencias contabeis PJ 24.409"
        type: "Task"
        labels: ["p1"]
        description: "Listar todas as pendencias contabeis e fiscais da PJ 24.409 junto ao contador."
        acceptance_criteria:
          - "Lista completa de pendencias"
          - "Prazo de cada obrigacao"
          - "Custo estimado de regularizacao"
      - summary: "Enviar declaracoes fiscais atrasadas"
        type: "Task"
        labels: ["p1", "legal"]
        description: "Enviar todas as declaracoes fiscais em atraso identificadas no levantamento."
        acceptance_criteria:
          - "Todas as declaracoes enviadas"
          - "Comprovantes de envio anexados"
          - "Nenhuma pendencia restante na RFB"
```

### D.4) Formato do relatório de execução (Claude CLI → ChatGPT)

Após executar o manifesto, o Claude CLI devolve:

```yaml
execution_report:
  manifesto_version: "1.0"
  executed_at: "2026-02-14T15:05:00Z"
  status: "completed"  # completed | partial | failed

  components_created: []  # nenhum novo neste manifesto

  epics_created:
    - key: "KAN-28"
      summary: "LexNotify - Configurar infra de notificacoes"
      component: "PRODUCT"
      status: "created"
      tasks:
        - key: "KAN-29"
          summary: "Definir stack de mensageria"
          status: "created"
          epic_link: "KAN-28"
        - key: "KAN-30"
          summary: "Implementar servico de dispatch"
          status: "created"
          epic_link: "KAN-28"

    - key: "KAN-31"
      summary: "OTC - Fluxo de intermediacao completo"
      component: "OTC"
      status: "created"
      tasks:
        - key: "KAN-32"
          summary: "Mapear fluxo de KYT com Foxbit"
          status: "created"
          epic_link: "KAN-31"
        - key: "KAN-33"
          summary: "Template de contrato de intermediacao"
          status: "created"
          epic_link: "KAN-31"

    - key: "KAN-34"
      summary: "GOV - Regularizacao contabil Q1 2026"
      component: "GOV"
      status: "created"
      tasks:
        - key: "KAN-35"
          summary: "Levantar pendencias contabeis PJ 24.409"
          status: "created"
          epic_link: "KAN-34"
        - key: "KAN-36"
          summary: "Enviar declaracoes fiscais atrasadas"
          status: "created"
          epic_link: "KAN-34"

  transitions_executed: []
  updates_executed: []

  errors: []

  summary:
    epics: 3
    tasks: 6
    total_created: 9
    total_errors: 0
```
