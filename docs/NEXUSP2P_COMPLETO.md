# NexusP2P — Documentacao Completa do Jira

> Extraido em: 2026-02-21
> Projeto: KAN (MHX Digital)
> Epic: KAN-15
> Total de issues: 1 Epic + 29 Tarefas

---

## Visao Geral

| Campo         | Valor                                      |
|---------------|--------------------------------------------|
| **Epic**      | KAN-15 — NexusP2P (conclusao V1)           |
| **Status**    | Em andamento                               |
| **Prioridade**| Medium                                     |
| **Labels**    | `p2`                                       |
| **Component** | PRODUCT                                    |
| **Deploy**    | https://www.nexusp2p.finance               |
| **Backend**   | Railway (Express + TypeScript + Supabase)   |
| **Progresso** | Beta ~85% concluido                        |

### Stack

- Frontend: React 18 + Vite + Tailwind CSS + Framer Motion
- Backend: Express.js + TypeScript 5
- Banco: Supabase (PostgreSQL) com RLS
- Cache: Redis (ioredis) + BullMQ
- Auth: Supabase Auth (JWT)
- Monitoramento: Sentry + Winston + Telegram Bot
- Deploy: Railway

---

## Estrutura de Issues

```
KAN-15 [Epic] NexusP2P (conclusao V1)                          -- Em andamento
  |
  | --- CONCLUIDAS (Beta) ---
  +-- KAN-61 [Tarefa] SOP + DoR/DoD + Checklists               -- Concluido
  +-- KAN-62 [Tarefa] Backlog inicial (8/10 itens done)         -- Concluido
  +-- KAN-63 [Tarefa] Riscos & Dependencias (mapeados)          -- Concluido
  |
  | --- SPRINT 1: SEGURANCA (ate 2026-03-31) ---
  +-- KAN-170 [Tarefa] S1 - 2FA (TOTP)                         -- A fazer
  +-- KAN-171 [Tarefa] S2 - Sessoes ativas                     -- A fazer
  +-- KAN-172 [Tarefa] S3 - Historico de logins                 -- A fazer
  +-- KAN-173 [Tarefa] S4 - reCAPTCHA v3                       -- A fazer
  +-- KAN-193 [Tarefa] A5 - Rate limiter Redis                  -- A fazer
  |
  | --- SPRINT 2: PAGAMENTOS (ate 2026-04-30) ---
  +-- KAN-174 [Tarefa] P1 - PIX Dinamico (BB API)              -- A fazer
  +-- KAN-175 [Tarefa] P2 - Webhook confirmacao PIX             -- A fazer
  +-- KAN-176 [Tarefa] P3 - PIX automatico vendas (payout)      -- A fazer
  +-- KAN-177 [Tarefa] P4 - WebSocket tracking ordens           -- A fazer
  |
  | --- SPRINT 3: COMUNICACAO (ate 2026-05-15) ---
  +-- KAN-178 [Tarefa] C1 - Email transacional                  -- A fazer
  +-- KAN-179 [Tarefa] C2 - SMS verificacao telefone            -- A fazer
  +-- KAN-180 [Tarefa] C3 - Pagina historico notificacoes       -- A fazer
  |
  | --- SPRINT 4: TECNICO + QUALIDADE (ate 2026-05-31) ---
  +-- KAN-181 [Tarefa] T1 - Migrar para Zustand                 -- A fazer
  +-- KAN-182 [Tarefa] T2 - TanStack Query                      -- A fazer
  +-- KAN-183 [Tarefa] T3 - React Hook Form + Zod               -- A fazer
  +-- KAN-184 [Tarefa] T4 - Socket.io-client frontend           -- A fazer
  +-- KAN-185 [Tarefa] T5 - Swagger/OpenAPI docs                -- A fazer
  +-- KAN-186 [Tarefa] T6 - Code splitting                      -- A fazer
  +-- KAN-189 [Tarefa] A1 - Testes automatizados                -- A fazer
  +-- KAN-190 [Tarefa] A2 - CI/CD pipeline                      -- A fazer
  +-- KAN-194 [Tarefa] A6 - Compliance LGPD                     -- A fazer
  |
  | --- SPRINT 5: ADMIN + POLISH (ate 2026-06-30) ---
  +-- KAN-187 [Tarefa] K1 - Validacao CPF Receita Federal       -- A fazer
  +-- KAN-188 [Tarefa] K2 - OCR documentos KYC                  -- A fazer
  +-- KAN-191 [Tarefa] A3 - Monitoramento APM                   -- A fazer
  +-- KAN-192 [Tarefa] A4 - Backup automatico Supabase          -- A fazer
  +-- KAN-195 [Tarefa] A7 - Painel admin frontend               -- A fazer
```

---

## Resumo por Sprint

### Sprint 1 — Seguranca (Marco 2026)

| Issue   | Titulo                        | Labels          | Due        | Esforco    |
|---------|-------------------------------|-----------------|------------|------------|
| KAN-170 | S1 - 2FA (TOTP)              | p1, security    | 2026-03-31 | 3-5 dias   |
| KAN-171 | S2 - Sessoes ativas          | p1, security    | 2026-03-31 | 2-3 dias   |
| KAN-172 | S3 - Historico de logins     | p2, security    | 2026-03-31 | 1-2 dias   |
| KAN-173 | S4 - reCAPTCHA v3            | p2, security    | 2026-03-31 | 1 dia      |
| KAN-193 | A5 - Rate limiter Redis      | p2, infra       | 2026-03-31 | 1 dia      |

**Total: 8-12 dias**

---

