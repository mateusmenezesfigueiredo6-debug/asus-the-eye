# THE EYE

**Observatório auditável de fronteira tecnológica.**

Plataforma local, incremental, auditável e reproduzível para pesquisar, organizar,
relacionar, analisar e acompanhar:

1. **500 inovações** em inteligência artificial, machine learning, predição,
   forecasting, séries temporais, causalidade, decision intelligence, agentes,
   modelos multimodais, robótica, AI for Science, hardware de IA, computação
   quântica, quantum machine learning, algoritmos híbridos quântico-clássicos e
   **áreas emergentes ainda desconhecidas**;
2. **500 pessoas** de maior influência e notoriedade técnica nesses campos;
3. **300 universidades** mais relevantes para esses campos;
4. **conteúdo público** que sustenta tudo isso: artigos, patentes, teses,
   datasets, benchmarks, bibliotecas, repositórios, cursos e discussões técnicas.

## O objetivo é descoberta, não confirmação

O sistema não existe para confirmar o que já se sabe. Ele deve encontrar termos
novos, tecnologias pouco divulgadas, áreas em crescimento, conexões inesperadas
entre campos, algoritmos ressurgentes, grupos de pesquisa emergentes, **pessoas
subestimadas**, universidades fora dos rankings convencionais e projetos abertos
com crescimento anormal.

Uma plataforma que só devolve o que o operador já digitou falhou, por melhor que
esteja construída.

## Por que auditável

Tudo que acontece vira um evento encadeado por hash que ninguém — nem o dono —
reescreve depois. Isso não é preciosismo de engenharia: descoberta só vale se a
trilha da afirmação até a fonte primária não puder ser alterada mais tarde. É o
que separa um observatório de uma opinião com números.

Três regras atravessam o projeto: métrica social nunca vira score; toda resposta
guarda proveniência com SHA-256, URL e horário; e o que não foi medido não é
afirmado.

## O pipeline — uma plataforma, sete etapas

    ingestão → classificação → processamento → operação → evidência
             → verificação → publicação

| Etapa | O que faz | Estado |
|---|---|---|
| 1. Ingestão | grafo de fontes: descobre e faz hash do que existe | conectores ROR, Crossref, arXiv e DOAJ implementados |
| 2. Classificação | taxonomia de 145 áreas em 22 grupos; contexto decisório | 145/145 com alias PT-BR |
| 3. Processamento | benchmark clássico/QUBO/QAOA, LLM local, adaptador IBM | QAR honesto, quantum travado |
| 4. Operação | verticais que consomem a plataforma | Radar Jurídico (um vertical, não o produto) |
| 5. Evidência | hash chain, Merkle, ledger em Cloudflare | staging no ar |
| 6. Verificação | governança L0–L6, contrato de ancoragem | promoção exige aprovação humana |
| 7. Publicação | superfície pública de verificação | **não construída** |

O registro que mede intenção contra artefatos existentes é
`data/mistress-chart/projects.json`. Ele conta um artefato apenas quando o arquivo
existe em disco — status declarado não conta.

## O que este projeto recusa

- ranquear por popularidade, estrelas, seguidores ou citação como prestígio;
- afirmar vantagem quântica sem medida (o QAR atual é 1,0 e isso está publicado);
- montar lista de pessoas físicas a partir de fonte pública;
- promover fase sem aprovação humana registrada;
- publicar número cuja origem não possa ser reaberta.

## Começar

```bash
make setup     # ambiente + dependências
make check     # lint + tipos + testes (o que o CI roda)
asus-theye chart          # medição do projeto por artefato existente
asus-theye source-graph   # cobertura do grafo de fontes
asus-theye benchmark      # clássico vs QUBO vs QAOA
```

## Licença

Código sob **AGPL-3.0**: quem oferecer esta plataforma como serviço de rede
precisa publicar o fonte modificado. `data/` **não** está sob AGPL — a taxonomia,
os aliases e as séries são curadoria sob licença restrita (`data/LICENSE`).
Detalhes em `LICENSE.md`. Autoria em [`AUTHORS.md`](AUTHORS.md).

