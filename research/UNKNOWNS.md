# Incógnitas

O que ainda não sabemos, explicitamente. Preferir `UNKNOWN` a palpite é regra do
`AGENTS.md`; este arquivo é onde os `UNKNOWN` moram em vez de virarem suposição
silenciosa.

---

## U001 — Modelo de ameaça para rastreamento

**Pergunta:** rastreado por quem, e com que consequência?

Levantado pelo dono em 2026-08-02 ("temos que ter certeza que nunca seremos
rastreados nas interações"), sem modelo de ameaça definido. As três leituras
possíveis levam a desenhos diferentes:

| Leitura | Solução |
| --- | --- |
| As fontes não devem saber o que pesquisamos | Dumps em massa: 1 requisição em vez de milhares |
| Nossos dados não devem vazar a terceiros | **Já resolvido**: LLM local, ledger só com hashes, repo privado, worker com token |
| Anonimato total, sem identificação | Conflita com `AGENTS.md` (attribution, não burlar controle de acesso) e com os termos das APIs |

**Bloqueia:** o primeiro fetch real (Estágio 2). **Não bloqueia** o Estágio 1.

## U002 — Identidade a usar quando a API exigir contato

SEC EDGAR **exige** User-Agent com contato. Crossref polite pool e Open Library
pedem. Opções: e-mail genérico do projeto · só fontes que não exigem · só dumps.

Sem decisão, nenhum conector que exija identificação pode ser habilitado.

## U003 — Cobertura real por categoria

Não sabemos quantas entidades qualificadas existem de fato em nenhuma das 19
categorias — nenhuma busca foi executada. É por isso que todo `qualified_count`
é 0 com `blocking_reason: not_yet_attempted`, e não uma estimativa.

## U004 — Licenças dos 23 artefatos de software

As licenças em `software_artifacts.json` são as **declaradas publicamente** pelos
projetos, não verificadas com hash do arquivo `LICENSE`. Por isso todos estão em
`verification_status: declared_unverified`. Promover a `FACT` exige buscar e
hashear cada uma.

## U005 — Se o dump CC0 do OpenAlex cabe no disco disponível

O dump completo (480M works) é grande. Antes de baixá-lo, medir espaço livre e
decidir se ingerimos o conjunto todo ou um recorte por tópico.

## U006 — Se os limites de taxa verificados em 2026-08-02 seguem válidos

ROR muda no 3º trimestre de 2026 (passa a exigir client ID; sem ele, 50 req/5min
em vez de 2.000). Crossref revisou limites em 01/12/2025. Reverificar antes de
cada corrida.

## U101 — Baseline do projeto em 30/07/2026

Não existe commit em ou antes de 30/07 no histórico local. Sem snapshot, tag ou
repositório anterior, regressão desde essa data não é mensurável.

## U102 — Cardinalidade de uma eventual segmentação comercial

Não há meta atual de operar 145 produtos. THE EYE permanece uma plataforma única
que pode ser segmentada quando o dono quiser. Se essa opção for exercida, ainda
será necessário escolher entre produtos agregadores (106 áreas hoje fora do
recorte) e 145 nichos um-a-um (+130 configurações).

## U103 — Classificação de pessoa física nas 145 áreas

Apenas três nichos atuais têm `tipo_parte: fisica`. A taxonomia não contém esse
campo. O total do universo de 145 é desconhecido e não deve ser inferido do nome.

## U104 — Necessidade de padrão de extração por área

Oito nichos atuais possuem regex, quatro usam modo genérico e três são
bloqueados. Não existe corpus ou especificação para decidir quantos dos novos
objetos precisam de padrão próprio.

## U105 — Fonte pública equivalente por área

A ontologia atual declara o Querido Diário. Uma corrida local tentou essa mesma
fonte para as 145 áreas e salvou 138 contagens, 7 ausências e 6 termos suspeitos,
mas consulta com retorno não prova adequação. Não existe matriz área→fonte nem
definição operacional de “equivalente”. O número sem fonte adequada permanece
desconhecido até pesquisa primária e validação.

## U106 — Utilidade comercial da QKP depois da correção dos dados

Não há custos por área, evidência de sinergia comercial nem validação de que a
contagem máxima entre aliases mede demanda. O ótimo matemático da formulação
atual não responde quais áreas devem receber orçamento. Isso exige dados
observados, critérios de fonte e análise de sensibilidade antes de nova seleção.
