# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Decision-context intelligence (Phase G): schema-validated extraction."""

from asus_theye.decision_context.extractor import (
    DecisionExtractionError,
    extract_decision_fields,
    validate_against_schema,
)

__all__ = ["DecisionExtractionError", "extract_decision_fields", "validate_against_schema"]
