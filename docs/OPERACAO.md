# Operação da plataforma

Se `asus-theye` não estiver no `PATH`, use `.venv/bin/asus-theye` no clone local.
Os exemplos abaixo assumem instalação feita com `make setup`.

## O que a plataforma faz

- Emite e liquida mercados preditivos contra fonte oficial nomeada, nunca contra outra opinião.
- Mede o erro de contratos já fechados; contrato aberto não ganha Brier.
- Sela cada liquidação, divergência e medição numa corrente append-only versionada em `reports/markets/eventos.jsonl`.
- Espelha a corrente no ledger restrito da nuvem (`D1`) sem subir documentos brutos nem segredos.
- Pode ancorar lotes Merkle na Base Sepolia para provar quando a corrente já existia.

## Rotina mensal

O cron de `/home/runner/work/asus-the-eye/asus-the-eye/.github/workflows/operacao-continua.yml` roda às `13:00 UTC` nos dias `11–15` de cada mês.

Sozinho, ele faz isto:

1. instala o pacote com `python -m pip install --quiet -e .`;
2. fora do modo de ensaio, restaura `reports/audit/pseudonimos.key` a partir do segredo `THE_EYE_AUDIT_KEY_HEX`;
3. roda `python -m asus_theye.cli markets-resolve`;
4. tenta arquivar o vintage do mês com `python -m asus_theye.cli markets-vintage --mes "$(date -u +%Y-%m)"`;
5. roda `python -m asus_theye.cli projeto-medir`;
6. se `THE_EYE_ANCHOR_PK` existir, instala `.[anchor]` e roda `python -m asus_theye.cli markets-anchor --execute --minimo 10`;
7. roda `python -m asus_theye.cli ledger-sync` para espelhar a corrente no D1;
8. adiciona `reports/markets` e `reports/projeto` e só commita se houve mudança.

O que continua sendo ato humano:

- plantar e rotacionar os segredos `THE_EYE_AUDIT_KEY_HEX`, `THE_EYE_LEDGER_TOKEN` e, se quiser ancoragem automática, `THE_EYE_ANCHOR_PK`;
- fundear a carteira de `reports/audit/anchor.key` na Base Sepolia;
- investigar falhas de fonte, de corrente, de espelho ou de âncora;
- rodar o ensaio manual (`workflow_dispatch` com `somente_verificar=true`), que hoje só executa `python -m asus_theye.cli projeto-medir --json --no-audit` e não sela, não espelha e não commita;
- manter backup cifrado das chaves e do token local.

## Comandos do dia a dia

| Subcomando | Para que serve | Exemplo |
| --- | --- | --- |
| `benchmark` | Roda o benchmark local clássico/QUBO/QAOA. | `asus-theye benchmark --output-dir reports/benchmark` |
| `audit-verify` | Verifica um documento JSON de auditoria offline e devolve recibo. | `asus-theye audit-verify evidence.json --receipt receipt.json` |
| `llm` | Chama o LLM local auditado via Ollama. | `asus-theye llm "Explique este hash" --model qwen2.5:3b` |
| `adjudicate` | Faz proposer/challenger; divergência vira `CONFLICTED`. | `asus-theye adjudicate "Esta alegação é FACT?" --proposer openai --challenger anthropic` |
| `extract-decision` | Extrai campos estruturados de uma decisão pública em texto. | `asus-theye extract-decision decisao-publica.txt` |
| `batch` | Monta lote Merkle de eventos pendentes do ledger. | `asus-theye batch --ledger-url "$THE_EYE_LEDGER_URL" --proofs-out reports/audit/proofs` |
| `source-graph` | Gera cobertura, lacunas e relatórios do grafo de fontes. | `asus-theye source-graph --reports` |
| `chart` | Renderiza o Mistress Chart de projetos e nichos. | `asus-theye chart --html reports/chart/mistress-chart.html` |
| `quantum` | Ensaia o adaptador IBM Quantum; execução real continua gated. | `asus-theye quantum --shots 1024 --layers 2` |
| `markets-reconcile` | Reconcilia o scoring do módulo contra o banco medido. | `asus-theye markets-reconcile --db "$ASUS_MARKETS_DB" --json` |
| `markets-resolve` | Liquida mercados vencidos, sela e emite o mês seguinte. | `asus-theye markets-resolve --json` |
| `markets-emitir` | Emite um mercado mensal para uma área resolvível. | `asus-theye markets-emitir --area juros --mes 2026-09 --limiar 14.0 --json` |
| `markets-vintage` | Arquiva o consenso Focus vigente do mês e sela o corte. | `asus-theye markets-vintage --mes 2026-09 --json` |
| `markets-comparar` | Mede divergência versus Kalshi sem usar Kalshi para resolver. | `asus-theye markets-comparar --claim MACRO-01::2026-08 --ticker INFLATION-26SEP-T500 --nota "CPI/EUA como comparador imperfeito" --preco 0.615 --json` |
| `markets-sinais` | Mostra os sinais reais (Focus/IPCA-15) e a probabilidade WPAM. | `asus-theye markets-sinais --mes 2026-09 --limiar 0.5 --json` |
| `markets-anchor` | Faz ensaio offline de ancoragem ou broadcast real se autorizado. | `asus-theye markets-anchor --minimo 10` |
| `serve` | Sobe o dashboard local. | `asus-theye serve --port 8712` |
| `benchmark-maxcut` | Mede a curva QAR×p do Max-Cut 12–16 qubits. | `asus-theye benchmark-maxcut --nodes 14 --layers 1,2,3 --json` |
| `projeto-medir` | Mede o estado declarado do projeto e sela o hash. | `asus-theye projeto-medir --json` |
| `mlops-benchmark` | Rastreia a suíte de benchmark como corrida MLOps selada. | `asus-theye mlops-benchmark --shots 1024 --layers 2 --json` |
| `mlops-promover` | Promove uma versão de modelo a campeão ou desafiante. | `asus-theye mlops-promover --modelo nowcast-ipca --versao r4 --papel desafiante --motivo "Brier selado" --json` |
| `publicar-ancora` | Publica lote e âncora no D1 para o verificador público. | `asus-theye publicar-ancora --ledger-url "$THE_EYE_LEDGER_URL" --json` |
| `ledger-sync` | Espelha a corrente selada no ledger restrito da nuvem. | `asus-theye ledger-sync --ledger-url "$THE_EYE_LEDGER_URL" --json` |
| `verificar-espelho` | Compara a corrente local com o espelho remoto e aponta faltas na janela. | `asus-theye verificar-espelho --ledger-url "$THE_EYE_LEDGER_URL" --json` |
| `export-static` | Exporta os painéis como HTML estático em `dist/`. | `asus-theye export-static --out dist --json` |
| `relatorio-mensal` | Gera o extrato mensal em Markdown da atividade da plataforma. | `asus-theye relatorio-mensal --mes 2026-08` |
| `relatorio-anual` | Consolida o ano por área: Brier médio dos liquidados elegíveis, com as ressalvas de skill. | `asus-theye relatorio-anual --ano 2026` |
| `doutor` | Diagnóstico local: corrente, chave, prova temporal, mercados, titularidade e backup — com o conserto de cada item. | `asus-theye doutor` |

