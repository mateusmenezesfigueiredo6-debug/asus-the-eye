# Protocolo de lançamento — THE EYE

Como qualquer coisa sai daqui. Nenhum lançamento acontece por decisão de uma IA,
por pressa, ou porque "já estava funcionando". Cada classe abaixo tem gatilho,
evidência obrigatória e quem aprova.

Este protocolo é executável: `python3 scripts/release_check.py <classe>` roda as
checagens automáticas da classe e emite um **registro de lançamento** com hash,
que é ancorado no ledger como `release.checked`. O que não passa, não sobe.

## Princípio

> Reversível e fechado ⇒ pode fluir. Irreversível ou exposto ⇒ para e pede humano.

A trava (`scripts/publish_lock.py`) é o mecanismo; este documento é a regra que
diz quando a trava deve ser aberta — e por quem.

## Classes de lançamento

| Classe | O que é | Reversível? | Quem aprova | Senha? |
| --- | --- | --- | --- | --- |
| **L0 — Local** | Código na máquina, testes, benchmark, extrator | Sim | Ninguém (fluxo livre) | Não |
| **L1 — Interno** | Commit + push para repo privado | Sim (revert) | Você, tacitamente | Não — só avisa |
| **L2 — Restrito** | Deploy do worker/dashboard atrás de token | Sim (rollback) | Você, explícito na sessão | Não — só avisa |
| **L3 — Testnet** | Ancoragem em blockchain de teste (Sepolia) | Não (bloco é permanente) | Você, explícito + registro | **Sim** |
| **L4 — Piloto** | Dados reais de terceiros, tenants limitados | Parcial | Você + DPO/jurídico | **Sim** |
| **L5 — Público** | Repo público, release, pacote, site | **Não** (cópias existem para sempre) | Você, com 24h de intervalo | **Sim** |
| **L6 — Mainnet** | Blockchain real, dinheiro real | **Não** | Governança formal | **Sim** |

## Portões por classe

### L0 / L1 — fluxo livre
- Testes verdes (`pytest`) e lint limpo (`ruff`).
- Nenhum segredo rastreado pelo git.
- Aviso na tela quando algo sai da máquina.

### L2 — restrito
Tudo de L1, mais:
- Todos os endpoints exigem token (`leak_check.py` camada 1 = 401 em tudo).
- Segredo no cofre do provedor, nunca no repositório.
- Rollback testado (`wrangler rollback` ou versão anterior identificada).

### L3 — testnet
Tudo de L2, mais:
- **Nada de dado pessoal on-chain.** Só raiz Merkle e hashes (ADR-001).
- Chave privada **nunca** tocada por IA: a transação é assinada por você.
- Contrato com testes passando e endereço/bytecode registrados antes.
- Registro do que ficará público para sempre: raiz, horário, endereço.
- Senha de publicação obrigatória.

### L4 — piloto
Tudo de L3, mais:
- RIPD/DPIA concluído por profissional humano.
- Base legal mapeada por operação; teste de balanceamento onde couber.
- Processo de correção e contestação operante.
- Plano de incidente e rollback com dados reais.

### L5 — público
Tudo de L4, mais:
- **Intervalo obrigatório de 24h** entre a decisão e a execução. Publicação
  não se faz no calor do momento — o que vira público não volta.
- Varredura de segredo em **todo o histórico**, não só no HEAD.
- Revisão do que o README e os relatórios expõem (URLs, IDs, nomes).
- Confirmação explícita de que a regra "repos sempre privados" está sendo
  conscientemente excepcionada.

### L6 — mainnet
Decisão de governança formal, separada, documentada. Nenhuma aprovação de
etapa anterior vale aqui.

## Condições de parada imediata

Vale para qualquer classe — se qualquer uma ocorrer, o lançamento para:

- dado pessoal em evento, manifesto ou calldata;
- raiz Merkle divergente ou buraco na sequência;
- endpoint respondendo sem token;
- segredo encontrado no histórico do git;
- teste vermelho ou lint sujo;
- signatário não aprovado ou chave em lugar errado;
- monitoramento desligado;
- impossibilidade de provar restauração.

## Sequência de execução

1. **Declarar a classe.** Diga explicitamente: "isto é um L3".
2. **Rodar** `python3 scripts/release_check.py L<n>`.
3. **Ler o resultado.** Falhou algo? Corrige e repete. Não existe "passa assim mesmo".
4. **Abrir a trava** (L3+): `python3 scripts/publish_lock.py unlock` — só você.
5. **Executar** o lançamento.
6. **Ancorar** o registro no ledger (`release.completed`).
7. **Reverificar**: `python3 scripts/leak_check.py` depois, não só antes.

## Papéis

- **Você** — única pessoa que abre a trava. Nenhuma IA tem a senha, por desenho.
- **A IA (eu)** — preparo, testo, documento, executo o que é reversível, e
  **paro** no que é irreversível. Se eu insistir para você abrir a trava com
  pressa, isso por si só é motivo de suspeita.
- **Profissional humano (DPO/jurídico)** — obrigatório em L4+. Nenhum código
  substitui.

## Registro

Todo lançamento a partir de L2 gera evento no ledger com: classe, commit,
resultado das checagens, hash do registro. O histórico de lançamentos fica
verificável pela mesma cadeia que audita o resto — inclusive os que falharam.
