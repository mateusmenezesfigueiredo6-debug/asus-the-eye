# Decision context — data quality report

Status: **initial — no production data ingested**. Generated at Phase G scaffold
creation (2026-08-02). This report must be regenerated on every ingestion cycle.

## Current state

| Dataset | Records | Sources verified | Duplicates | Missingness |
| --- | --- | --- | --- | --- |
| decision-makers | 0 | — | — | — |
| decision-bodies | 0 | — | — | — |
| assignment-rules | 0 | — | — | — |
| public-decisions | 0 | — | — | — |
| metrics | 0 | — | — | — |

## Quality gates for future ingestion

1. Every record must carry a `source_manifest` with official URL + SHA-256.
2. Duplicate detection by content hash before insert.
3. Missingness recorded per metric (`missingness.missing_count`), never silently
   dropped.
4. Sample size and statistical power evaluated before any pattern statement.
5. Concept drift note required when the period spans a legal or precedent change.

## Known limitations

- No ingestion pipeline exists yet; schemas only.
- Official-source availability varies by tribunal; coverage will be uneven and
  must be reported per body, never extrapolated.
