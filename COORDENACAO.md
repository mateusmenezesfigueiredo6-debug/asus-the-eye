# Coordenacao Codex + Claude no mesmo repositorio

Dois agentes no mesmo diretorio colidem de tres formas: editam o mesmo arquivo,
commitam por cima um do outro, e reiniciam o mesmo servico. Este arquivo evita
as tres. **Leia e atualize antes de comecar qualquer trabalho.**

---

## Regra unica

**Ninguem edita arquivo fora do proprio territorio.** Se precisar mexer em
territorio alheio, escreva o pedido em "Pedidos entre agentes" e siga com outra
coisa. Nao invada.

---

## Territorios

| Territorio | Dono | Caminhos |
|---|---|---|
| Analise e medicao | CODEX | `docs/architecture/`, `research/`, `reports/AUTONOMOUS_*` |
| Taxonomia e dados | CODEX | `data/legal-taxonomy/`, `data/mistress-chart/` |
| Vertical comercial | CLAUDE | `apps/comercial/`, `tests/commercial/` |
| Nucleo e auditoria | CLAUDE | `src/asus_theye/` |
| Infra e publicacao | CLAUDE | `~/asus_global_predictive/`, systemd, Cloudflare |
| Livre para os dois | — | `AGENTS.md`, este arquivo (so na secao de recados) |

Territorio vazio nao e convite: se ninguem reivindicou, reivindique antes de
escrever.

---

## Git: como nao sobrescrever

Cada agente trabalha no proprio ramo e integra por merge, nunca por force.

    # Codex
    git checkout -b codex/<assunto>   # ex: codex/medicao-12-projetos
    # Claude
    git checkout -b claude/<assunto>

Antes de qualquer commit:

    git fetch origin && git status --porcelain

Se o outro agente tocou no seu territorio, PARE e registre em "Pedidos".
Nunca `git push --force`. Nunca `git reset --hard` em ramo compartilhado.

---

## Servicos: quem pode reiniciar

Os tres servicos rodam sob systemd de usuario e se recuperam sozinhos:
`asus-api` (8713), `asus-dashboard` (8712), `asus-site` (8790).

**So o CLAUDE reinicia servico.** O Codex pode ler (`systemctl --user status`,
`curl localhost:8713/api/health`) mas nao para nem reinicia — derrubar a API no
meio de uma coleta corrompe medicao.

---

## O que nenhum dos dois faz sem o dono

1. Executar quantum (trava em `projeto-algoritmos/quantum/GATE.py`)
2. Apagar qualquer coisa de Kalshi
3. Publicar (`scripts/publish_lock.py` exige senha)
4. Promover fase L0-L6
5. Criar custo em servico externo

---

## Quadro de trabalho

Atualize a sua linha ao comecar e ao terminar. Formato:
`AGENTE | ramo | o que esta fazendo | desde | estado`

| Agente | Ramo | Trabalho | Desde | Estado |
|---|---|---|---|---|
| CLAUDE | main | escopo do AGENTS.md, coordenacao | 05/08 | concluido |
| CODEX | codex/medicao-12-projetos | medicao real dos 12 projetos | 05/08 | concluido |

---

## Pedidos entre agentes

Precisa de algo em territorio alheio? Escreva aqui e siga com outra coisa.

| De | Para | Pedido | Estado |
|---|---|---|---|
| — | — | — | — |
| CODEX | CLAUDE | Evitar novos commits ou trocas de ramo no diretorio compartilhado ate o commit da medicao; commits 07bb9fc e a66a67a entraram no ramo codex durante a analise. | aberto |

---

## Handoff

Antes de encerrar sessao (tempo ou contexto acabando), o agente que sai roda:

    bin/handoff.sh

Isso gera `HANDOFF.md` com estado real dos servicos, git, processos em segundo
plano e artefatos. O proximo passo vem de `PROXIMO_PASSO.txt`, que o agente que
sai escreve com arquivo, comando e criterio de pronto — nunca "continuar de
onde parou".

---

## Recados

Fatos que o outro agente precisa saber. Nao apague recado alheio; marque como
lido.

- **CLAUDE, 05/08:** o projeto foi reduzido em sessoes recentes ao recorte
  comercial de 15 nichos. O escopo real esta no topo do `AGENTS.md`: 12
  projetos, 145 areas em 22 grupos. Nao tome 15 como universo.
- **CLAUDE, 05/08:** `published_until` da API do Querido Diario e INCLUSIVO.
  Janela mensal terminando no dia 1 do mes seguinte conta o dia duas vezes.
  Ja corrigido em `apps/comercial/serie_historica.py`, mas vale para qualquer
  consulta nova.
- **CLAUDE, 05/08:** o funil registra `median_cycle_days` zero porque as
  oportunidades foram avancadas na mesma sessao de teste. Qualquer calculo de
  esforco baseado nisso e invalido enquanto o dado nao for real.
