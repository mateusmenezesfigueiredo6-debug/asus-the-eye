# ASUS + THE EYE - Unified Master Mission

Read `AGENTS.md` in full before doing anything. Inspect the repository before
creating new architecture. Reuse existing components and avoid a second nested
monorepo.

## Mission

Consolidate the entire ASUS + THE EYE program into one high-end, evidence-first,
privacy-by-design, legally responsible, auditable platform. Work autonomously and
locally. Research current facts with live search, cite primary sources, answer the
questions you formulate, search for contrary evidence, implement safe components,
test them, and revise the work before concluding.

The program includes:

1. legal-intelligence source graph;
2. comprehensive and versioned legal taxonomy;
3. ranking and monitoring methodology for universities, people, firms, chambers,
   courts, regulators, publications, datasets, and news sources;
4. legal case analysis and process-management matrices;
5. contract generation in three controlled versions;
6. arbitration, mediation, dispute boards, and sports dispute resolution;
7. sports law, games, betting, esports, and integrity;
8. institutional and jurisprudential decision-context intelligence;
9. Cloudflare-oriented data and event architecture;
10. append-only audit ledger;
11. canonical hashing, hash chains, Merkle proofs, and blockchain anchoring;
12. verifiable AI execution records and mandatory human legal review;
13. security, LGPD, threat modeling, incident response, and governance;
14. diagrams, tests, migration models, CI checks, and implementation roadmap.

## Non-negotiable restrictions

Do not deploy, push, publish, broadcast blockchain transactions, modify Cloudflare
or another external service, install globally, use sudo, read credentials, inspect
`.env`, access `chaves`, use leaked credentials, create costs, or delete user data.

Cloudflare MCP may be inspected and used only for read-only metadata if already
authenticated and if the tool operation is demonstrably non-mutating. Otherwise,
create local adapters and mocks.

## Phase A - repository inspection and consolidation

1. Map the current repository, manifests, tests, architecture, documentation,
   existing agents, Cloudflare components, audit components, legal modules, and
   duplicated work.
2. Create:
   - `docs/architecture/CURRENT_STATE.md`;
   - `docs/architecture/GAP_ANALYSIS.md`;
   - `docs/architecture/MASTER_ARCHITECTURE.md`;
   - `docs/architecture/IMPLEMENTATION_ROADMAP.md`;
   - `docs/architecture/DEPLOYMENT_GATES.md`.
3. Preserve user work. Do not commit.

## Phase B - comprehensive legal taxonomy

Create a hierarchical, multilingual, versioned, extensible taxonomy with stable
IDs, aliases, broader/narrower/related relationships, jurisdictions, official
sources, regulators, courts, CNJ crosswalks, temporal validity, sensitivity,
review requirements, and audit references.

Minimum domains and subdomains:

