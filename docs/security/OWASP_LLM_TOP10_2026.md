<!--
SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
SPDX-License-Identifier: AGPL-3.0-or-later
-->

# Mapeamento OWASP GenAI LLM Top 10 (2026) → THE EYE

Este documento mede a exposição real da plataforma aos dez riscos catalogados
pelo *OWASP GenAI Security Project* na edição 2026 e cita, para cada um, o
controle já em código, o arquivo que o realiza e o risco residual. Segue a
mesma disciplina de `docs/security/THREAT_MODEL.md`: risco listado é risco
*residual* — o que sobra depois dos controles nomeados.

## Escopo

Não é o repositório inteiro. O que este mapeamento cobre é a superfície LLM
explícita:

- `src/asus_theye/llm/audited.py` — wrapper `AuditedLocalLLM`; toda chamada
  gera registro JSONL local encadeado por hash e opcionalmente ancora hashes
  (nunca texto) no ledger.
- `src/asus_theye/llm/dual.py` — adjudicação `proposer` × `challenger`;
  divergência de substância força `CONFLICTED` (não há voto de minerva).
- `src/asus_theye/llm/ollama_client.py` — caminho local padrão.
- `src/asus_theye/llm/remote_client.py` — OpenAI/Anthropic atrás do portão
  `THE_EYE_REMOTE_LLM=1`, sem fallback implícito do local para o remoto.

O gerador de mercados (`src/asus_theye/markets/`) é determinístico e não usa
LLM na rota crítica de emissão/resolução; portanto os riscos abaixo não se
aplicam ao caminho de claim/resolution, e essa fronteira precisa ser mantida.

## Doutrina em uma linha

*"Pare de tentar construir um modelo que não pode ser enganado; construa o
sistema ao redor dele para que, quando for enganado, nada importante quebre."*
— OWASP GenAI Project Leads, 2026. Este documento trata cada risco como
controle de raio de explosão, não como problema de prevenção perfeita.

## Tabela de exposição residual

| Risco | Superfície no THE EYE | Controle atual | Arquivo:linha | Residual |
| --- | --- | --- | --- | --- |
| **LLM01** — Prompt Injection | Qualquer prompt vindo de fonte externa (RAG, documento, saída de tool) entrando em `AuditedLocalLLM.chat` | Adjudicação `dual` força `CONFLICTED` quando o proposer e o challenger divergem; nenhum efeito colateral é acionado a partir da saída do LLM; a saída não vira input de mercado sem revisão humana | `src/asus_theye/llm/dual.py:1` | Médio — nenhuma sanitização estrutural do prompt antes da chamada |
| **LLM02** — Sensitive Information Disclosure | Payloads podem conter dados que não devem ser hasheados nem enviados a provedor remoto (ex.: contexto decisório LGPD do módulo `decision_context`) | `remote_client` explicitamente proíbe *payloads Fase G* (ADR-001, local-only); registros no ledger carregam **apenas hashes** (`prompt_sha256`, `response_sha256`), nunca texto; `SENSITIVE_KEYS` redige chaves conhecidas antes de qualquer selagem | `src/asus_theye/llm/remote_client.py:12`; `src/asus_theye/llm/audited.py:70`; `src/asus_theye/audit/sdk.py:22` | Médio — a lista de chaves sensíveis é atualizada à mão |
| **LLM03** — Excessive Agency | Nenhuma tool-calling autônoma hoje: o LLM não escreve no banco, não posta em rede, não move fundos. Provedor remoto exige env explícita e nome do provedor no *call site* | Ausência de tool interface = zero raio de explosão; portão `THE_EYE_REMOTE_LLM=1` recusa em vez de degradar silenciosamente | `src/asus_theye/llm/remote_client.py:20` | Baixo — enquanto tool-calling não for adicionado; se for, releitura obrigatória |
| **LLM04** — Supply Chain | Dependências Python; ollama binário; imagens de modelos; pacotes das SDKs OpenAI/Anthropic (via HTTP puro em `urllib`, sem SDK oficial) | `remote_client` usa `urllib.request` da stdlib (não puxa SDK de terceiros); dependências mínimas; ADR-001 fixa vetores canônicos independentes; SBOM previsto em `THREAT_MODEL.md` linha "Dependency/build attacker" | `src/asus_theye/llm/remote_client.py:16` | Médio — sem verificação de integridade dos modelos locais Ollama |
| **LLM05** — Data and Model Poisoning | Modelos locais Ollama vêm de registry externo; sem fine-tuning próprio, sem RAG persistente hoje | Ausência de RAG persistente = sem vetor de envenenamento de conhecimento; escolha do modelo é declarada no registro (`record["model"]`, `record["backend"]`), portanto trocas silenciosas quebram o hash chain do log | `src/asus_theye/llm/audited.py:71` | Baixo enquanto não houver fine-tuning ou índice vetorial em produção |
| **LLM06** — Unbounded Consumption | Chamadas remotas podem incorrer em custo; um prompt malformado pode disparar loop de tokens | Sem loops implícitos no código atual; `AuditedLocalLLM.chat` é single-shot; `dual.adjudicate` faz exatamente 2 chamadas por decisão; registro grava `prompt_tokens` e `eval_tokens` para monitoramento | `src/asus_theye/llm/audited.py:78` | Médio — não há circuit-breaker por custo/rate no remoto |
| **LLM07** — Misinformation | Modelo pode inventar fonte, citação, número. Se essa saída virar claim de mercado, corrompe a corrente | Prompt do proposer instrui `UNKNOWN over guess` (regra 4 do AGENTS.md); challenger é adversarial (procura o que está errado, não confirma); discordância força `CONFLICTED`; classes de claim `FACT/DERIVED/INFERENCE/RECOMMENDATION/UNKNOWN/CONFLICTED/BLOCKED` são finitas e checadas | `src/asus_theye/llm/dual.py:32` | Baixo para o caminho auditado; **crítico** se alguém injetar saída de LLM não-auditada na emissão de mercado |
| **LLM08** — Hidden Context Exposure | System prompts, cadeia de conversação, contexto RAG podem vazar via jailbreak | Sistema prompts do proposer e do challenger estão **em código público e versionado** (nenhum segredo a proteger); `system_sha256` no log torna auditável qualquer mudança silenciosa | `src/asus_theye/llm/dual.py:35`; `src/asus_theye/llm/audited.py:72` | Baixo — política deliberada de não colocar segredo em system prompt |
| **LLM09** — Vector and Embedding Weaknesses | Nenhum índice vetorial em produção hoje | N/A no estado atual | — | Não aplicável enquanto não houver embeddings; se adicionar, releitura obrigatória |
| **LLM10** — Improper Output Handling | Saída do LLM pode ser markdown, JSON, ou string arbitrária que caia em renderer/executor a jusante | `dual.adjudicate` parseia como JSON estrito (levanta em prosa fora do objeto); nenhum caminho no repo passa saída de LLM para `eval`, `shell`, SQL, ou template server-side sem trip por revisão humana; dashboard não renderiza HTML de LLM | `src/asus_theye/llm/dual.py:1` | Baixo hoje; **médio** se surgir integração de tool ou export para app externa |

