# Decision Context Intelligence — LGPD posture

Scope: the `data/decision-context/` schemas (Phase G). Status: **local prototype,
not approved for production**. Production requires the gates in
`data-protection.schema.json` (`approved_for_production` conditions) plus the
approvals listed in IMPLEMENTATION_ROADMAP.md.

## What this module is

Institutional and jurisprudential decision-context analysis over lawful public
data: who composes which adjudicative body, which official rules assign cases,
what public decisions exist, and what aggregate patterns those decisions show —
always with denominators, uncertainty, and limitations.

## What this module is structurally forbidden from being

Personal, psychological, ideological, political, religious, health, racial,
sexual, biometric or relational profiling of adjudicators. These attributes are
not optional-but-discouraged: they have no field in any schema, every schema sets
`additionalProperties: false`, and `tests/decision_context/` fails the build if a
prohibited attribute name ever appears in a schema.

Specific policy encodings:

| Policy rule | Encoding |
| --- | --- |
| "Never say a person will decide X" | patterns carry `claim_class` + template statement wording; no prediction field exists |
| "Never declare bias automatically" | `conflict-alerts.state` has no `bias_confirmed` value; `confirmed_by_official_decision` requires `official_decision_ref` |
| "Do not infer ideology from appointing authority" | `appointment_method` is a plain public fact; no ideology/alignment field exists anywhere |
| "Metrics need denominator, period, sample, uncertainty, missingness, case-mix" | all are `required` in `metrics.schema.json` |
| "Human review before use" | `human_review.required` is `const: true` on decision-makers, patterns and conflict alerts |
| "Mediators are not adjudicators" | excluded from the `role` enum; documented in schema description |
| "Corrections and contestation" | `correction_status` on records; `correction_process`/`contestation_process` required in processing records |

## Claim classes

`FACT` (official publication), `DERIVED_METRIC` (computed with denominators),
`INFERENCE` (marked, with contrary evidence), `UNKNOWN` (insufficient evidence),
`PROHIBITED` (refusal record — auditable, contentless).

## Data flow and audit

Every decision-context mutation is a critical mutation: it must pass through the
audit SDK / staging worker (`infra/cloudflare/staging`), producing a hash-chained
`audit_events` row. Evidence documents are content-addressed in R2. Personal data
never goes on-chain (ADR-001, ADR-007).

## Pre-production checklist (all pending)

- [ ] RIPD/DPIA completed and approved
- [ ] Processing record per operation (`data-protection.schema.json` instances)
- [ ] Legal basis mapped per operation; balancing test for legitimate interest
- [ ] Fairness audit
- [ ] Correction + contestation process operational
- [ ] DPO + legal + security + executive approval
