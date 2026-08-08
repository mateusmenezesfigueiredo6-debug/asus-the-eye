# ADR-012 — Estrutura do repositório e ferramentas

**Status:** aceito · **Data:** 2026-08-03 · **Classe:** L1

## Contexto

O projeto cresceu para 12 subprojetos, 211 testes e 27 commits em uma sessão,
mas mantinha a estrutura do primeiro dia: pacote na raiz, 12 arquivos `.md`
soltos, sem licença, sem CI real, sem cobertura medida e sem trava pré-commit.
Lint e testes rodavam quando alguém lembrava.

Diagnóstico medido antes de mexer:

| Item | Antes |
| --- | --- |
| Arquivos `.md` na raiz | 12 |
| Licença | ausente |
| Cobertura | 67% (linha), nunca medida em CI |
| CI | 1 workflow local, sem testes |
| Lock de dependências | ausente |
| Pre-commit | ausente |
| Layout | flat (`asus_theye/` na raiz) |

## Decisões

### 1. Licença

Adotada a MIT em 03/08/2026, por pedido explícito: permissiva, curta,
universalmente compreendida.

> **Superada em 05/08/2026.** O projeto passou para **AGPL-3.0-or-later**, e o
> diretório `data/` saiu para licença restrita própria. O raciocínio da troca
> está no [ADR-013](ADR-013-LICENCA-AGPL.md). Esta seção fica registrada como
> histórico: um ADR narra o que foi decidido *naquele momento* e é superado por
> outro, nunca reescrito para fingir que a decisão anterior não existiu.

### 2. Layout `src/` (recomendação da PyPA)

`asus_theye/` → `src/asus_theye/`.

O layout flat permite que `import asus_theye` pegue o diretório local em vez do
pacote instalado. Isso esconde erros de empacotamento: um módulo esquecido no
`packages.find` funciona no desenvolvimento e quebra na instalação. Com `src/`,
os testes rodam **contra o pacote instalado**, como o usuário final o receberá.

Custo pago: 37 caminhos atualizados em `projects.json`, oito `parents[2]` →
`parents[3]`, e referências em scripts e testes. Verificado pelos 211 testes,
pelo lint e pelo próprio painel — que voltou a medir 103/106 artefatos, prova de
que nenhum caminho ficou para trás.

Feito **agora** porque o custo cresce com o projeto: 12 subprojetos ainda é
barato; 30 não seria.

### 3. Raiz enxuta

12 → 5 arquivos `.md` na raiz. Ficam apenas os que alguém procura no primeiro
minuto: `README`, `AGENTS`, `CONTRIBUTING`, `SECURITY`, `RETOMADA`. O resto foi
para `docs/governance/`, `docs/audit/` e `docs/`.

Uma raiz poluída esconde o que importa — o leitor não sabe por onde começar.

### 4. `uv` como gerenciador, com fallback

10–100× mais rápido que pip e já padrão de fato em 2026. Mas o `Makefile` cai
para `python -m venv` + `pip` quando o `uv` não existe: **a ferramenta não pode
ser um pré-requisito para rodar o projeto.**

### 5. Cobertura com piso que só sobe

`fail_under = 65`, com branch coverage ligado. O número é o **real de hoje**
(65,91%), não uma meta aspiracional.

Quando a medição com branch revelou 64,53% — abaixo do piso — a resposta foi
escrever testes para `report.py` (27% → coberto) em vez de baixar o piso. Baixar
o piso para caber no resultado é a mesma família de erro que preencher uma lista
até a meta: adaptar a régua ao resultado.

**O piso nunca desce sem um ADR explicando por quê.**

### 6. `mypy` com adoção gradual

`continue-on-error: true` no CI e alvo `types` que não falha o build. Ligar
checagem estrita em 2.100 linhas existentes produziria centenas de erros que
ninguém leria — e um portão que todo mundo ignora é pior que nenhum portão.

A checagem existe, é visível, e aperta módulo a módulo.

### 7. Pre-commit com dois portões locais

Além de ruff, whitespace e detecção de chave privada, dois portões próprios:

- **`policy_gate`** — broadcast desligado, nenhum `.env` real, ABI de ancoragem
  estreita;
- **`no-secrets-tracked`** — nenhum arquivo de credencial rastreado.

E `no-commit-to-branch` em `main`: mudança entra por merge, não por empurrão.

### 8. CI em três frentes separadas

`qualidade` (lint, formato, tipos, testes, cobertura em três versões de Python),
`politica` (portões, cobertura de eventos, varredura de segredos no **histórico
completo**) e `integridade-dos-dados` (145 nichos, 19 categorias, 8 tiers, pesos
somando 1.0, crosswalks pendentes vazios, painel medindo sem erro).

Separadas de propósito: quando quebra, o nome do job já diz o que quebrou.

**Nenhum job tem credencial de deploy.** O CI verifica; publicar continua sendo
decisão humana atrás da senha.

## O que NÃO foi feito, e por quê

- **Consolidar as cinco cópias de `urllib`** — `batching.py` continua sem
  testes; a ordem correta (ADR-011) é testar primeiro, migrar depois.
- **`mypy --strict`** — ver decisão 6.
- **Remover `packages/`** — só tem `README`s hoje, mas são o contrato dos
  pacotes planejados. Diretório vazio com propósito documentado é melhor que
  apagar e esquecer.
- **Conventional commits automatizados** — a disciplina de mensagem já existe;
  automatizar agora seria cerimônia sem ganho.

## Consequências

- `make` sozinho lista tudo o que se pode fazer. Descobribilidade deixou de
  depender de alguém lembrar.
- O CI roda o que antes rodava por lembrança.
- Testes passam a exercitar o pacote instalado, não o diretório.
- A cobertura tem piso, e o piso é honesto.