## Notas por risco onde há particularidade

### LLM01 + LLM07 — por que `dual` é a mitigação principal

A escolha arquitetural do repositório é rara e vale explicitar: quando os dois
modelos discordam sobre a substância, o resultado **não é resolvido** — vira
`CONFLICTED`. Um único modelo corrigindo a si mesmo não produz honestamente a
"melhor evidência contrária" que o `AGENTS.md` exige. A regra que faz isso
funcionar é que o `dual` **não elege vencedor**: discordância é sinal de
evidência fraca, não empate a ser desfeito. Essa é a mitigação real para
prompt injection e para alucinação — não um filtro de string.

### LLM02 — por que a corrente é segura mesmo com prompt público

O ledger recebe *hash* do prompt e da resposta, nunca o texto. Um adversário
com acesso ao worker público (`the-eye-public-verifier`) que hoje serve o
verificador não consegue reconstruir prompt algum a partir do log. A regra
está em `audited.py:70` e é o pilar do desenho "conteúdo secreto, prova
pública" descrito em `NOTICE` e no `THREAT_MODEL.md` (linha "AI/operator").

### LLM03 — o motivo do salto na edição 2026

A OWASP moveu *Excessive Agency* do 6º ao 3º lugar em 2026 porque agentes com
tool-calling autônomo saíram do laboratório. O THE EYE **hoje** não tem
tool-calling: o LLM propõe classes de claim, humanos e código determinístico
decidem consequências. Adicionar tool-calling — mesmo "só leitura" — exige
releitura formal deste documento e possivelmente um evento
`project.compliance` novo. Não é decisão que se toma em PR incremental.

### LLM04 — vale ler junto com `THREAT_MODEL.md`

A linha "Dependency/build attacker" do `THREAT_MODEL.md` já cobre o vetor;
este mapeamento apenas registra que a superfície LLM não adiciona SDK
próprio (fica em `urllib` da stdlib para OpenAI/Anthropic), o que reduz a
árvore de dependências transitivas comparado a puxar `openai==*` +
`anthropic==*`.

### LLM09 — declarar N/A é escolha, não esquecimento

Ausência de vector store é uma **decisão arquitetural** desta fase: RAG
persistente introduziria envenenamento de conhecimento (LLM05) e vazamento
por proximidade (LLM09). Se a Fase C ou D introduzir embeddings, este risco
deixa de ser N/A e passa a exigir isolamento por tenant, HMAC nas chaves de
vetor e uma política de rehidratação.

## Ponte com `THREAT_MODEL.md`

O modelo de ameaças geral já cobre a última linha da tabela — *"AI/operator →
CoT or sensitive tool output logged"* — e a controle é o mesmo aplicado aqui:
hash/redação, proibição explícita. Este documento é a **decomposição** dessa
linha nas dez categorias OWASP, para que auditores externos que trabalham com
o framework encontrem o mapeamento na linguagem que esperam.

## Referências

- OWASP GenAI Security Project — *OWASP Top 10 for LLM Applications 2026*:
  <https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/>
- Repositório da lista: <https://github.com/GenAI-Security-Project/GenAI-LLM-Top10>
- ADR local relevante: `docs/adr/ADR-001-off-chain-payloads.md` (regra que
  proíbe payload sensível no ledger)
- Documentos de segurança complementares neste diretório: `THREAT_MODEL.md`,
  `DATA_CLASSIFICATION.md`, `PSEUDONYMIZATION.md`, `LGPD_BLOCKCHAIN.md`.

## O que mudaria a conclusão deste documento

Seguindo a disciplina de evidência do `AGENTS.md`:

- **Tool-calling autônomo** no LLM → LLM03 passa de Baixo a Alto; releitura
  obrigatória.
- **RAG persistente ou fine-tuning** → LLM05 e LLM09 saem de N/A; exigem
  controles novos.
- **Saída de LLM alimentando emissão de mercado sem revisão humana** →
  LLM07 passa a Crítico; a doutrina do gerador determinístico precisa ser
  reafirmada por evento na corrente.
- **Nova política de logging** que grave prompt em claro → LLM02 volta de
  Médio a Alto; contradiz ADR-001.