1. Constitutional and constitutional procedure.
2. Administrative and public service.
3. Regulatory.
4. Public procurement and public contracts.
5. Concessions, PPPs, privatization, and infrastructure.
6. Public finance, budgeting, fiscal responsibility, and public debt.
7. Tax.
8. Customs.
9. Civil law.
10. Obligations.
11. Contracts.
12. Civil liability and product liability.
13. Consumer.
14. Family.
15. Children and adolescents.
16. Elder law.
17. Succession, private client, and family offices.
18. Real estate.
19. Urban planning.
20. Registry and notarial law.
21. Business law.
22. Corporate law.
23. Governance.
24. M&A.
25. Startups.
26. Venture capital.
27. Private equity.
28. Banking.
29. Private financial law.
30. Fintech and payments.
31. Capital markets.
32. Asset management.
33. Insurance.
34. Reinsurance.
35. Private pensions.
36. Insolvency.
37. Judicial and extrajudicial restructuring.
38. Competition and antitrust.
39. International trade.
40. Sanctions, export controls, and foreign-investment screening.
41. Employment.
42. Collective labor and unions.
43. Social security.
44. Criminal law.
45. Criminal procedure.
46. Sentence enforcement.
47. Corporate criminal law.
48. Compliance.
49. Internal investigations.
50. AML, KYC, KYB, beneficial ownership, and asset recovery.
51. Civil procedure.
52. Precedents and repetitive litigation.
53. Collective actions and structural litigation.
54. Enforcement.
55. Jurimetrics, litigation analytics, and litigation finance.
56. Arbitration.
57. Mediation.
58. Conciliation.
59. Negotiation.
60. Dispute boards and adjudication.
61. Expert determination and neutral evaluation.
62. Online dispute resolution and dispute-system design.
63. Public international law.
64. Private international law.
65. International investment law.
66. Human rights.
67. Humanitarian law.
68. Migration, nationality, asylum, and refugees.
69. Health law.
70. Life sciences.
71. Pharmaceutical and medical devices.
72. Bioethics, genetics, reproductive medicine, end-of-life, and neurorights.
73. Education.
74. Science, research integrity, and technology transfer.
75. Environmental.
76. Climate.
77. ESG and business and human rights.
78. Animal law.
79. Electric power.
80. Renewables, hydrogen, storage, and nuclear.
81. Oil, gas, fuels, and biofuels.
82. Mining and critical minerals.
83. Water resources.
84. Agrarian.
85. Agribusiness.
86. Food, labeling, traceability, and food security.
87. Construction and engineering.
88. Aviation and drones.
89. Maritime and shipping.
90. Ports.
91. Rail.
92. Roads and automotive.
93. Transportation, logistics, and autonomous mobility.
94. Technology.
95. Software and SaaS.
96. Cloud and outsourcing.
97. Telecommunications and internet.
98. Data protection.
99. Privacy.
100. Cybersecurity and incident response.
101. Artificial intelligence.
102. Algorithmic governance and AI auditing.
103. Digital evidence and forensics.
104. Intellectual property.
105. Patents and utility models.
106. Trademarks, industrial designs, and geographical indications.
107. Copyright and neighboring rights.
108. Trade secrets and unfair competition.
109. Domain names and platform enforcement.
110. Media and press.
111. Entertainment, music, audiovisual, and streaming.
112. Advertising, influencers, and marketing.
113. Fashion law.
114. Luxury law.
115. Art, cultural heritage, provenance, restitution, and museums.
116. Sports law.
117. Sports arbitration.
118. Sports justice and disciplinary law.
119. Anti-doping.
120. Sports integrity and safeguarding.
121. Sports betting.
122. Match-fixing and competition manipulation.
123. Esports.
124. Games and virtual economies.
125. Gambling and lotteries.
126. Cryptoassets.
127. Blockchain and smart contracts.
128. Web3, DeFi, DAOs, NFTs, tokenization, and digital custody.
129. Electoral law.
130. Political parties and campaign finance.
131. Legislative process and legislative drafting.
132. Government relations, public policy, and lobbying.
133. Military law.
134. Defense, dual-use technology, and export control.
135. Public security, policing, surveillance, and use of force.
136. Air and space law, satellites, launches, orbital debris, and space resources.
137. Third sector.
138. Philanthropy, endowments, and impact investing.
139. Religious law and freedom of religion.
140. Professional ethics and legal responsibility.
141. Legal operations.
142. Legal management and knowledge management.
143. Access to justice, legal aid, and public defense.
144. Legal design, plain language, and accessible justice.
145. Auditable legal AI and computational law.

Required files:

- `data/legal-taxonomy/legal_areas.master.json`;
- `data/legal-taxonomy/legal_areas.master.yaml`;
- `data/legal-taxonomy/cnj_crosswalk.json`;
- `data/legal-taxonomy/international_crosswalk.json`;
- `data/legal-taxonomy/legal_area_aliases.json`;
- `data/legal-taxonomy/legal_area_relationships.json`;
- `docs/legal-intelligence/LEGAL_TAXONOMY.md`;
- `docs/legal-intelligence/TAXONOMY_METHODOLOGY.md`.

Do not claim that one taxonomy is universally official. Preserve provenance and
version each source independently.

## Phase C - source graph and qualified top lists

For each legal area and subarea, design a pipeline to discover and validate up to
100 qualified entities in each relevant category:

- universities;
- schools and departments;
- research centers;
- legal clinics;
- academics and researchers;
- practitioners;
- arbitrators and mediators;
- institutional authorities using only necessary public professional data;
- law firms and specialist boutiques;
- courts and tribunals;
- regulators and public bodies;
- arbitration and mediation institutions;
- sports tribunals and federations;
- journals, repositories, and working-paper series;
- professional associations and think tanks;
- official datasets and APIs;
- observatories;
- news portals, newsletters, and podcasts;
- conferences and research programs.

Never fill a list artificially to reach 100. Report actual qualified coverage.
Separate global, Brazil, jurisdictional, academic, professional, institutional,
emerging, and period-specific rankings.

