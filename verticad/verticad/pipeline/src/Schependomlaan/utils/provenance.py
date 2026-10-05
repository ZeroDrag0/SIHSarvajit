"""Provenance / data-status helpers shared by all stages."""
from __future__ import annotations

from typing import Any

# Allowed data-status vocabulary (never hide uncertainty).
STATUSES = ("authoritative", "derived", "inferred", "prototype", "unavailable", "unverified")


def provenance(
    *,
    source_dataset: str = "Schependomlaan",
    source_file: str | None = None,
    source_ifc_global_ids: list[str] | None = None,
    derivation_method: str,
    method_type: str | None = None,
    confidence: float | None = None,
    validation_state: str = "not_validated",
    coordinate_reference: dict[str, Any] | None = None,
    data_status: str = "derived",
    notes: list[str] | None = None,
) -> dict[str, Any]:
    if data_status not in STATUSES:
        raise ValueError(f"data_status must be one of {STATUSES}")
    return {
        "source_dataset": source_dataset,
        "source_file": source_file,
        "source_ifc_global_ids": list(source_ifc_global_ids or []),
        "derivation_method": derivation_method,
        "method_type": method_type,
        "confidence": confidence,
        "validation_state": validation_state,
        "coordinate_reference": coordinate_reference,
        "data_status": data_status,
        "notes": list(notes or []),
    }
