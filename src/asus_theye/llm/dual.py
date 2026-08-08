"""Two-model adjudication: one model proposes, a different one tries to refute.

This is the project's own evidence policy expressed as code. ``AGENTS.md``
requires every material conclusion to carry a question, a claim class, primary
evidence, *best contrary evidence*, a justification, confidence, limitations,
and what would change the conclusion. A single model grading its own homework
cannot honestly produce the "best contrary evidence" line — so a second,
different model is asked to attack the first one's answer.

The rule that makes this worth doing: when the two disagree on the substance,
the result is downgraded to ``CONFLICTED`` rather than resolved by picking a
winner. A disagreement between models is a signal that the evidence is thin,
not a tie to be broken. Confidence is likewise capped by the challenger.

Both calls go through ``AuditedLocalLLM``, so each leg lands in the
hash-chained audit log with its own provider recorded.
"""

from __future__ import annotations

import json
import re
from typing import Any

from asus_theye.llm.audited import AuditedLocalLLM
from asus_theye.llm.remote_client import build_client

CLAIM_CLASSES = ("FACT", "DERIVED", "INFERENCE", "RECOMMENDATION", "UNKNOWN", "CONFLICTED", "BLOCKED")

PROPOSER_SYSTEM = """You answer as an evidence-bound analyst.

Never invent a source, citation, URL, author, date, case, statistic, test, or
result. When the evidence is insufficient, classify the claim as UNKNOWN — that
is a correct answer, not a failure.

Reply with JSON only, no prose outside it, no code fences:
{"claim": str,
 "claim_class": one of FACT|DERIVED|INFERENCE|RECOMMENDATION|UNKNOWN|BLOCKED,
 "primary_evidence": [str],
 "justification": str,
 "confidence": float between 0 and 1,
 "limitations": [str],
 "what_would_change_it": str}"""

CHALLENGER_SYSTEM = """You are the adversary. Another model produced a claim.
Your job is to find what is wrong with it, not to agree with it.

Look for: unsupported leaps, invented or unverifiable sources, a claim class
that overstates the evidence (calling an INFERENCE a FACT), overconfidence, and
missing limitations. If the claim genuinely holds, say so — but only after
producing the strongest contrary evidence you can.

Never invent a source, citation, URL, author, date, case, statistic, test, or
result to manufacture a disagreement.

Reply with JSON only, no prose outside it, no code fences:
{"agrees_with_claim": bool,
 "contrary_evidence": [str],
 "claim_class": one of FACT|DERIVED|INFERENCE|RECOMMENDATION|UNKNOWN|BLOCKED,
 "confidence": float between 0 and 1,
 "divergences": [str],
 "critique": str}"""


class DualModelError(RuntimeError):
    """A leg of the adjudication failed or returned unusable output."""


def _extract_json(text: str) -> dict[str, Any]:
    """Parse the model's JSON, tolerating code fences and surrounding prose."""
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        brace = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not brace:
            raise DualModelError(f"model did not return JSON: {text[:200]!r}") from None
        try:
            parsed = json.loads(brace.group(0))
        except json.JSONDecodeError as error:
            raise DualModelError(f"model returned malformed JSON: {text[:200]!r}") from error
    if not isinstance(parsed, dict):
        raise DualModelError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed


def _normalize_class(value: Any) -> str:
    """Map a model's claim class onto the allowed set; anything odd is UNKNOWN."""
    candidate = str(value or "").strip().upper()
    return candidate if candidate in CLAIM_CLASSES else "UNKNOWN"


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, confidence))


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def adjudicate(
    question: str,
    proposer: str = "openai",
    challenger: str = "anthropic",
    proposer_model: str | None = None,
    challenger_model: str | None = None,
    temperature: float = 0.2,
    ledger_url: str | None = None,
) -> dict[str, Any]:
    """Run the propose/refute pair and return one auditable claim record.

    ``proposer`` and ``challenger`` are provider names: local, openai, or
    anthropic. Remote providers require ``THE_EYE_REMOTE_LLM=1``.
    """
    if proposer == challenger and proposer_model == challenger_model:
        raise DualModelError(
            "proposer and challenger are the same model; a model cannot adversarially "
            "review itself — pick two different providers or two different models"
        )

    proposer_llm = AuditedLocalLLM(client=build_client(proposer, proposer_model), ledger_url=ledger_url)
    proposal_call = proposer_llm.chat(question, system=PROPOSER_SYSTEM, temperature=temperature)
    proposal = _extract_json(proposal_call["content"])

    claim = str(proposal.get("claim", "")).strip()
    if not claim:
        raise DualModelError("proposer returned an empty claim")

    challenge_prompt = (
        f"Question under review:\n{question}\n\n"
        f"Claim to attack:\n{claim}\n\n"
        f"Claim class asserted: {_normalize_class(proposal.get('claim_class'))}\n"
        f"Confidence asserted: {_normalize_confidence(proposal.get('confidence'))}\n"
        f"Evidence offered:\n{json.dumps(_as_list(proposal.get('primary_evidence')), ensure_ascii=False, indent=2)}\n"
        f"Limitations acknowledged:\n{json.dumps(_as_list(proposal.get('limitations')), ensure_ascii=False, indent=2)}"
    )
    challenger_llm = AuditedLocalLLM(client=build_client(challenger, challenger_model), ledger_url=ledger_url)
    challenge_call = challenger_llm.chat(challenge_prompt, system=CHALLENGER_SYSTEM, temperature=temperature)
    challenge = _extract_json(challenge_call["content"])

    proposed_class = _normalize_class(proposal.get("claim_class"))
    challenged_class = _normalize_class(challenge.get("claim_class"))
    agrees = bool(challenge.get("agrees_with_claim"))
    divergences = _as_list(challenge.get("divergences"))

    # Disagreement is recorded, never arbitrated: a split verdict means the
    # evidence is thin, so the claim is downgraded instead of a winner picked.
    if agrees and proposed_class == challenged_class:
        final_class = proposed_class
    else:
        final_class = "CONFLICTED"
        if proposed_class != challenged_class:
            divergences.append(f"claim class: proposer said {proposed_class}, challenger said {challenged_class}")

    # The challenger can only lower confidence, never raise it.
    final_confidence = min(
        _normalize_confidence(proposal.get("confidence")),
        _normalize_confidence(challenge.get("confidence")),
    )

    return {
        "question": question,
        "claim": claim,
        "claim_class": final_class,
        "primary_evidence": _as_list(proposal.get("primary_evidence")),
        "contrary_evidence": _as_list(challenge.get("contrary_evidence")),
        "justification": str(proposal.get("justification", "")),
        "critique": str(challenge.get("critique", "")),
        "confidence": final_confidence,
        "limitations": _as_list(proposal.get("limitations")),
        "what_would_change_it": str(proposal.get("what_would_change_it", "")),
        "agreement": agrees and proposed_class == challenged_class,
        "divergences": divergences,
        "proposer": {
            "provider": proposer,
            "model": proposal_call["audit_record"]["model"],
            "claim_class": proposed_class,
            "record_hash_sha256": proposal_call["audit_record"]["record_hash_sha256"],
        },
        "challenger": {
            "provider": challenger,
            "model": challenge_call["audit_record"]["model"],
            "claim_class": challenged_class,
            "record_hash_sha256": challenge_call["audit_record"]["record_hash_sha256"],
        },
    }
