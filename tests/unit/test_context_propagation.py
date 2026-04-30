"""Tests for OTel context propagation fix.

Verifies that TracingListener correctly attaches/detaches spans in the
OTel context so that trace.get_current_span() and propagate.inject()
work from within keyword execution.
"""

from unittest.mock import Mock, patch

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from robotframework_tracer.listener import TracingListener


class _NoOpExporter(SpanExporter):
    """Exporter that discards spans — avoids network calls in tests."""

    def export(self, spans):
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def _make_listener():
    """Create a TracingListener with a no-op exporter (no network)."""
    with patch("robotframework_tracer.listener.HTTPExporter"):
        listener = TracingListener()
    # Replace the tracer with a real SDK tracer (no-op export)
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_NoOpExporter()))
    trace.set_tracer_provider(provider)
    listener.tracer = trace.get_tracer(__name__)
    return listener


def _mock_data(name="item", **kwargs):
    data = Mock()
    data.name = name
    data.source = kwargs.get("source", "/path/to/suite.robot")
    data.metadata = kwargs.get("metadata", {})
    data.tags = kwargs.get("tags", [])
    data.args = kwargs.get("args", [])
    data.type = kwargs.get("type", "KEYWORD")
    return data


def _mock_result(**kwargs):
    result = Mock()
    result.id = kwargs.get("id", "s1")
    result.status = kwargs.get("status", "PASS")
    result.starttime = None
    result.endtime = None
    result.elapsedtime = kwargs.get("elapsedtime", 100)
    result.message = kwargs.get("message", "")
    return result


class TestContextPropagation:
    """Verify spans are attached as current in the OTel context."""

    def test_start_suite_makes_span_current(self):
        """After start_suite, trace.get_current_span() returns the suite span."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())

        current = trace.get_current_span()
        assert current.is_recording()
        assert current is listener.span_stack[-1]

        # Cleanup
        listener.end_suite(_mock_data("Suite"), _mock_result())

    def test_start_test_makes_span_current(self):
        """After start_test, trace.get_current_span() returns the test span."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())

        current = trace.get_current_span()
        assert current.is_recording()
        assert current is listener.span_stack[-1]
        # Test span should differ from suite span
        assert current is not listener.span_stack[0]

        listener.end_test(_mock_data("Test"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())

    def test_start_keyword_makes_span_current(self):
        """After start_keyword, trace.get_current_span() returns the keyword span."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())
        listener.start_keyword(_mock_data("Keyword"), _mock_result())

        current = trace.get_current_span()
        assert current.is_recording()
        assert current is listener.span_stack[-1]

        listener.end_keyword(_mock_data("Keyword"), _mock_result())
        listener.end_test(_mock_data("Test"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())

    def test_end_keyword_restores_parent_context(self):
        """After end_keyword, current span reverts to the test span."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())
        test_span = listener.span_stack[-1]

        listener.start_keyword(_mock_data("Keyword"), _mock_result())
        listener.end_keyword(_mock_data("Keyword"), _mock_result())

        current = trace.get_current_span()
        assert current is test_span

        listener.end_test(_mock_data("Test"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())

    def test_end_test_restores_suite_context(self):
        """After end_test, current span reverts to the suite span."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        suite_span = listener.span_stack[-1]

        listener.start_test(_mock_data("Test"), _mock_result())
        listener.end_test(_mock_data("Test"), _mock_result())

        current = trace.get_current_span()
        assert current is suite_span

        listener.end_suite(_mock_data("Suite"), _mock_result())

    def test_end_suite_restores_empty_context(self):
        """After end_suite, current span is INVALID_SPAN (no active span)."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())

        current = trace.get_current_span()
        assert not current.is_recording()

    def test_nested_keywords_context_stack(self):
        """Nested keywords each become current, and unwind correctly."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())

        listener.start_keyword(_mock_data("Outer KW"), _mock_result())
        outer_kw = listener.span_stack[-1]

        listener.start_keyword(_mock_data("Inner KW"), _mock_result())
        inner_kw = listener.span_stack[-1]
        assert trace.get_current_span() is inner_kw

        listener.end_keyword(_mock_data("Inner KW"), _mock_result())
        assert trace.get_current_span() is outer_kw

        listener.end_keyword(_mock_data("Outer KW"), _mock_result())
        listener.end_test(_mock_data("Test"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())


class TestPropagateInject:
    """Verify propagate.inject() produces valid traceparent headers."""

    def test_inject_during_keyword(self):
        """propagate.inject() produces a traceparent during keyword execution."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())
        listener.start_keyword(_mock_data("KW"), _mock_result())

        headers = {}
        inject(headers)

        assert "traceparent" in headers
        parts = headers["traceparent"].split("-")
        assert len(parts) == 4
        assert parts[0] == "00"
        # trace_id must not be all zeros
        assert parts[1] != "0" * 32

        listener.end_keyword(_mock_data("KW"), _mock_result())
        listener.end_test(_mock_data("Test"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())

    def test_inject_reflects_current_keyword_span(self):
        """traceparent span_id matches the current keyword's span_id."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())
        listener.start_keyword(_mock_data("KW"), _mock_result())

        kw_span = listener.span_stack[-1]
        expected_span_id = format(kw_span.get_span_context().span_id, "016x")

        headers = {}
        inject(headers)
        actual_span_id = headers["traceparent"].split("-")[2]

        assert actual_span_id == expected_span_id

        listener.end_keyword(_mock_data("KW"), _mock_result())
        listener.end_test(_mock_data("Test"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())

    def test_inject_empty_after_close(self):
        """After close(), propagate.inject() produces no traceparent."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())
        listener.close()

        headers = {}
        inject(headers)
        # Should be empty or have an invalid (all-zero) trace
        tp = headers.get("traceparent", "")
        if tp:
            trace_id = tp.split("-")[1]
            assert trace_id == "0" * 32


class TestContextTokensCleanup:
    """Verify _context_tokens stays in sync with span_stack."""

    def test_tokens_empty_after_full_lifecycle(self):
        """After a complete suite/test/keyword lifecycle, no tokens remain."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())
        listener.start_keyword(_mock_data("KW"), _mock_result())
        listener.end_keyword(_mock_data("KW"), _mock_result())
        listener.end_test(_mock_data("Test"), _mock_result())
        listener.end_suite(_mock_data("Suite"), _mock_result())

        assert len(listener._context_tokens) == 0
        assert len(listener.span_stack) == 0

    def test_close_cleans_up_tokens(self):
        """close() detaches all remaining context tokens."""
        listener = _make_listener()
        listener.start_suite(_mock_data("Suite"), _mock_result())
        listener.start_test(_mock_data("Test"), _mock_result())
        listener.start_keyword(_mock_data("KW"), _mock_result())
        # Abrupt close without end_* calls
        listener.close()

        assert len(listener._context_tokens) == 0
        assert len(listener.span_stack) == 0