Each ranking entry must include evidence, score components, confidence,
methodology version, source IDs, cut-off date, validation date, limitations,
conflicts of interest, and human-review status.

Suggested score dimensions:

- authority and verifiable reputation;
- specialization in the exact subarea;
- relevant research, decisions, matters, transactions, or policy impact;
- citations and documented impact;
- recency and continuity;
- methodology transparency;
- source accessibility and structured data;
- jurisdictional relevance.

Do not rank people primarily by social-media followers. Do not mix academics,
practitioners, judges, regulators, and policy officials in one list.

Create:

- `docs/legal-intelligence/RANKING_METHODOLOGY.md`;
- `docs/legal-intelligence/SOURCE_AUTHORITY_MODEL.md`;
- `docs/legal-intelligence/LEGAL_SOURCE_GRAPH.md`;
- `reports/LEGAL_SOURCE_COVERAGE.md`;
- `reports/SOURCE_GAPS.md`;
- `reports/RANKING_LIMITATIONS.md`.

## Phase D - arbitration, mediation, and dispute institutions

Create `dispute_resolution_institution` as its own entity type. Distinguish a
rule-making organization from an administering institution. Do not classify
UNCITRAL as an arbitration chamber.

Initial Brazilian institutional seed set:

- CAM-CCBC;
- CIESP/FIESP;
- CAMARB;
- CBMA;
- FGV Chamber;
- CAM AMCHAM;
- CAM/B3;
- ARBITAC;
- CAMFIEP;
- ICC Brazil.

Initial international seed set:

- ICC;
- LCIA;
- SIAC;
- HKIAC;
- ICDR/AAA;
- SCC;
- Swiss Arbitration Centre;
- DIAC;
- SCCA;
- ICSID;
- Permanent Court of Arbitration;
- WIPO Arbitration and Mediation Center;
- Court of Arbitration for Sport.

Institution records include official name, aliases, nature, seat, jurisdiction,
sector expertise, rules and versions, effective dates, model clauses, languages,
costs, emergency arbitration, expedited procedure, consolidation, multiple
parties, third-party funding, mediation, dispute boards, expert determination,
online filing, data protection, AI rules, neutral lists, disclosure standards,
statistics, published decisions, public accreditation, source manifest, and last
verification date.

Create:

- `docs/legal-intelligence/ARBITRATION_INSTITUTIONS.md`;
- `data/arbitration/institutions.json`;
- `data/arbitration/rulesets.json`;
- `reports/ARBITRATION_INSTITUTIONS_REPORT.md`.

## Phase E - sports law, betting, and esports

Build complete source and data models for:

- national and international sports governance;
- Lei Geral do Esporte and related legislation;
- clubs, leagues, federations, confederations, and SAF structures;
- athlete, coach, staff, agent, image-rights, sponsorship, licensing, naming-rights,
  broadcast, streaming, and merchandising contracts;
- transfers, registration, training compensation, solidarity mechanisms, and
  intermediaries;
- labor, tax, social-security, competition, consumer, data, biometric, IP, and
  human-rights issues;
- stadiums, arenas, events, security, fans, accessibility, and public financing;
- disciplinary proceedings and sports justice;
- STJD, TJDs, CNRD, CBMA, CAS, FIFA Football Tribunal, WADA, JAD/TJDA, and other
  sport-specific bodies;
- anti-doping;
- safeguarding and protection of minors;
- discrimination, racism, women's sport, and Paralympic sport;
- integrity, betting, AML, match-fixing, and manipulation;
- esports, publishers, teams, players, minors, streaming, cheating, digital
  doping, virtual items, loot boxes, and consumer protection.

Create:

- `data/sports-law/institutions.json`;
- `data/sports-law/regulations.json`;
- `data/sports-law/tribunals.json`;
- `data/sports-law/dispute-resolution.json`;
- `data/sports-law/integrity-sources.json`;
- `docs/legal-intelligence/SPORTS_LAW_SOURCE_MAP.md`;
- `reports/SPORTS_LAW_REPORT.md`.

## Phase F - twenty legal and business evaluation matrices

Implement or specify these matrices with schemas, required evidence, scoring
rules, limitations, and human-review gates:

