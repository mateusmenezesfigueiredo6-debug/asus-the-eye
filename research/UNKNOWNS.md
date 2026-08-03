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
