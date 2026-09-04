# Estado atual do motor — THE EYE OF GOD

**Retrato de 02/09/2026.** O documento anterior (02/08/2026) descrevia um motor
de benchmark quântico sem domínio de mercados; ficou um mês desatualizado e
uma auditoria o apontou como dívida. Este substitui aquele, com a regra de
sempre: o que está aqui foi MEDIDO na data do retrato — não é promessa.

## O fluxo, ponta a ponta

```
1. FONTES ──────────────────────────────────────────────────────────────
   BCB (IPCA/Selic/PTAX/SGS) · SIDRA · ANEEL · ANP · ONS (carga+EAR) ·
   TSE · Wikipédia (atenção, trava de identidade) · GDELT (tom) ·
   CISA KEV (cyber) · FAO FFPI (commodities) · ClinicalTrials (biotec) ·
   Netflix Top10 (cultura) · World Bank · Focus/Olinda (vintage DATADO
   por corte) · source_graph (Crossref/arXiv/GitHub)
                     │  net/http (max_bytes obrigatório, testado)
                     ▼
2. ARMAZENAMENTO ───────────────────────────────────────────────────────
   reports/markets/*.json|jsonl sob CONTRATO v1 (esquema_store.py; tabela
   nova sem declarar = violação; a suíte valida o store REAL) · migrações
   documentadas (migrations/0002) · DuckDB como ponte de leitura
                     ▼
3. SINAIS ──────────────────────────────────────────────────────────────
   sinais_ipca (Focus 20 + IPCA-15 10) · sinais_noticia (GDELT; cobertura
   hoje INSUFICIENTE — 0-2 eventos/dia BR, diagnóstico em curso) ·
   vintage_focus (série reconstruída do arquivo datado: 27 meses) ·
   frescor · expectativas
                     ▼
4. MODELOS ─────────────────────────────────────────────────────────────
   WPAM (gerador; prior honesto, pesos com fonte) ·
   nowcast ridge R2 = DESAFIANTE 0.2.0 no mlops, peso ZERO até a porta
   do spec (24m prospectivos + aprovação humana; relógio ligado por cron)
   — pareado MEDIDO: Brier 0,0575 vs Focus duro 0,2222 (18 meses) ·
   Modelo2026 eleitoral (encolhimento por ignorância, evidências com
   citação; importador: markets-eleitoral-preview, cron diário) ·
   ATLAS v0 (catálogo com hub/licença/versão; statsforecast:
   auto_arima 0,1667 · ets/theta 0,3333 nos mesmos folds)
                     ▼
5. CALIBRAÇÃO/INCERTEZA ────────────────────────────────────────────────
   calibracao (Murphy) · conformal + conformal_adaptativo ·
   calibracao_uf (297 pontos, TSE 2022: erro médio 2,38pp, 95% ±17,82pp)
                     ▼
6. VERIFICAÇÃO ─────────────────────────────────────────────────────────
   scoring (Brier/skill) · verificacao (Murphy fecha em 1e-9) ·
   consenso (baseline Focus) · comparador (Chaox: comparador, NUNCA
   fonte — trava de família proibida testada na suíte)
                     ▼
7. AUDITORIA ───────────────────────────────────────────────────────────
   corrente hash (schema 37 campos, RFC 8785, merkle, âncora, redator
   LGPD que RECUSA campo sensível) — 220+ elos íntegros; QR de
   titularidade selado (elo 211: nome + commitment HMAC, nunca o CPF)
                     ▼
8. SAÍDAS ──────────────────────────────────────────────────────────────
   CLI 40+ subcomandos · site (painel-mercados, 370+ mercados, loopback,
   sigilo em 3 camadas + SIGILO vale para toda área) · resolvedor do
   site (cron 3×/dia; liquidação real: CAMBIO-D 01/09 contra a PTAX) ·
   dashboard · relatórios · verificador público de recibos
```

## As regras que o código IMPÕE (não só promete)

- **UNKNOWN over guess** — ausência nunca vira zero nem desfecho; pendente
  fica pendente com motivo contado.
- **Peso sem fonte não entra** (`Evidencia` recusa; a porta do nowcast é de
  calendário + aprovação humana, não de backtest).
- **Contrato emitido não se reescreve** — o trigger recusou o próprio autor
  em 01/09; a correção textual vale para a emissão seguinte.
- **Selagem por conteúdo** — mesma identidade com conteúdo diferente é
  adulteração e a corrente recusa (aconteceu, funcionou, está no log).
- **Fonte proibida cobre a família** — a reintrodução de dado Kalshi por um
  ledger de sessão foi detectada pela suíte e removida da história no mesmo
  dia (exposição externa: zero; origin dezenas de commits atrás, sem push).

## Dívidas conhecidas (com dono)

- GDELT: cobertura BR insuficiente — diagnóstico da resiliência em curso.
- `lawful_basis_reference` nos elos: placeholder `REQUIRES_LEGAL_VALIDATION`
  (item de conformidade).
- Porta do nowcast: fecha por calendário (vintage prospectivo desde
  01/09/2026) + decisão do titular.
- Dinheiro real: inexistente por desenho em TODAS as áreas (SEM_OUTORGA);
  cyber e FAO liberados só para DEMONSTRAÇÃO por parecer de 02/09.
