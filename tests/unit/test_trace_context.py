"""Tests for trace context propagation functionality."""

from unittest.mock import Mock, patch

from opentelemetry import trace

from robotframework_tracer.config import TracerConfig
from robotframework_tracer.listener import TracingListener


class TestTraceContextPropagation:
    """Test trace context propagation to Robot Framework variables."""

    def setup_method(self):
        """Set up test environment."""
        self.config = TracerConfig()

        # Mock the exporter to avoid network calls
        with patch("robotframework_tracer.listener.HTTPExporter") as mock_exporter:
            mock_exporter.return_value = Mock()
            self.listener = TracingListener()

    @patch("robotframework_tracer.listener.BUILTIN_AVAILABLE", True)
    @patch("robotframework_tracer.listener.BuiltIn")
    def test_set_trace_context_variables_with_builtin(self, mock_builtin_class):
        """Test setting trace context variables when BuiltIn is available."""
        # Setup mock BuiltIn
        mock_builtin = Mock()
        mock_builtin_class.return_value = mock_builtin

        # Create a test span
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_span"):
            # Call the method
            self.listener._set_trace_context_variables()

            # Verify BuiltIn.set_test_variable was called
            assert mock_builtin.set_test_variable.call_count >= 4

            # Check that trace variables were set
            calls = mock_builtin.set_test_variable.call_args_list
            call_names = [call[0][0] for call in calls]

            assert "${TRACE_HEADERS}" in call_names
            assert "${TRACE_ID}" in call_names
            assert "${SPAN_ID}" in call_names
            assert "${TRACEPARENT}" in call_names

    @patch("robotframework_tracer.listener.BUILTIN_AVAILABLE", False)
    def test_set_trace_context_variables_without_builtin(self):
        """Test that method returns early when BuiltIn is not available."""
        # Should not raise any exceptions
        self.listener._set_trace_context_variables()

    @patch("robotframework_tracer.listener.BUILTIN_AVAILABLE", True)
    @patch("robotframework_tracer.listener.BuiltIn")
    def test_trace_context_format(self, mock_builtin_class):
        """Test that trace context variables have correct format."""
        mock_builtin = Mock()
        mock_builtin_class.return_value = mock_builtin

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_span"):
            self.listener._set_trace_context_variables()

            # Get the calls to set_test_variable
            calls = mock_builtin.set_test_variable.call_args_list

            # Find trace ID and span ID calls
            trace_id_call = None
            span_id_call = None
            traceparent_call = None

            for call in calls:
                var_name, var_value = call[0]
                if var_name == "${TRACE_ID}":
                    trace_id_call = var_value
                elif var_name == "${SPAN_ID}":
                    span_id_call = var_value
                elif var_name == "${TRACEPARENT}":
                    traceparent_call = var_value

            # Verify formats
            if trace_id_call:
                assert len(trace_id_call) == 32  # 32 hex chars
                assert all(c in "0123456789abcdef" for c in trace_id_call)

            if span_id_call:
                assert len(span_id_call) == 16  # 16 hex chars
                assert all(c in "0123456789abcdef" for c in span_id_call)

            if traceparent_call:
                # W3C traceparent format: 00-{trace_id}-{span_id}-{flags}
                parts = traceparent_call.split("-")
                assert len(parts) == 4
                assert parts[0] == "00"  # version
                assert len(parts[1]) == 32  # trace_id
                assert len(parts[2]) == 16  # span_id
                assert len(parts[3]) == 2  # flags

    @patch("robotframework_tracer.listener.BUILTIN_AVAILABLE", True)
    @patch("robotframework_tracer.listener.BuiltIn")
    def test_start_test_sets_context_variables(self, mock_builtin_class):
        """Test that start_test calls _set_trace_context_variables."""
        mock_builtin = Mock()
        mock_builtin_class.return_value = mock_builtin

        # Mock test data
        test_data = Mock()
        test_data.name = "Test Case"
        test_data.tags = []

        test_result = Mock()

        # Start a suite first to have a parent span
        suite_data = Mock()
        suite_data.name = "Test Suite"
        suite_data.source = "/path/to/suite.robot"
        suite_data.metadata = {}

        suite_result = Mock()

        self.listener.start_suite(suite_data, suite_result)

        # Now start the test
        self.listener.start_test(test_data, test_result)

        # Verify that trace context variables were set
        assert mock_builtin.set_test_variable.called

    @patch("robotframework_tracer.listener.BUILTIN_AVAILABLE", True)
    @patch("robotframework_tracer.listener.BuiltIn")
    def test_exception_handling_in_set_trace_context(self, mock_builtin_class):
        """Test that exceptions in _set_trace_context_variables are handled gracefully."""
        # Make BuiltIn().set_test_variable raise an exception
        mock_builtin = Mock()
        mock_builtin.set_test_variable.side_effect = Exception("Test exception")
        mock_builtin_class.return_value = mock_builtin

        # Should not raise an exception
        self.listener._set_trace_context_variables()

    def test_trace_headers_structure(self):
        """Test that trace headers have the expected structure."""
        from opentelemetry.propagate import inject

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test_span"):
            headers = {}
            inject(headers)

            # Should contain traceparent at minimum
            assert "traceparent" in headers
            assert isinstance(headers["traceparent"], str)

            # May contain tracestate
            if "tracestate" in headers:
                assert isinstance(headers["tracestate"], str)
