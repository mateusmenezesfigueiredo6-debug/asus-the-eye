# Spec — problema quântico de 12–16 qubits (benchmark técnico)

> Fecha a pendência do `RETOMADA.md` ("problema quântico maior 12–16 qubits").
> Documento de ESPECIFICAÇÃO; a implementação vai em
> `src/asus_theye/benchmark/`, mantendo o contrato atual do QAR
> (`metrics.quantum_advantage_ratio = score_qaoa / score_classical`).
> Referências de leitura: `src/asus_theye/benchmark/` (clássico × QUBO × QAOA) e
> `~/Downloads/quantum_gratis.py`. Simulação **local** (qiskit Aer); o gate
> `THE_EYE_IBM_EXECUTE` continua fechado (sem QPU real).

## 1. Escolha do problema: Max-Cut (não knapsack)

O problema-demônio atual é um **knapsack** de 6 variáveis (`problem.py`). Para
12–16 qubits, o alvo natural do QAOA é o **Max-Cut**, por três razões:

1. **Mapa 1-para-1 qubit↔nó**: um grafo de N nós → N qubits, sem qubits de folga.
   14 nós → 14 qubits, dentro da faixa pedida.
2. **QUBO/Ising exato e canônico**, sem penalidade de restrição (o knapsack
   precisa de penalidade para a capacidade, que polui o QAR).
3. **Ótimo clássico ainda tratável**: 2¹⁴=16 384 (e 2¹⁶=65 536) cortes — força
   bruta exata roda em milissegundos, então o `score_classical` é o **ótimo
   verdadeiro**, e o QAR mede aproximação real, não clássico-heurístico.

## 2. Definição do grafo (fixo, reprodutível)

Grafo `G(N, seed)` **determinístico** (nada de aleatório em runtime — o projeto
proíbe; o seed viaja no problema):

- `N = 14` (padrão; configurável 12–16).
- Arestas: grafo 3-regular gerado por um seed fixo (`seed=42`), pesos unitários
  (Max-Cut não-ponderado) ou pesos inteiros pequenos declarados. 3-regular dá
  densidade suficiente para o QAOA não ser trivial e o ótimo não ser óbvio.
- O grafo é **serializado no problema** (`nodes`, `edges`, `seed`) e entra no
  hash do relatório — reprodutível bit a bit.

## 3. Encoding QUBO / Ising

Para Max-Cut, com `x_i ∈ {0,1}` indicando o lado do corte:

    maximizar  C(x) = Σ_(i,j)∈E  w_ij · (x_i + x_j − 2·x_i·x_j)

Ising equivalente (para o QAOA), com `z_i ∈ {−1,+1}`:

    C = Σ_(i,j)∈E  w_ij · (1 − z_i·z_j) / 2

- Custo (`cost Hamiltonian`): `H_C = Σ w_ij · (I − Z_i Z_j)/2`.
- Mixer padrão: `H_B = Σ X_i`.
- `score(x)` = valor do corte — reaproveita a interface `BenchmarkProblem.score`.

## 4. Parâmetros do QAOA

- Camadas `p`: 1, 2 e 3 (varredura — o QAR melhora com `p`, e a honestidade é
  mostrar a curva, não só o melhor ponto).
- Otimização dos ângulos (`γ, β`): busca clássica leve (COBYLA ou grid grosso),
  seed fixo. Sem otimizador estocástico não-reprodutível.
- `shots`: 1024 (consistente com o benchmark atual).
- Backend: `qiskit-aer` statevector para N≤16 (exato, sem ruído) e,
  opcionalmente, `aer` com shots para o custo amostral. QPU real permanece
  atrás do gate fechado.

## 5. Formato do QAR e a ressalva honesta

Mantém `metrics.quantum_advantage_ratio(score_qaoa, score_classical)`:

- `score_classical` = **ótimo exato** (força bruta em 2^N) — é o teto real.
- `score_qaoa` = melhor corte amostrado pelo QAOA no melhor `p`.
- `qar = score_qaoa / score_classical ∈ (0, 1]`; QAR = 1,0 significa que o QAOA
  achou o ótimo.

**Ressalva obrigatória no relatório** (regra do projeto — nunca vender vantagem
que não existe):

> "QAR ≤ 1,0 por construção: o clássico aqui é o ótimo EXATO (força bruta em
> 2^N), viável até ~20 qubits. Este benchmark mede a QUALIDADE DA APROXIMAÇÃO do
> QAOA contra o ótimo, não vantagem quântica — que exigiria um regime onde o
> clássico não alcança o ótimo. A curva QAR × p é publicada inteira; o tempo do
> QAOA (simulado) NÃO é comparável a tempo de QPU real."

## 6. Plano de implementação (`src/asus_theye/benchmark/`, do Claude)

- `maxcut.py` — `MaxCutProblem` (grafo determinístico por seed, `score`, QUBO,
  força bruta exata), no estilo de `problem.py`.
- `qaoa_benchmark.py` — estender para o `H_C` de Max-Cut e a varredura de `p`.
- `report.py` — acrescentar a curva `QAR × p` e a ressalva acima.
- CLI `asus-theye benchmark --problem maxcut --nodes 14 --p 1,2,3`.
- Testes: ótimo de força bruta bate com um grafo pequeno conhecido; QAR ∈ (0,1];
  QAR não-decrescente (tendência) com `p`; reprodutibilidade por seed.

## 7. O que fica de fora

- Nada de QPU real (gate fechado, sem custo).
- Nada de alegar "vantagem quântica" — o clássico exato vence sempre nesta
  escala, e o relatório diz isso na cara.
- N > 18 fica para depois (a força bruta exata deixa de ser o teto trivial;
  precisaria de um baseline clássico aproximado, outra discussão).
