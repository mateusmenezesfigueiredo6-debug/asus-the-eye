# Handoff para o Codex — 17/08/2026 (revisado: território respeitado)

Você é o Codex, trabalhando EM PARALELO com o Claude Code no mesmo repositório
`/home/sexexes/pegasus/asus_the_eye`. Duas tarefas de **PROJETO e PESQUISA**,
ambas dentro do SEU território — nenhuma toca `src/`.

## Antes de tudo (leia nesta ordem)

1. `AGENTS.md` — missão e regras inegociáveis (UNKNOWN over guess; Brier nulo
   até liquidar; janela sempre declarada; Kalshi é comparador, nunca fonte;
   nada de custo/broadcast/deploy).
2. `COORDENACAO.md` — territórios.

## Territórios (protocolo do repo — NÃO viole)

- **SEU (Codex):** `docs/architecture/`, `research/`, `reports/AUTONOMOUS_*`,
  `data/legal-taxonomy/`, `data/mistress-chart/`.
- **DO CLAUDE (não edite):** `src/asus_theye/`, `apps/`, `tests/`,
  `reports/markets/`, `reports/provenance/`, `contracts/`.
- **NÃO commitar, NÃO push.** Deixe os arquivos novos no working tree.

Estas tarefas são de **design/pesquisa** (documentos em `docs/architecture/`).
A IMPLEMENTAÇÃO em `src/` fica com o Claude, a partir do que você projetar.

## Política de reuso por licença (do dono, permanente)

Só absorver de fonte com licença que PERMITE: permissiva (MIT/Apache/BSD) ou
copyleft compatível (AGPL). Repo SEM licença = proibido. Proprietário
(Palantir/Kalshi) NUNCA — usa-se a categoria (ideia) e a API pública, nunca o
código. Toda ideia absorvida cita origem + arquivo + commit + licença.

## TAREFA A — Projeto da ontologia de Evidência

Alvos legítimos (Apache-2.0, confirmados): `open-metadata/OpenMetadata`,
`datahub-project/datahub`. Clone raso em `/tmp` (NUNCA dentro do repo).

Estude como modelam entidades, relações, linhagem (upstream/downstream),
versionamento de schema e proveniência. Entregue:

`docs/architecture/ONTOLOGIA_EVIDENCIA.md` — proposta de ontologia para os
NOSSOS objetos: `Fonte → Artefato → EventoSelado → LoteMerkle → Âncora →
Recibo`, mais `Mercado`/`Resolução` (ver `src/asus_theye/markets/*.py` só como
LEITURA de referência). Para cada entidade: campos, relações, e o que absorver
de OpenMetadata/DataHub (com arquivo + commit de origem) vs o que fica de fora e
por quê. Em português, honesto, sem prometer o que não existe. É a base do app
"THE EYE Evidência" (benchmark de arquitetura: Palantir).

## TAREFA B — Spec do problema quântico de 12–16 qubits

Pendência do `RETOMADA.md`. Referências de LEITURA: `src/asus_theye/benchmark/`
(clássico × QUBO × QAOA, QAR com ressalva) e `/home/sexexes/Downloads/quantum_gratis.py`.

Entregue `docs/architecture/QUANTUM_12_16_QUBITS.md`: a especificação de um
problema de otimização de 12–16 qubits (ex.: Max-Cut/QUBO em grafo definido),
o encoding para QAOA, os parâmetros, o formato do QAR e a ressalva honesta
esperada (aproximação vs clássico exato). É SPEC, não código — o Claude
implementa em `src/asus_theye/benchmark/` a partir dela.

## Como devolver

Escreva `HANDOFF_RETORNO.md` na raiz: o que fez, o que ficou de fora e por quê,
e o que você leu. O Claude revisa (revisão adversarial), implementa o que for de
`src/`, e commita com o dono.
