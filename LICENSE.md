# Licenciamento

Este projeto usa licencas distintas para codigo e para dados, porque licenca de
software nao cobre bem base de dados curada.

## Codigo — AGPL-3.0

Todo o codigo (`src/`, `apps/`, `tests/`, `scripts/`, `bin/`, `contracts/`) esta
sob GNU Affero General Public License v3.0. Texto integral em `LICENSE`.

O que isso significa na pratica:

- qualquer pessoa pode usar, estudar, modificar e redistribuir;
- quem **oferecer este software como servico pela rede** precisa disponibilizar
  o codigo-fonte modificado a quem usa o servico;
- e a clausula que separa a AGPL das demais: fechar a plataforma e vende-la como
  SaaS proprietario nao e permitido.

Copyright (c) 2026 Mateus Menezes Figueiredo. O titular detem a totalidade dos
direitos e pode conceder licenca comercial em separado.

## Dados — licenca restrita

O diretorio `data/` NAO esta sob AGPL. Ver `data/LICENSE`.

A taxonomia de 145 areas juridicas, os 354 aliases PT-BR e as series historicas
sao trabalho de curadoria, nao codigo. Estao disponiveis para leitura,
verificacao e auditoria do funcionamento da plataforma, e nao para extracao,
redistribuicao ou uso em produto derivado sem autorizacao escrita.

## Medicoes geradas — `reports/`

As medicoes versionadas em `reports/` (registro de mercados, resolucoes contra
fonte oficial, eventos selados da cadeia auditavel, ancoras e snapshots) sao
obra do titular: Copyright (c) 2026 Mateus Menezes Figueiredo. Ficam
disponiveis para leitura e verificacao independente — e a verificabilidade e o
proposito delas —, mas extracao ou redistribuicao como dataset segue a mesma
regra de `data/`: exige autorizacao escrita do titular. Os fatos subjacentes
(IPCA publicado pelo BCB, votacoes da Camara) sao publicos por definicao;
esta clausula cobre a MEDICAO — a serie, o erro calculado e a curadoria.

## Por que nao MIT

O projeto usou MIT ate 05/08/2026. MIT permite fechar o codigo e revender sem
devolver nada, o que e incompativel com atrair colaborador mantendo o valor da
plataforma. A troca foi feita enquanto havia autor unico, sem necessidade de
concordancia de terceiros.

## Licenca comercial

Quem precisar de termos diferentes dos da AGPL — uso em produto proprietario,
por exemplo — deve tratar diretamente com o titular.