## Quando algo quebra

| Sintoma | Causa provável | Comando |
| --- | --- | --- |
| `markets-resolve` ou `projeto-medir` falha com `a chave de pseudonimização ativa não é a da corrente`. | `reports/audit/pseudonimos.key` não bate com `reports/markets/chave.fingerprint`; trocar a chave bifurcaria os pseudônimos. | `./scripts/backup_chaves.sh --verificar /caminho/para/the-eye-chaves-AAAA-MM-DD.tar.gz.gpg` para conferir o backup antes de restaurar a chave correta. |
| `ledger-sync` ou `verificar-espelho` acusa que a corrente não verifica. | `reports/markets/eventos.jsonl` foi editado, truncado ou entrou num merge fora de ordem. | `asus-theye verificar-espelho --ledger-url "$THE_EYE_LEDGER_URL" --json` para confirmar o erro sem escrever nada; depois restaure a corrente canônica antes de selar de novo. |
| `markets-resolve`/`markets-sinais` retorna `fonte oficial inalcançável` ou `Focus/Olinda inacessível`. | BCB/Olinda fora do ar, timeout ou resposta malformada. | `asus-theye markets-sinais --mes 2026-09 --limiar 0.5 --json` para testar o sinal do mês; se a falha for de resolução, repita `asus-theye markets-resolve --json` quando a fonte voltar. |
| `markets-anchor --execute` falha com `carteira ... sem saldo na Base Sepolia`. | `reports/audit/anchor.key` existe, mas a carteira está sem gás de testnet. | `asus-theye markets-anchor --minimo 10` para ensaiar offline; depois de fundear a carteira, rode `asus-theye markets-anchor --execute --minimo 10`. |
| `verificar-espelho` mostra `cobertura_da_janela: false` ou faltantes na janela. | `ledger-sync` ainda não rodou, o token do D1 está ausente/expirado ou o worker recusou a gravação. | `asus-theye ledger-sync --ledger-url "$THE_EYE_LEDGER_URL" --json` e, em seguida, `asus-theye verificar-espelho --ledger-url "$THE_EYE_LEDGER_URL" --json`. |

## O que NUNCA fazer

- Nunca publique `*.key`, `~/.the-eye/staging-token`, `~/.the-eye/publish-lock.json` ou qualquer segredo de provedor.
- Nunca reescreva a corrente: correção entra como evento novo; o passado não é editado.
- Nunca use Kalshi como fonte de resolução; Kalshi é comparador, não árbitro.
- Nunca apresente Brier de contrato aberto; o erro só existe depois da liquidação contra fonte oficial.
- Nunca apresente reconstrução retrospectiva como se fosse previsão prospectiva.

## Custódia

Arquivos de custódia que importam na operação:

- `reports/audit/pseudonimos.key`: identidade da corrente auditável;
- `reports/markets/chave.fingerprint`: impressão digital versionada da chave da corrente;
- `reports/audit/anchor.key`: chave local da carteira de ancoragem na Base Sepolia;
- `~/.the-eye/staging-token`: token do ledger restrito;
- `~/.the-eye/publish-lock.json`: hash local da senha de publicação.

Para refazer o backup cifrado:

```bash
./scripts/backup_chaves.sh
```

O script empacota o que existir entre `reports/audit/pseudonimos.key`, `reports/audit/anchor.key`, `reports/markets/chave.fingerprint`, `~/.the-eye/staging-token` e `~/.the-eye/publish-lock.json`, cifra com senha digitada na hora e grava o `.tar.gz.gpg` em `${THE_EYE_BACKUP_DIR:-$HOME/Área de trabalho/organizado/Backups/the-eye-chaves}`.

Para testar se o backup abre sem citar nem registrar senha:

```bash
./scripts/backup_chaves.sh --verificar /caminho/para/the-eye-chaves-AAAA-MM-DD.tar.gz.gpg
```

---

© 2026 Mateus Menezes Figueiredo, AGPL-3.0.