1. Case intake and issue framing.
2. Issue-rule-fact-application-conclusion analysis.
3. Norm hierarchy, validity, temporal effect, revocation, and jurisdiction.
4. Precedent similarity, distinction, ratio, authority, and negative treatment.
5. Evidence, burden, admissibility, chain of custody, and evidentiary gaps.
6. Procedural routes and dispute-system design.
7. Seven-elements negotiation analysis.
8. Expected dispute value, probability, costs, time, execution, and residual risk.
9. Deadline calculation and critical path.
10. Stakeholder power-interest-legitimacy analysis.
11. Legal RACI.
12. Legal-process maturity.
13. Legal value chain.
14. Legal balanced scorecard.
15. Five-forces analysis for the legal or regulated context.
16. Requirement-clause-legal-basis-risk-evidence mapping.
17. Three-version contract comparison.
18. Breach-remedy-cure-termination-guarantee-enforcement matrix.
19. Due-diligence request list, issues list, risk, condition precedent, and owner.
20. Provenance, model, citations, confidence, audit receipt, and human review.

Required product capabilities:

### Case solution

Generate an executive summary, verified facts, disputed facts, issues, applicable
law, supporting and contrary precedents, evidence, gaps, procedural routes,
scenarios, cost, time, enforceability, uncertainty, recommendation, sources, and
audit receipt. Never state a probability without sample, period, method, and
limitations.

### Process management

Track phase, movements, owner, deadlines, tasks, documents, decisions, evidence,
costs, strategy, risks, settlement, appeal, closure, and post-case learning.

### Contracts in three versions

Produce:

1. protective version;
2. balanced version;
3. simplified/commercial version.

Each version requires a table of contents, risk table, footnotes, official-source
links, alternative clauses, open fields, comparison, and redline.

Create a separate legal-support file with summary of law, relevant full statutory
articles when lawful to reproduce, regulations, precedents, article-to-clause
mapping, applicability explanation, nullity/revision/resolution/termination
analysis, cut-off date, official links, and hashes. Require lawyer review before
signature or use.

### Deadlines

Record jurisdiction, tribunal, class, triggering event, governing rule, business
or calendar days, holidays, suspensions, calculated date, conservative date,
official source, responsible person, and human confirmation. No critical deadline
may depend solely on AI.

### Stakeholders and lawful open-source intelligence

Use only lawful, relevant, proportionate public data. Separate verified fact,
allegation, inference, and opinion. Do not create invasive dossiers.

## Phase G - Decision Context Intelligence

Create institutional and jurisprudential analysis for all relevant adjudicative
levels:

- state and federal trial courts;
- appellate courts;
- labor, electoral, military, and special courts;
- superior courts and STF;
- audit courts;
- CARF and tax administrative adjudication;
- CADE, CVM, CRSFN, agencies, and administrative councils;
- arbitration tribunals and ad hoc arbitrators;
- dispute boards;
- sports justice, STJD, TJDs, CNRD, CBMA, FIFA bodies, and CAS;
- professional disciplinary bodies where public and lawful.

Create distinct schemas for judge, appellate judge, justice, rapporteur, reviewer,
panel member, panel president, administrative adjudicator, regulatory decision
maker, tax council member, audit-court member, arbitrator, tribunal president,
dispute-board member, sports-justice member, and disciplinary-council member.
Mediators are not adjudicators.

Permitted fields are limited to necessary public professional data: official name,
normalized ID, role, institution, body, jurisdiction, level, competence, official
profile, official curriculum, appointment method, appointment or term dates,
active status, public decisions, jurisprudential areas, source manifest, last
verification, correction status, legal-basis reference, retention, and review.

Explicitly block political, ideological, religious, health, racial, sexual,
biometric, private-address, private-family, friendship-network, geolocation,
psychological, social-sentiment, or corruption-propensity profiling.

Allowed institutional context includes appointment process, public hearing,
mandate, competence, composition, presidency, changes in composition, assignment
rules, substitution, binding precedents, repetitive themes, IRDR, IAC, public
hearings, amici, official agenda, legislation, regulation, public policy, fiscal,
economic, and sectoral context. Do not turn the appointing authority into an
ideological label.

Metrics must include denominator, period, sample size, uncertainty, missingness,
and case-mix controls. Consider grant/denial/partial rates by motion, time to
decision, monocratic/collegiate rates, precedent citation, alignment, distinction,
dissent, concurrence, panel agreement, reconsideration, appeal, affirmance,
reversal, remand, publication, duplicates, data quality, statistical power,
confidence interval, and concept drift.

