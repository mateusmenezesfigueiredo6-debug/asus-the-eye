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
