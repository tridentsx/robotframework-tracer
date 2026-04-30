"""Shared fixtures for unit tests.

Patches OTel log exporters to prevent background threads
from attempting real network connections during tests.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _patch_otel_exporters(monkeypatch):
    """Auto-patch log exporters to no-ops for all unit tests."""
    mock_log_exporter = MagicMock()

    monkeypatch.setattr(
        "robotframework_tracer.listener.OTLPLogExporter",
        lambda **kwargs: mock_log_exporter,
    )