Control when possible for area, class, CNJ subject, motion, procedural phase,
period, legal change, precedent change, urgency, expert evidence, binding
precedent, and panel composition. Record unobserved factors.

Outputs must separate FACT, DERIVED_METRIC, INFERENCE, UNKNOWN, and PROHIBITED.
Use wording such as: "In comparable public decisions from the specified period and
sample, scenario X occurred with the reported frequency, subject to these
limitations." Never say that a person "will decide X".

Potential impediment or conflict states:

- no_public_indicator;
- potential_indicator;
- legal_review_required;
- confirmed_by_official_decision;
- resolved;
- insufficient_information.

Never declare bias or partiality automatically.

Create:

- `data/decision-context/decision-makers.schema.json`;
- `data/decision-context/decision-bodies.schema.json`;
- `data/decision-context/assignment-rules.schema.json`;
- `data/decision-context/public-decisions.schema.json`;
- `data/decision-context/jurisprudential-patterns.schema.json`;
- `data/decision-context/panel-dynamics.schema.json`;
- `data/decision-context/conflict-alerts.schema.json`;
- `data/decision-context/institutional-context.schema.json`;
- `data/decision-context/metrics.schema.json`;
- `data/decision-context/data-protection.schema.json`;
- `docs/security/DECISION_CONTEXT_LGPD.md`;
- `reports/decision-context/DATA_QUALITY_REPORT.md`;
- `reports/decision-context/LGPD_ASSESSMENT.md`.

Before production, require RIPD/DPIA, processing record, legal basis per operation,
balancing test where relevant, minimization, retention, correction, contestation,
human review, fairness audit, security review, incident plan, and legal/privacy
approval.

## Phase H - auditable data and blockchain architecture

Use an off-chain data/on-chain proof architecture:

Sources and user inputs
-> validation and classification
-> encrypted object storage
-> normalized metadata and search indexes
-> mandatory audit SDK
-> transactional outbox
-> queue
-> idempotent sequencer
-> append-only event ledger
-> deterministic Merkle batching
-> manifest and inclusion proofs
-> blockchain anchor adapter
-> verifier.

Create or adapt:

- `apps/audit-worker`;
- `apps/verifier`;
- `packages/audit-core`;
- `packages/audit-sdk`;
- `packages/canonical-json`;
- `packages/merkle`;
- `packages/event-schemas`;
- `contracts/audit-anchor`;
- `infra/cloudflare`;
- `migrations`;
- `tests/audit`.

### Audit event schema

Include at least:

- schema version;
- event ID;
- idempotency key;
- tenant ID;
- sequence;
- event type and action;
- occurred and recorded timestamps;
- pseudonymous actor and role;
- source system;
- pseudonymous resource and version;
- jurisdiction and legal areas;
- classification and retention policy;
- legal-basis reference;
- content and metadata SHA-256 hashes;
- previous event hash;
- event hash;
- correlation and causation IDs;
- AI provider, model, version, prompt-template version;
- source citation hashes;
- human-review status and pseudonymous reviewer;
- result, error code, service, and build version.

Do not include raw personal data in audit events.

### Canonicalization and hash chain

Implement RFC 8785-compatible canonical JSON where supported, deterministic
SHA-256 hashes, immutable sequence validation, previous-event hash verification,
and tamper tests.

### Merkle

Use deterministic event order by tenant and sequence, domain separation between
leaf and internal node, inclusion proofs, duplicate detection, manifests, and
golden vectors. A suitable local design is:

- leaf: `keccak256(0x00 || event_hash_sha256_bytes)`;
- internal node: `keccak256(0x01 || min(left,right) || max(left,right))`.

Record batch ID, tenant, schema, sequence range, count, root, previous root,
manifest hash, generation version, proof version, storage reference, network,
chain ID, contract, transaction, block, and confirmation status. Blockchain fields
remain null before anchoring.

### Ledger and outbox

Model:

- audit_events;
- audit_outbox;
- audit_batches;
- audit_batch_events;
- audit_anchors;
- audit_verification_runs;
- resource_versions;
- retention_policies;
- audit_failures.

Events are immutable. Corrections create new events. Deletion creates a tombstone.
Enforce tenant isolation, unique idempotency keys, unique tenant sequences,
reprocessing safety, failure records, and indexes.

### Cloudflare local templates only

Prepare non-deployed templates for:

- R2 event notifications;
- Queue `the-eye-audit-events`;
- DLQ `the-eye-audit-dlq`;
- consumer Worker;
- Durable Object or equivalent sequencer;
- alarms and batching;
- D1, R2, and Vectorize bindings;
- observability and reprocessing.