---

## Detalhe técnico — motor de benchmark (etapa 3)

O engine executa o mesmo problema binário nos três caminhos e registra:

- tempo, memória, combinações e versão no baseline clássico;
- dimensão, termos, densidade, construção e resolução do QUBO;
- backend, shots, camadas, profundidade, tempo, score e fidelidade no QAOA local;
- QAR (`score_qaoa / score_classical`), razão de velocidade, diferença de qualidade e
  estabilidade em dez execuções;
- CPU, RAM e estimativas de custo/QPU em um ledger JSONL encadeado por SHA-256.

Instale em ambiente virtual e execute:

```bash
python -m pip install -e '.[telemetry,dashboard,dev]'
asus-theye benchmark
```

O relatório atual fica em `reports/benchmark/latest.json`; o histórico resumido em
`history.jsonl`; e as evidências auditáveis em `ledger.jsonl`. A página HTML de dashboard
é gerada por `asus_theye.dashboard.benchmark_page`. Em uma aplicação FastAPI existente,
registre `register_benchmark_routes(app)` para expor `GET /benchmark`, ou use
`create_dashboard_app()` para criar uma aplicação independente.

### Limitações

O QAOA 0.2 é um simulador local de vetor de estado, reproduzível e com busca controlada
de parâmetros variacionais; ele não é evidência de desempenho de hardware quântico. A
comparação usa um dataset demo pequeno e tempos de parede dependentes da máquina. QAR
acima de 1 é apenas um sinal para investigação, nunca prova científica automática.

Detalhes metodológicos e operacionais: [docs/BENCHMARK_ENGINE.md](docs/BENCHMARK_ENGINE.md).

## Camadas em operação (recorte da etapa 3 e 5)

| Camada | Estado |
| --- | --- |
| Benchmark clássico/QUBO/QAOA local | `asus-theye benchmark` (QAR honesto) |
| Ledger de auditoria em produção (staging) | Worker Cloudflare + D1 append-only + R2 — hash chain viva |
| Publicação de evidência | `asus-theye benchmark --publish` (resumo + hash; relatório fica local) |
| LLM local auditado | `asus-theye llm` (Ollama/qwen2.5:3b; prompts nunca saem da máquina) |
| Fase G — contexto decisório (judiciário) | 10 schemas LGPD-por-construção + `asus-theye extract-decision` (híbrido LLM+regex, divergências sinalizadas) |
| IBM Quantum (gated) | `asus-theye quantum` (dry-run); `--execute` exige `THE_EYE_IBM_EXECUTE=1` |

Primeira execução em hardware real: QAOA de 6 qubits em `ibm_kingston` (Heron
156q) encontrou o ótimo exato — com a ressalva honesta, registrada no ledger,
de que um problema de 64 estados amostrado por 1.024 shots não demonstra
vantagem quântica. Evidência: evento 6 da cadeia, job `d9ngkpcsfqic73ar17vg`.

## Estrutura

```
src/asus_theye/     código do pacote (layout src, recomendação da PyPA)
apps/observatorio/  varredura dos campos da missão e alimentação do grafo
apps/comercial/     vertical jurídico (Radar) — um vertical, não a plataforma
apps/verifier/      verificação de cadeia offline e remota
data/legal-taxonomy/ 145 áreas em 22 grupos, 354 aliases PT-BR
data/source-graph/  conectores, categorias, fontes descobertas
data/mistress-chart/ registro que mede intenção contra artefatos
docs/               ADRs, governança, segurança, metodologia
  adr/              decisões arquiteturais, com o que as reverteria
  governance/       protocolo de lançamento L0–L6, runbook, gates
infra/cloudflare/   worker do ledger (D1 + R2)
scripts/            trava de publicação, checagem de vazamento, portões
tests/              espelha src/ e apps/
research/           perguntas, decisões, incógnitas, fontes
```

Detalhes das decisões: [ADR-012](docs/adr/ADR-012-ESTRUTURA-E-FERRAMENTAS.md).
Como contribuir e as regras inegociáveis: [CONTRIBUTING.md](CONTRIBUTING.md).
