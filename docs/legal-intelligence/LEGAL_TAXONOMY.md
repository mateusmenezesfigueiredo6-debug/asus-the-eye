# Legal taxonomy

145 legal areas in 22 structural groups, generated verbatim from the master
mission's "Minimum domains and subdomains" list. Stable IDs (`legal_area_id`,
kebab-case) are the join key across the platform: audit events
(`legal_area_ids`), decision-context records, dashboards and routing.

Files:

- `data/legal-taxonomy/legal_areas.master.json` — source of truth (+ YAML mirror)
- `legal_area_relationships.json` — structural group membership only
- `legal_area_aliases.json` — high-confidence PT-BR aliases (seed, reviewed growth)
- `cnj_crosswalk.json` / `international_crosswalk.json` — status
  `pending_official_mapping`: entries come only from official published tables

Niches are **data, not apps**: every area is a row consumed by the same five
platform surfaces (audit-worker, dashboard, extract-decision, llm, verifier).
