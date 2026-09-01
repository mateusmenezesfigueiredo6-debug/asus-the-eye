# 0002 — contrato do store de mercados, versão 1

Diferente da 0001 (SQL do ledger de auditoria), esta migração não cria tabela:
**declara o contrato v1 do store JSONL** que já existe em `reports/markets/` e
fixa as regras de evolução. O código-fonte do contrato é
`src/asus_theye/markets/esquema_store.py` (fonte única); este arquivo registra
a decisão e o procedimento de migração — o que um `.sql` faria para SQL.

## Decisão (F1, 01/09/2026)

- **JSONL continua canônico.** DuckDB (`markets/duckdb_source.py`) permanece
  ponte de leitura. Motivo: os writers (`live.py` e vizinhos) já garantem
  lock + ordem de escrita (registro antes do ledger), e a corrente selada em
  `eventos.jsonl` referencia o conteúdo como está — migrar o formato agora
  seria risco sem ganho de leitura que a ponte não dê.
- `registro.json` carrega `"versao": 1`. Esse número é a versão DESTE contrato.

## Regras de evolução

1. **Acrescentar campo novo** a um writer: compatível, não exige migração —
   o contrato lista o núcleo que os readers consomem, não o teto.
2. **Remover ou renomear campo**, mudar tipo, ou criar tabela nova
   (`*.jsonl`/`*.json` na raiz do store): exige
   - nova entrada/alteração em `esquema_store.CAMPOS_POR_ARQUIVO`;
   - migração `NNNN_markets_store_v{N+1}.md` com o passo-a-passo de conversão
     dos dados existentes;
   - incremento de `VERSAO_DO_STORE` e do `"versao"` gravado;
   - a suíte (`tests/markets/test_esquema_store.py`) verde contra o store real.
3. **A corrente não se reescreve.** Se uma migração alterar linhas que já foram
   selegadas em `eventos.jsonl`, o evento de migração entra na corrente
   (novo elo), nunca se edita elo antigo — mesma regra de sempre.

## Verificação

```
.venv/bin/python -c "from asus_theye.markets.esquema_store import validar_store; print(validar_store() or 'store íntegro')"
```
