# ASUS + THE EYE

Camada local e auditável para comparar um baseline clássico, uma formulação QUBO e uma
simulação QAOA controlada. A versão 0.2 prioriza desempenho, estabilidade, custo e
auditabilidade antes de qualquer alegação de vantagem quântica.

## Benchmark Engine

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

## Plataforma 0.3 — o que está no ar

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