Assume at-least-once delivery and implement idempotency. Never use real IDs or
secrets in examples.

### Coverage manifest

Create `packages/event-schemas/audit-coverage-manifest.json` covering all critical
platform events, including authentication, users, roles, cases, processes,
movements, deadlines, tasks, documents, versions, authorized downloads, deletion,
contracts and all three versions, clauses, legal bases, laws, articles,
jurisprudence, precedents, theses, sources, source captures, universities,
experts, firms, news portals, stakeholders, OSINT, public corporate and fiscal
data, prompts, model calls, answers, citations, evaluations, guardrails, human
review, agents, tools, workflows, configuration, release, deploy, rollback,
Cloudflare services, index changes, Merkle batches, anchors, verification,
incidents, retention, anonymization, blocking, deletion, and audit export.

Create a test that fails when a declared event lacks schema, version,
classification, retention, handler or explicit planned state, and documentation.

### AI audit

Record purpose, pseudonymous case, model/version, prompt-template version,
parameters, input hashes, source hashes, citations, tools, response hash,
confidence, guardrails, evaluation, human-review need, reviewer decision,
corrected version, and limitations. Do not store private chain-of-thought.

### Solidity contract

Create a simple, non-upgradeable `TheEyeAuditAnchor.sol` compatible with the
current OpenZeppelin 5.x APIs available to the repository. Include minimal roles,
pause capability, duplicate-batch prevention, immutable roots, custom errors,
NatSpec, authorization tests, duplicate tests, pause tests, invalid-input tests,
event tests, and threat analysis.

Conceptual function:

`anchorBatch(bytes32 batchId, bytes32 merkleRoot, bytes32 manifestHash,
uint64 firstSequence, uint64 lastSequence, uint64 eventCount,
uint32 schemaVersion)`.

The contract must never accept arbitrary personal content.

### Networks

Templates only:

- local Anvil;
- Base Sepolia, chain ID 84532, staging only;
- Base Mainnet, chain ID 8453, disabled.

Default variables:

- `BLOCKCHAIN_BROADCAST_ENABLED=false`;
- `BLOCKCHAIN_NETWORK=local`;
- `BLOCKCHAIN_SIGNER_MODE=disabled`.

Do not place a private-key variable in `.env.example`. Production signing must be
documented for KMS, HSM, protected keystore, or equivalent controlled custody.

### Verifier

Build a local library and CLI that can recalculate event hashes, verify previous
hashes, verify a tenant/resource chain, derive leaves, validate Merkle proofs,
validate manifests, compare roots, and emit JSON and human-readable receipts with
states valid, invalid, incomplete, not_anchored, and anchor_unconfirmed.

## Phase I - privacy, security, and governance

Create:

- `docs/security/LGPD_BLOCKCHAIN.md`;
- `docs/security/DATA_CLASSIFICATION.md`;
- `docs/security/RETENTION_AND_DELETION.md`;
- `docs/security/PSEUDONYMIZATION.md`;
- `docs/security/THREAT_MODEL.md`;
- `docs/architecture/OPERATIONAL_RUNBOOK.md`;
- `docs/architecture/INCIDENT_RESPONSE.md`;
- `docs/architecture/AUDIT_VERIFICATION_GUIDE.md`.

Threat model must cover ledger tampering, reordering, deletion, duplication,
replay, signer compromise, malicious RPC, chain reorganization, queue failure,
abandoned DLQ, audit-SDK bypass, metadata or hash leakage, cross-tenant
correlation, administrator abuse, supply-chain compromise, clock skew,
canonicalization inconsistency, idempotency collision, retention failure, gas
cost, chain outage, delayed anchor, and corrupt proof bundle.

For each threat record asset, actor, vector, impact, prevention, detection,
response, and residual risk.

Create ADRs for off-chain content/on-chain proof, canonical format, append-only
ledger, Merkle batching, network selection, key management, LGPD and immutability,
transactional outbox, tenant isolation, and mandatory human legal review.

## Phase J - diagrams

Create Mermaid diagrams:

- `docs/architecture/PLATFORM_ARCHITECTURE.mmd`;
- `docs/architecture/AUDIT_SEQUENCE.mmd`;
- `docs/architecture/VERIFICATION_SEQUENCE.mmd`;
- `docs/architecture/LEGAL_SOURCE_GRAPH.mmd`;
- `docs/architecture/DECISION_CONTEXT.mmd`;
- `docs/architecture/THREAT_BOUNDARIES.mmd`.

