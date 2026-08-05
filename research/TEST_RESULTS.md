# Resultados de testes — uma plataforma, 12 recortes de medição

## T101 — Existência dos artefatos declarados

- Comando: script Python que carrega `projects.json` e aplica `Path.exists()` a
  cada item de `artifacts`.
- Status: exit 0.
- Resultado: 106 declarados, 103 existentes, 3 ausentes; somente
  `public-verifier` está em 0/3.

## T102 — Histórico e datas de modificação

- Comandos: `git log --since=2026-07-30 --name-only`, último commit por escopo,
  `stat` dos artefatos e `git rev-list -1 --before=...`.
- Status: exit 0.
- Resultado: nenhum commit antes do cutoff; primeiro commit em 01/08;
  `public-verifier` sem histórico ou `mtime`; atividade substantiva após 03/08
  concentrada em `comercial`.

## T103 — Cardinalidades da expansão comercial

- Comando: validação Python de taxonomia, nichos e ontologia.
- Status: exit 0.
- Resultado: 145 áreas, 22 grupos, 15 nichos, 39 áreas mapeadas, 106 não
  mapeadas, 8 padrões customizados, 3 bloqueios físicos e 4 modos genéricos.

## T104 — Integridade do relatório

- Comando: asserts de totais e partições; `python3 -m json.tool` nos quatro JSON
  de entrada; inspeção do diff restrito ao território.
- Status: exit 0.
- Resultado: 106/103/3, 145/22/15/39/106 e 8/3/4 confirmados; entradas JSON
  válidas. Testes de implementação e quantum não foram executados.

## T105 — Snapshot de sinal para a taxonomia

- Comando: leitura local de `reports/commercial/sinal_taxonomia.json`, sem rede
  e sem reexecutar o coletor.
- Status: exit 0.
- Resultado: timestamp 2026-08-05T19:20:01Z; 145 linhas; cobertura declarada
  138/145; 7 sem `mencoes`; 6 com `suspeita_termo_generico=true`.
- Limitação: o snapshot precede o commit `26ebc79`; não valida o código atual nem
  a adequação semântica do Querido Diário para cada área.

## T106 — Isolamento do commit em diretório compartilhado

- Verificação: `git diff --cached --name-only` confirmou somente os nove arquivos
  do território Codex antes do fechamento.
- Resultado: `CONFLICTED`. O agente concorrente executou o commit `165e3f6`
  enquanto o índice estava preparado e incluiu os nove arquivos com artefatos de
  benchmark do território dele.
- Tratamento: preservar a história; não resetar, não reescrever e criar um commit
  final isolado apenas com este registro de handoff.
