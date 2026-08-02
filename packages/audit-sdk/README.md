# audit-sdk

Canonical implementation: `asus_theye.audit.sdk.AuditSDK`. Required entry points are
`record`, `recordMutation`, `recordAIExecution`, `recordSourceSnapshot`,
`recordHumanReview`, `verifyEvent`, `verifyResourceHistory` and `verifyBatch`.

Critical mutations use `recordMutation` and fail closed with `AuditUnavailableError`.
AI integrations hash redacted inputs, sources and outputs; log model/template IDs,
guardrail/evaluation results as metadata hashes; and must never record chain-of-thought.