Show off-chain data, indexes, ledger, Queue, DLQ, sequencer, batch, Merkle tree,
contract, verifier, trust boundaries, users, lawyers, human reviewers, and AI
agents.

## Phase K - tests and CI

Run or create, depending on the repository toolchain:

- unit tests;
- schema validation;
- canonicalization vectors;
- hash-chain and tamper tests;
- Merkle proof and batch-boundary tests;
- idempotency and duplicate-delivery tests;
- privacy and redaction tests;
- no-PII-on-chain tests;
- legal-taxonomy stable-ID and cycle tests;
- CNJ crosswalk tests;
- ranking evidence and no-artificial-fill tests;
- arbitration-institution type tests;
- sports-law coverage tests;
- decision-context sensitive-inference blocks;
- sample-size, missing-data, case-mix, drift, and Simpson's-paradox tests;
- conflict alert not becoming an accusation;
- contract tests when the local toolchain exists;
- lint, typecheck, and secret-pattern checks.

Prepare non-deployed CI for lint, typecheck, tests, secret scanning, dependency
review, CodeQL or equivalent, SBOM, event-coverage validation, and proof that chain
broadcast and mainnet remain disabled.

Do not install global tools. Mark unavailable tests SKIPPED and provide exact safe
commands for later.

## Phase L - authoritative references

Build `docs/architecture/REFERENCES.md` from official or primary sources. At a
minimum research and validate the current versions of:

- OpenAI Codex CLI, AGENTS.md, non-interactive mode, configuration, search, MCP,
  sandbox, and output schema;
- Cloudflare R2 event notifications, Queues, DLQ, Durable Objects, D1, R2,
  Vectorize, and Workers;
- JSON Canonicalization Scheme RFC 8785;
- Merkle transparency concepts such as RFC 6962;
- NIST SHA-256/FIPS 180-4;
- OpenZeppelin cryptography and access control;
- Base network information;
- LGPD and ANPD guidance;
- CNJ procedural taxonomies, DataJud, AI governance, and official judicial data;
- official court, legislative, regulatory, arbitration, sports, and academic
  sources relevant to the modules.

Do not copy extensive protected text. Record title, publisher, date, URL, access
date, authority tier, license/reuse notes, and content hash when locally stored.

## Autonomous evidence protocol

For each material conclusion, ask and answer:

1. What exact question is being answered?
2. What primary source supports it?
3. What is the strongest contrary source or counterexample?
4. Is the source current and authoritative?
5. Does the conclusion exceed the evidence?
6. Is there another plausible explanation?
7. What is the confidence and why?
8. What remains unknown?
9. What would change the conclusion?
10. What human approval is required?

Record concise answers, not private chain-of-thought.

## Completion criteria

A cycle is useful only if it produces repository artifacts, evidence, tests, or a
well-supported blocker. Do not mark complete merely because documents were
created.

Overall completion requires at least:

1. current-state and gap reports;
2. master architecture and roadmap;
3. comprehensive taxonomy schemas and initial validated records;
4. source and ranking methodology;
5. arbitration and sports-law models;
6. twenty evaluation matrices;
7. decision-context schemas and LGPD safeguards;
8. audit event schema and coverage manifest;
9. canonicalization, hash-chain, and Merkle tests;
10. ledger and outbox models;
11. local verifier;
12. local contract and tests when supported;
13. privacy documents and threat model;
14. diagrams;
15. evidence matrix and source log;
16. final report listing every limitation and next gate.

Do not claim that collection of all top-100 lists is complete unless every entry
has validated evidence. It is acceptable and required to report partial coverage.

## Final report

Create `reports/AUTONOMOUS_RESEARCH_REPORT.md` containing:

- executive summary;
- repository state;
- questions and answers;
- source register;
- contrary evidence;
- architecture;
- artifacts created and changed;
- tests, exit codes, and results;
- legal and privacy analysis;
- decision-context safeguards;
- blockchain design;
- data coverage;
- incomplete areas;
- critical risks;
- blocked actions;
- next 48 hours;
- next 30 days;
- staging gates;
- production gates;
- explicit confirmation of no deploy, no external write, no chain broadcast, and
  no secret written.

The final assistant message must satisfy the provided JSON Schema exactly.