### Sprint 2 — Pagamentos (Abril 2026)

| Issue   | Titulo                        | Labels          | Due        | Esforco    |
|---------|-------------------------------|-----------------|------------|------------|
| KAN-174 | P1 - PIX Dinamico BB API     | p1, infra       | 2026-04-30 | 5-8 dias   |
| KAN-175 | P2 - Webhook confirmacao PIX | p1, infra       | 2026-04-30 | 3-5 dias   |
| KAN-176 | P3 - PIX automatico vendas   | p1, infra       | 2026-04-30 | 3-5 dias   |
| KAN-177 | P4 - WebSocket tracking      | p2, infra       | 2026-04-30 | 2-3 dias   |

**Total: 13-21 dias**

---

### Sprint 3 — Comunicacao (Maio 2026)

| Issue   | Titulo                        | Labels          | Due        | Esforco    |
|---------|-------------------------------|-----------------|------------|------------|
| KAN-178 | C1 - Email transacional      | p2              | 2026-05-15 | 3-5 dias   |
| KAN-179 | C2 - SMS verificacao         | p2              | 2026-05-15 | 2-3 dias   |
| KAN-180 | C3 - Pagina notificacoes     | p3              | 2026-05-15 | 2 dias     |

**Total: 7-10 dias**

---

### Sprint 4 — Tecnico + Qualidade (Maio 2026)

| Issue   | Titulo                        | Labels          | Due        | Esforco    |
|---------|-------------------------------|-----------------|------------|------------|
| KAN-181 | T1 - Zustand                 | p2              | 2026-05-31 | 2-3 dias   |
| KAN-182 | T2 - TanStack Query          | p2              | 2026-05-31 | 3-5 dias   |
| KAN-183 | T3 - React Hook Form + Zod   | p3              | 2026-05-31 | 2-3 dias   |
| KAN-184 | T4 - Socket.io-client        | p2              | 2026-05-31 | 1-2 dias   |
| KAN-185 | T5 - Swagger/OpenAPI         | p3              | 2026-05-31 | 2-3 dias   |
| KAN-186 | T6 - Code splitting          | p3              | 2026-05-31 | 1 dia      |
| KAN-189 | A1 - Testes automatizados    | p1              | 2026-05-31 | 5-8 dias   |
| KAN-190 | A2 - CI/CD pipeline          | p1, infra       | 2026-05-31 | 2-3 dias   |
| KAN-194 | A6 - Compliance LGPD         | p2, legal       | 2026-05-31 | 2-3 dias   |

**Total: 20-31 dias**

---

### Sprint 5 — Admin + Polish (Junho 2026)

| Issue   | Titulo                        | Labels          | Due        | Esforco    |
|---------|-------------------------------|-----------------|------------|------------|
| KAN-187 | K1 - Validacao CPF Serpro    | p3              | 2026-06-30 | 2-3 dias   |
| KAN-188 | K2 - OCR documentos KYC     | p3              | 2026-06-30 | 3-5 dias   |
| KAN-191 | A3 - Monitoramento APM      | p2, infra       | 2026-06-30 | 1-2 dias   |
| KAN-192 | A4 - Backup Supabase        | p2, infra       | 2026-06-30 | 1 dia      |
| KAN-195 | A7 - Painel admin frontend  | p2              | 2026-06-30 | 5-8 dias   |

**Total: 12-19 dias**

---

## Resumo Quantitativo

| Categoria    | Itens | Esforco Estimado | Deadline   |
|--------------|-------|------------------|------------|
| Concluidas   | 3     | -                | -          |
| Seguranca    | 5     | 8-12 dias        | 2026-03-31 |
| Pagamentos   | 4     | 13-21 dias       | 2026-04-30 |
| Comunicacao  | 3     | 7-10 dias        | 2026-05-15 |
| Tecnico      | 9     | 20-31 dias       | 2026-05-31 |
| Admin+Polish | 5     | 12-19 dias       | 2026-06-30 |
| **TOTAL**    | **29**| **60-93 dias**   | **Junho 2026** |

**Progresso: 3/29 tarefas concluidas (10%)**

---

## Dependencias Externas

| Dependencia              | Status      | Bloqueia        |
|--------------------------|-------------|-----------------|
| BB API (PIX dinamico)    | Pendente    | KAN-174, 175, 176 |
| Resend/SendGrid (email)  | Pendente    | KAN-178         |
| Twilio/SNS (SMS)         | Pendente    | KAN-179         |
| Google reCAPTCHA v3      | Pendente    | KAN-173         |
| Serpro (CPF validation)  | Pendente    | KAN-187         |
| Supabase Cloud           | Configurado | -               |
| Railway (hosting)        | Configurado | -               |
| Telegram Bot             | Configurado | -               |

---

## Fases do SOW Original — Status

| Fase | Descricao                    | Status     |
|------|------------------------------|------------|
| 1    | Setup e Infra               | CONCLUIDA  |
| 2    | Autenticacao e Landing Page  | CONCLUIDA  |
| 3    | Dashboard Base               | CONCLUIDA  |
| 4    | Sistema de Negociacao        | CONCLUIDA  |
| 5    | KYC (3 niveis)              | CONCLUIDA  |
| 6    | Configuracoes e Seguranca   | PARCIAL (falta 2FA, sessoes) |
| 7    | Notificacoes                | PARCIAL (falta email, SMS)   |
| 8    | Polimento e Otimizacao      | PENDENTE   |
| 9    | Testes e Homologacao        | PENDENTE   |
| 10   | Deploy e Lancamento         | CONCLUIDA (Railway) |
