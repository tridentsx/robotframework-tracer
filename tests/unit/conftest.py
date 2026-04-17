"""Shared fixtures for unit tests.

Patches OTel metric and log exporters to prevent background threads
from attempting real network connections during tests. Without this,
tests that create TracingListener instances without fully mocking
all providers will spawn retry threads that produce noisy stderr
output and can delay process exit.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _patch_otel_exporters(monkeypatch):
    """Auto-patch metric and log exporters to no-ops for all unit tests."""
    mock_metric_exporter = MagicMock()
    mock_log_exporter = MagicMock()
    mock_metric_reader = MagicMock()

    monkeypatch.setattr(
        "robotframework_tracer.listener.OTLPMetricExporter",
        lambda **kwargs: mock_metric_exporter,
    )
    monkeypatch.setattr(
        "robotframework_tracer.listener.PeriodicExportingMetricReader",
        lambda *args, **kwargs: mock_metric_reader,
    )
    monkeypatch.setattr(
        "robotframework_tracer.listener.OTLPLogExporter",
        lambda **kwargs: mock_log_exporter,
    )
