# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""RFC 8785 JSON Canonicalization Scheme helpers.

The implementation is dependency-free and intentionally rejects values outside the
I-JSON domain (non-string keys, lone surrogates and non-finite numbers).
"""

from __future__ import annotations

import json
import math
from typing import Any


class CanonicalizationError(ValueError):
    """Value cannot be represented as RFC 8785 canonical JSON."""


def _string(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError("lone Unicode surrogate is not I-JSON") from exc
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _number(value: int | float) -> str:
    if isinstance(value, int):
        if abs(value) > 9_007_199_254_740_991:
            raise CanonicalizationError("integer exceeds interoperable IEEE-754 range")
        return str(value)
    if not math.isfinite(value):
        raise CanonicalizationError("non-finite number is not I-JSON")
    if value == 0:
        return "0"
    raw = repr(value).lower()
    mantissa, marker, exponent = raw.partition("e")
    if marker:
        exp = int(exponent)
        absolute = abs(value)
        if 1e-6 <= absolute < 1e21:
            whole, _, fraction = mantissa.partition(".")
            digits = whole.lstrip("-") + fraction
            decimal_at = 1 + exp
            sign = "-" if value < 0 else ""
            if decimal_at <= 0:
                return sign + "0." + ("0" * -decimal_at) + digits
            if decimal_at >= len(digits):
                return sign + digits + ("0" * (decimal_at - len(digits)))
            return sign + digits[:decimal_at] + "." + digits[decimal_at:]
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{'+' if exp >= 0 else ''}{exp}"
    if raw.endswith(".0"):
        return raw[:-2]
    return raw


def canonicalize(value: Any) -> str:
    """Return canonical JSON text; object keys are sorted by UTF-16 code units."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _number(value)
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonicalize(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("JSON object keys must be strings")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(f"{_string(key)}:{canonicalize(value[key])}" for key in keys) + "}"
    raise CanonicalizationError(f"unsupported JSON type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return canonicalize(value).encode("utf-8")
