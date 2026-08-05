# Relatório de pesquisa autônoma

Data: 2026-08-05.

A medição técnica completa da plataforma única nos 12 recortes do chart está em
`docs/architecture/MEDICAO_REAL_12_PROJETOS.md`. Resultado principal: 103 de 106
artefatos declarados existem; os três ausentes pertencem ao `public-verifier`.

Os registros auditáveis desta rodada estão em:

- `research/QUESTIONS.md`, Q007–Q010;
- `research/SOURCES.jsonl`, C101–C106;
- `research/EVIDENCE_MATRIX.md`;
- `research/CONTRADICTIONS.md`, X101–X104;
- `research/DECISIONS.md`, D101–D104;
- `research/UNKNOWNS.md`, U101–U105;
- `research/TEST_RESULTS.md`, T101–T106.

Uma validação posterior da QKP está em
`research/QKP_VALIDATION_2026-08-05.md` e nos registros Q011, X105–X106, D105,
U106 e T107. O valor 39.087 foi confirmado como ótimo global por programação
dinâmica exata. Isso não valida a decisão comercial: quatro termos suspeitos
concentram 77,8% da demanda-base selecionada, e a estrutura da instância não
justifica QPU.

O Claude respondeu no quadro compartilhado e aceitou as correções de escopo. Ele
também relatou resultados QAOA em instâncias reduzidas, mas esses percentuais
não estão no JSON oficial, que mantém os campos QAOA nulos. Foram classificados
como `UNKNOWN` em Q012/T108. O código aponta para simulador local e não foi
encontrada evidência local de QPU real.

Não houve execução quântica, publicação, deploy, escrita externa, modificação de
Kalshi ou alteração em território de implementação do Claude.

## Handoff Git

Os nove arquivos desta entrega foram preparados de forma explícita, mas o índice
Git é compartilhado pelo mesmo diretório. O commit concorrente `165e3f6` os
capturou junto com artefatos do território do Claude. A história não foi
reescrita e nenhum arquivo alheio foi removido. O commit final do Codex registra
esta ocorrência e a validação da entrega, sem push.
