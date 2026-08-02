# Decision context — LGPD assessment (preliminary)

Status: **preliminary self-assessment — not a DPIA/RIPD, not legal advice, not
production approval**. A formal RIPD by privacy/legal professionals is a hard
gate before any production use (see DEPLOYMENT_GATES.md).

## Assessment summary

| Dimension | State | Evidence |
| --- | --- | --- |
| Minimization | Enforced structurally | `additionalProperties: false` in all 10 schemas; permitted-field allowlists |
| Prohibited attributes | Structurally absent | No schema field for political/ideological/health/etc.; test-enforced |
| Legal basis mapping | Modeled, unfilled | `data-protection.schema.json` requires basis per operation |
| Retention | Modeled | `retention_policy_id` links to D1 `retention_policies` |
| Correction/contestation | Modeled | `correction_status` + required processes |
| Human review | Enforced structurally | `human_review.required: const true` on person-referencing records |
| Auditability | Available | staging audit worker (hash chain live) |
| Fairness audit | Not started | required before production |
| DPIA/RIPD | Not started | required before production |

## Risk notes (claim class: INFERENCE)

- Aggregated metrics about a named adjudicator remain personal data under LGPD
  even when sourced from public decisions; publicity of source does not waive
  purpose limitation (LGPD art. 7 §3 requires purpose compatibility).
- The highest residual risk is re-identification/aggregation harm: many lawful
  facts combined can approximate a prohibited profile. Mitigation: allowlisted
  fields only, no free-form person-level notes fields in any schema.
- Conflict alerts touching a person require the strictest handling: state machine
  forbids automatic conclusions; human legal review is mandatory.

## What would change this assessment

A formal RIPD, a balancing test per operation, or an ANPD guidance update on
public-data processing would supersede every conclusion above.
