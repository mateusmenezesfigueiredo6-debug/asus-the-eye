# THE EYE — dossiê consolidado das conversas

Selado em 2026-08-23. Este é o índice canônico dos chats do projeto e o
"estado da união" do que cada um resolveu. Substitui a leitura das
sessões antigas: a memória `projeto-asus-the-eye.md` mais este arquivo
carregam o contexto vivo.

## Índice de sessões

Ordem cronológica reversa. Copie o `session_id` e chame
`ccd_session_mgmt.get_session` (ou reabra pelo cliente) para retomar.

| # | Sessão | session_id | Última atividade | O que ficou |
|---|---|---|---|---|
| 1 | **[THE EYE] Conversa com algoritmos preditivos** *(canônica)* | `local_3e35f1da-76b3-4497-9060-23ae2c399deb` | 2026-08-23 | FASE B fechada — PR #112, tema portado, vitrine paritária, 975 testes, próxima fase C (IGP-M, INPC, IPCA-15, IBC-Br, dispersão) |
| 2 | [THE EYE] Conversa com algoritmos preditivos (fork) | `local_5fc8a360-1362-449f-80b4-7679d2c51332` | 2026-08-21 | PR #100 — refactor do site como sistema único (verdigris/latão, hash-ornamento, serifa/grotesca), 886 testes, 2 PDFs por produto |
| 3 | [Infra] Cloudflare MCP repository | `local_1418eefd-a0d1-4d3a-9475-ede9bd02867d` | 2026-08-19 | Worker `the-eye-public-verifier` e `the-eye-audit-staging` em pé (D1 staging), token em `~/.the-eye/staging-token`; wrangler local |
| 4 | [Dev] Corrigir 3 erros de tipo pré-existentes (mypy) | `local_e3b3d09d-95ab-4530-8de7-8b75ec334b4c` | 2026-08-17 | mypy passa em `src/` inteiro (override em pyproject removido) — CI verde |
| 5 | [THE EYE] Algoritmos preditivos e tendências *(original)* | `local_23187da3-b8b2-4a34-a39e-11413cdd9d3a` | 2026-08-17 | Sessão original — travou com "Prompt is too long" por paste de 2,7M chars do site da Kalshi. NÃO REABRIR; virou o repo. |
| 6 | [Dev] Script Python (`from __future__` / contextlib) | `local_67d7d81a-2569-4302-b1f1-e81c7e85b433` | 2026-08-14 | Correções ao `scripts/publish_guard.py` (o path velho `/home/sexexes/asus_the_eye/` foi movido para `~/pegasus/asus_the_eye/`) |
| 7 | [Infra] Integrar ChatGPT e Claude | `local_9e83a4c3-be3a-46ab-a376-2a1e530f3451` | 2026-08-08 | Fábrica 3-IAs mapeada: Claude (Code), Copilot coding agent (bot habilitado, PRs #19/#20/#21), Codex (bloqueado — sem crédito, login pendente) |
| 8 | [Avulsos] WhatsApp RDC | `local_5c8e08ed-e200-473b-8443-489c5c2d7011` | 2026-08-05 | Subiu `uvicorn apps.comercial.api:create_app` do EYE em ambiente local — só teste, sem impacto |

## Linha do tempo dos marcos

- **17/08** — Etapa 4 fechada (PR #4, `ff7d5c7`): módulo `markets/`, DuckDB, CLI, painel; tie-out 41 liquidados, voto 0.003293, macro 0.111089.
- **17/08 fim** — Roteiro em 95%. F3 a 70% até o faucet.
- **19/08** — Dia da virada: PRs #15/#22/#23/#24 mergeados. MLops selado, checklist vivo `produtos.json`, ledger espelhado no D1 (10/10 idempotente), sinais IPCA (Focus/Olinda). Carteira trocada: `0xeDd93384dB68D849d5dCEf49FfACE3A1c12bcC76`.
- **19/08 noite** — Roteiro 71,7%, fábrica 3-IAs completa. Kalshi comparador ao vivo. JUROS-01/CAMBIO-01 abertos com cron. Nowcast desafiante: R2 Brier 0,0575 / R4 0,0611 em 18 meses.
- **20/08** — Custódia fechada: backup GPG AES-256/SHA-512 (`the-eye-chaves-2026-08-20.tar.gz.gpg`, sha256 `1d5535b2b92dba5ce426a81469e170076703b154dcd00923f3a7820c3103e835`) no Google Drive + QR no iPhone físico. Titularidade selada (`project.authorship` fa8811df… em lote Merkle 5f7a9295…, tx 80e2f41d…, bloco 45716613, Base Sepolia).
- **21/08** — Fork: refactor do site como sistema único. PR #100. Verdigris no selado, latão no mutável, serifa AFIRMA / grotesca MEDE, hash como ornamento. 886 testes, 349/349 arquivos no nome dele.
- **23/08 madrugada** — FASE B fechada: PR #112. Tema portado às 10 páginas, SVG de calibração com variáveis do tema, vitrine paritária Markets+Ledger (2 testes semânticos travam regressão). 975 testes, titularidade 363/363. "Palantir" só em comentários; produtos chamados pelos nomes próprios.
- **23/08** — 50 sessões rotuladas com prefixos `[Projeto]`. Grupo `[THE EYE]` = 4 conversas; grupo `[Mercados]` (2) provavelmente entra em `[THE EYE]`.

## Doutrina inegociável (AGENTS.md)

- Kalshi é comparador, NUNCA fonte de resolução.
- Brier é `null` até liquidar (nunca 0).
- Janela sempre declarada; se o baseline vence, publica (regra 4).
- UNKNOWN over guess.
- Medição do projeto sempre em hash (`asus-theye projeto-medir` — sela snapshot determinístico, sem relógio; a corrente medida exclui `project.measurement`).
- `dependencies=[]` sagrado — R, Orange, HashDork, Anaconda, scikit ficam FORA. Se publicar métrica, anexo em R para o revisor acadêmico.

## Sistema de design (PR #100)

O site é um **instrumento de registro**, não um dashboard. Papel de arquivo, não preto de terminal.

- **Verdigris** (verde do bronze oxidado) — pátina do que foi selado, só no selado.
- **Latão** — no que ainda pode mudar.
- **Serifa** — para o que a plataforma **AFIRMA** sobre o mundo.
- **Grotesca** — para o que ela **MEDE**. Inverso do costume, de propósito.
- **Hash como ornamento** — todo objeto selado mostra o próprio hash correndo como fio fino na borda. A prova é a decoração; nenhum concorrente pode copiar porque nenhum tem a prova.
- **Claim selado como herói** na landing (não "número grande com rótulo pequeno").

## Estado dos apps

- **Public verifier** — `https://the-eye-public-verifier.mateusmenezesfigueiredo6.workers.dev` — no ar, D1 staging.
- **Dashboard** — `asus-theye serve --expose` exige `THE_EYE_DASHBOARD_TOKEN` (fail-closed, PR #9).
- **Deploy** — Dockerfile + compose + systemd + runbook em `deploy/`.
- **Painéis** — `/markets`, `/evidencia`, `/projeto` (checklist vivo por `produtos.json`).
- **Lovable** — 3 apps: Mercados, Evidência, Controle da Missão.
- **Export estático** — `dist/` 5 páginas, publicação = passphrase.

## Pendências vivas do dono

1. **Faucet** para "pode ancorar" na carteira `0xeDd93384dB68D849d5dCEf49FfACE3A1c12bcC76` (Base Sepolia).
2. **Passphrase** de `scripts/publish_lock.py`.
3. **Resgate** de 0,00232 ETH (mainnet) da carteira antiga `0x4F55…2E3b` — importar via MetaMask com a chave em `anchor.key.QUEIMADA`.
4. **2FA** no GitHub e no Cloudflare (elo mais fraco hoje).
5. **Crédito Codex** (opcional; Copilot já cobre a linha 3-IAs).
6. **Unificar** `[Mercados]` em `[THE EYE]` (rotulagem de sessões — pedir OK).

## Como retomar

- Sessão canônica: `local_3e35f1da-76b3-4497-9060-23ae2c399deb`. Reabra por ela sempre que possível.
- Banco medido: `export ASUS_MARKETS_DB=/home/sexexes/Área\ de\ trabalho/organizado/Backups/Recuperacao-Disco/2026-08/Backups-Proton/PROJETO_asus_COMPLETO_2026-08-08/asus/asus_teste.duckdb`.
- `.venv` do repo tem shebangs velhos (`/home/sexexes/asus_the_eye/...`): usar `.venv/bin/python -m pip` + `PYTHONPATH=src`, ou refazer `make setup`.
- Roteiro vivo: `reports/projeto/produtos.json` (o painel `/projeto` é o checklist canônico).

## O que este dossiê não tenta ser

- Não substitui `git log` para "quem mudou o quê".
- Não substitui `AGENTS.md` para a doutrina.
- Não substitui `produtos.json` para o roteiro.
- Não substitui os PRs para o histórico de código.

É a costura entre as conversas, para quando o Claude entra numa sessão nova e precisa saber o que já foi dito nas outras.
