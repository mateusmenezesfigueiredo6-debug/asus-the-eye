# EXTRACAO PARA CODEX — ASUS / THE EYE

Cole este arquivo inteiro como primeiro prompt no Codex, dentro de
`/home/sexexes/asus_the_eye`. Ele devolve o escopo REAL do projeto e corrige
uma reducao que ocorreu em sessoes recentes.

---

## 1. O erro que esta extracao corrige

Sessoes recentes trataram o projeto como se fosse **uma plataforma comercial de
direito com 15 nichos**. Nao e. Isso e UM dos doze projetos, e mesmo ele foi
reduzido: a taxonomia real tem **145 areas em 22 grupos**, e o recorte usado
tinha 15.

Tambem houve confusao entre benchmarks. Existem **dois benchmarkings
estrategicos** (Palantir e Kalshi) e **um benchmark tecnico** (classico / QUBO /
QAOA). Sao coisas distintas e nao devem ser misturadas.

---

## 2. O que o projeto e

THE EYE e uma plataforma de **evidencia auditavel**: tudo que acontece vira um
evento encadeado por hash que ninguem — nem o dono — reescreve depois.

O projeto inteiro e UM pipeline de sete etapas, medido pelos artefatos que
existem, nunca por status declarado:

    ingestao -> classificacao -> processamento -> operacao -> evidencia
             -> verificacao -> publicacao

Registro que mede intencao contra realidade: `data/mistress-chart/projects.json`.

## 3. Os 12 projetos (nao um)

| Etapa | Projeto | Artefatos declarados |
|---|---|---|
| 1-ingestao | Grafo de fontes de conhecimento (Fase C) | 35 |
| 2-classificacao | Contexto decisorio (Fase G — judiciario) | 14 |
| 2-classificacao | Taxonomia legal (145 nichos) | 8 |
| 3-processamento | Engine de benchmark (classico / QUBO / QAOA) | 5 |
| 3-processamento | LLM local auditado (Ollama) | 3 |
| 3-processamento | Adaptador IBM Quantum (gated) | 2 |
| 4-operacao | Plataforma comercial (direito) | 9 |
| 5-evidencia | Nucleo de auditoria (hash chain, Merkle, verifier) | 10 |
| 5-evidencia | Ledger em producao (Cloudflare D1 + R2 + Worker) | 5 |
| 6-verificacao | Governanca (trava, protocolo, checagem de vazamento) | 8 |
| 6-verificacao | Contrato de ancoragem (Base Sepolia) | 4 |
| 7-publicacao | Superficie publica de verificacao | 3 |

**Trabalho recente concentrou-se apenas no projeto 4.** Os demais nao foram
tocados desde 30/07 ou antes.

## 4. Os 22 grupos da taxonomia — o escopo NAO e so direito brasileiro

    civil-and-consumer, corporate-and-transactions, criminal-and-compliance,
    crypto-and-web3, defense-security-and-space, energy-and-natural-resources,
    environment-and-climate, financial-services, health-and-life-sciences,
    infrastructure-and-transport, insolvency-competition-trade,
    intellectual-property, international-and-human-rights,
    labor-and-social-security, legal-profession-and-operations,
    media-and-consumer-brands, political-and-legislative,
    procedure-and-disputes, public-law, sports-games-and-betting,
    technology-data-and-cyber, third-sector-and-religion

Fonte: `data/legal-taxonomy/legal_areas.master.json` (145 areas, campo `areas`).

## 5. Os DOIS benchmarkings estrategicos

### 5.1 Palantir — benchmark de arquitetura
Referencia de COMO construir: ontologia de objetos com relacoes explicitas,
linhagem do dado ate a fonte primaria, decisao apoiada em evidencia rastreavel,
recusa de afirmar o que nao foi medido.
Estado: aplicado no projeto 4 (ontologia + SHA-256 + proveniencia por consulta).
Pendente: estender aos projetos 1, 2 e 5.

### 5.2 Kalshi — benchmark de produto
Referencia de O QUE entregar: mercado de predicao, precificacao de eventos,
resolucao objetiva, liquidez.
Estado: PRESERVADO por ordem do dono (branch `kalshi-20260725` em `~/asus`,
nunca apagar). Nao foi evoluido nas sessoes recentes.

### 5.3 Nao confundir com o benchmark tecnico
`src/asus_theye/benchmark/` compara classico, QUBO e QAOA no MESMO problema e
publica QAR (quantum advantage ratio) com ressalva honesta. E medicao de
desempenho, nao referencia estrategica.
Ultimo resultado: QAR 1,0 — o classico empata em qualidade e e ~40x mais rapido
no tamanho atual do problema. Isso esta registrado, nao escondido.

## 6. Estado tecnico verificado (05/08/2026)

- 300 testes verdes, lint limpo (`make check`)
- 5.957 linhas de codigo em `src/` + `apps/`
- Servicos sob systemd de usuario: `asus-api` (8713), `asus-dashboard` (8712),
  `asus-site` (8790) — `Restart=always`, so em 127.0.0.1
- Quatro repositorios com remoto privado no GitHub
- Site publico: theyeofgod.pages.dev (dominio proprio theyeofgod.org NAO ligado;
  ha Cloudflare Access na frente)
- Cloudflare: R2 `asus-frio`, `projeto-algoritmos-backup`, `the-eye-audit-staging`;
  Worker `the-eye-audit-staging`; Pages `theyeofgod`

## 7. Regras invioláveis

1. **Quantum so roda com autorizacao explicita do dono.** Trava em
   `/home/sexexes/Downloads/projeto-algoritmos/quantum/GATE.py` (exige
   `QUANTUM_OK=1`). Cota IBM e escassa: ~133s de 600 na janela de 28 dias.
2. **Nunca apagar nada de Kalshi.**
3. **Sem emojis** em qualquer saida.
4. **Honestidade estatistica**: nunca afirmar o que nao foi medido. Se o modelo
   nao vence a media simples, publicar isso.
5. **Dado pessoal**: nichos cuja parte nomeada e pessoa fisica nao recebem
   extracao (`tipo_parte: fisica` na ontologia). Estatistica agregada sim,
   cadastro de individuos nao.
6. **Nada sai da maquina sem senha**: `scripts/publish_lock.py`.
7. Nenhuma fase L0-L6 promove sem aprovacao humana registrada
   (`docs/governance/IMPLEMENTATION_ROADMAP.md`).

## 8. Tarefa para o Codex

Na ordem, sem pular:

1. Rode `python3 -c "import json; d=json.load(open('data/mistress-chart/projects.json'))"`
   e produza a medicao REAL de cada um dos 12 projetos: para cada artefato
   declarado, verifique se o arquivo existe. O chart mede realidade, nao status.
2. Aponte quais dos 12 projetos regrediram ou estagnaram desde 30/07/2026.
3. Para o projeto 4 (plataforma comercial), avalie o custo de subir de 15 para
   os 145 nichos da taxonomia: o que quebra, o que precisa de padrao de
   extracao novo, o que cai na regra de dado pessoal.
4. Proponha como os benchmarkings Palantir e Kalshi voltam a orientar o roadmap,
   sem misturar com o benchmark tecnico.
5. NAO execute quantum. NAO altere nada de Kalshi. NAO publique nada.

Entregue um relatorio em `docs/architecture/MEDICAO_REAL_12_PROJETOS.md`.
