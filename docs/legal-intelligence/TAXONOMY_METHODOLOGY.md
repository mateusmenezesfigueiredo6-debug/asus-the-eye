# Taxonomy methodology

1. **Source**: the numbered list in `prompts/THE_EYE_MASTER_MISSION.md` is
   parsed mechanically (regex on numbered lines). No area added or removed.
2. **IDs**: deterministic kebab-case slug of the English name, unique-checked.
3. **Groups**: contiguous ranges of the source list; structural, not doctrinal.
4. **Aliases**: only unambiguous PT-BR names ship in the seed; every addition is
   reviewed. Ambiguous terms stay out (UNKNOWN over guess).
5. **Crosswalks (CNJ, international)**: empty by design until mapped from the
   official tables; the policy field in each file states this. Never inferred.
6. **Change control**: taxonomy_version bumps with any change; tests pin the
   area count, ID uniqueness and crosswalk honesty policy.
