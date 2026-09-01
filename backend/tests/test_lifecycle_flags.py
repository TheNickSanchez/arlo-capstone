"""Lifecycle mode flag resolution (analysis-only vs beta-prod vs smoke)."""

from __future__ import annotations

from backend.app.domain.workflow_contracts import resolve_lifecycle_flags


def test_beta_prod_wins_over_analysis_only_and_disables_smoke() -> None:
    smoke, analysis, beta = resolve_lifecycle_flags(
        smoke_enabled=True, analysis_only=True, beta_prod=True
    )
    assert beta is True
    assert analysis is False
    assert smoke is False


def test_analysis_only_disables_smoke() -> None:
    smoke, analysis, beta = resolve_lifecycle_flags(
        smoke_enabled=True, analysis_only=True, beta_prod=False
    )
    assert analysis is True
    assert beta is False
    assert smoke is False


def test_default_path_keeps_smoke() -> None:
    smoke, analysis, beta = resolve_lifecycle_flags(
        smoke_enabled=True, analysis_only=False, beta_prod=False
    )
    assert smoke is True
    assert analysis is False
    assert beta is False
