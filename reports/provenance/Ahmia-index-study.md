# Proveniência — Ahmia index (estudo de arquitetura)

Registro de estudo de projeto de terceiro, conforme a política de licenças do
projeto. Diferente de SocialPredict, Dask, MLflow, Kalshi, GDELT e WorldBank —
que informaram decisões de código já implementado — esta entrada registra um
**estudo de arquitetura sem uso implementado hoje**, e existe para carimbar a
data em que a ideia entrou no radar do titular.

| Campo | Valor |
| --- | --- |
| Componente do projeto | (nenhum ainda — estudo de referência) |
| Origem | Ahmia index — backend Elasticsearch do buscador Ahmia |
| Repositório | https://github.com/ahmia/ahmia-index |
| Commit upstream estudado | `9b99b6da0c35cbf81d5820a2fd05697ce3aca5c5` |
| Data do commit upstream | 2026-03-17 |
| Autor upstream | Juha Nurmi (juha.nurmi@ahmia.fi) |
| Licença de origem | **BSD-3-Clause** — © 2024 Juha Nurmi |
| Arquivos estudados | `README.md`, `mappings_tor.json`, `point_to_indexes.py`, `call_filtering.sh`, `setup_index.sh` |
| Data do estudo | 2026-08-23 |

## O que é o Ahmia index

Ahmia mantém um buscador de serviços `.onion` (Tor). O `ahmia-index` é a
camada de armazenamento: um schema Elasticsearch + scripts Python que recebem
documentos do crawler (`ahmia-crawler`) e servem o site (`ahmia-site`). Não
crawleia por si só — é o **cofre indexado** entre o coletor e a interface.

## Por que entrou no radar

Três padrões arquiteturais do Ahmia index conversam com problemas abertos do
THE EYE, mesmo que o domínio (indexação de darkweb) seja totalmente distinto
de mercados preditivos:

1. **Alias temporais para versionamento de índices**
   (`point_to_indexes.py` mantém um alias `latest-tor` apontando para o índice
   mensal vigente — `onions-2026-03`, `onions-2026-04`…). Isso é análogo ao
   que o THE EYE resolve hoje ad hoc para snapshots de fontes (Selic, PTAX,
   Focus). Vale estudar como padrão de "índice congelado por período,
   ponteiro móvel para a versão viva".

2. **Curadoria por filtragem automática de abuso**
   (`call_filtering.sh` + cron a cada hora, retira do índice conteúdo que
   viola políticas). Não é o problema do THE EYE, mas é um exemplo concreto
   e testado de **política declarada como código**, executada como job,
   sobre um índice imutável a jusante — padrão que o THE EYE pode adotar
   para hard-veto de fontes ("nunca aceitar sinal com origem em X", auditável
   como diff no índice).

3. **Separação de três camadas** (crawler ↔ index ↔ site). Documenta com
   clareza que a fronteira entre "quem coleta", "quem armazena e mantém
   invariantes de schema" e "quem serve" é uma decisão explícita, não um
   detalhe. Espelha `source_graph/paralelo.py` (coletor), `evidence/` (índice
   e proveniência) e o painel `/evidencia` (serviço) — sem que exista dívida
   arquitetural entre eles.

## O que NÃO foi (e não pode ser) copiado

- **Nenhum código Python, shell ou JSON do Ahmia foi importado, adaptado ou
  vendorado.** Esta entrada não altera nenhum arquivo em `src/`.
- **Nenhuma parte do índice Ahmia é consultada** pelo THE EYE em tempo de
  execução ou em testes. Não há dependência de runtime, de build, nem de
  dev.
- **O nome "Ahmia" NÃO é usado para promover** o THE EYE nem qualquer
  produto derivado — restrição explícita da cláusula 3 da BSD-3-Clause do
  Ahmia. A menção aparece apenas em registros técnicos (este arquivo, NOTICE)
  e em atribuição de estudo, nunca em comunicação de marketing.

## Situação de licença

- Código do THE EYE: AGPL-3.0-or-later (© 2026 Mateus Menezes Figueiredo).
- Projeto estudado: BSD-3-Clause (© 2024 Juha Nurmi). A BSD-3 permite
  incorporar código em obra sob AGPL preservando o aviso de copyright; **como
  nada foi copiado hoje**, a única obrigação cumprida aqui é o crédito
  técnico e a proibição de uso do nome do autor/projeto para promoção
  (cláusula 3), respeitada.
- Se no futuro alguma ideia estudada aqui virar código no THE EYE, uma nova
  entrada de proveniência será escrita para o componente específico, com o
  commit upstream de referência e o trecho de licença aplicável.

## Fronteira de titularidade

Esta entrada é obra do titular do THE EYE (registro de estudo), sob AGPL-3.0,
selada na corrente auditável com a data acima. Ela **atesta que o estudo
aconteceu em 2026-08-23** e que **nenhum código foi absorvido nessa data** —
prova negativa útil se a incorporação real acontecer mais tarde e alguém
questionar cronologia.

---

© 2026 Mateus Menezes Figueiredo — o projeto ASUS THE EYE é AGPL-3.0-or-later;
este registro descreve estudo de obra de terceiro sob BSD-3-Clause, cuja
titularidade permanece de Juha Nurmi.
