"""Shared fixtures for Phase 1 v2 tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_run_dir(tmp_path: Path) -> Path:
    """A mission-run directory under pytest's tmp_path."""
    run_dir = tmp_path / "runs" / "test-mission"
    run_dir.mkdir(parents=True)
    return run_dir
