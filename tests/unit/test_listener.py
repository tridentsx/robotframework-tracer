from unittest.mock import Mock, patch

from robotframework_tracer.listener import TracingListener


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_listener_initialization(mock_trace, mock_provider, mock_exporter):
    """Test listener initialization."""
    # Args as RF would pass them (colon-separated, split by RF)
    listener = TracingListener("endpoint=http", "//jaeger", "4318", "service_name=test")

    assert listener.config.endpoint == "http://jaeger:4318"
    assert listener.config.service_name == "test"
    assert listener.span_stack == []


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_start_suite(mock_trace, mock_provider, mock_exporter):
    """Test start_suite creates and pushes span."""
    listener = TracingListener()
    mock_span = Mock()
    listener.tracer = Mock()
    listener.tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Test Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    listener.start_suite(data, result)

    assert len(listener.span_stack) == 1
    assert listener.span_stack[0] == mock_span


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_end_suite(mock_trace, mock_provider, mock_exporter):
    """Test end_suite pops and ends span."""
    listener = TracingListener()
    mock_span = Mock()
    listener.span_stack = [mock_span]

    data = Mock()
    result = Mock()
    result.status = "PASS"
    result.elapsedtime = 1000

    listener.end_suite(data, result)

    assert len(listener.span_stack) == 0
    mock_span.end.assert_called_once()


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_start_test(mock_trace, mock_provider, mock_exporter):
    """Test start_test creates child span."""
    listener = TracingListener()
    parent_span = Mock()
    test_span = Mock()
    listener.span_stack = [parent_span]
    listener.tracer = Mock()
    listener.tracer.start_span.return_value = test_span

    data = Mock()
    data.name = "Test Case"
    data.tags = []

    result = Mock()
    result.id = "s1-t1"

    listener.start_test(data, result)

    assert len(listener.span_stack) == 2
    assert listener.span_stack[-1] == test_span


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_end_test_with_failure(mock_trace, mock_provider, mock_exporter):
    """Test end_test handles failure."""
    listener = TracingListener()
    mock_span = Mock()
    listener.span_stack = [mock_span]

    data = Mock()
    result = Mock()
    result.status = "FAIL"
    result.elapsedtime = 1000
    result.message = "Test failed"

    listener.end_test(data, result)

    assert len(listener.span_stack) == 0
    mock_span.end.assert_called_once()


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_error_handling(mock_trace, mock_provider, mock_exporter, capsys):
    """Test that errors in listener don't break execution."""
    listener = TracingListener()
    listener.tracer = Mock()
    listener.tracer.start_span.side_effect = Exception("Test error")

    data = Mock()
    data.name = "Test Suite"
    data.source = None
    data.metadata = {}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    # Should not raise exception
    listener.start_suite(data, result)

    captured = capsys.readouterr()
    assert "TracingListener error" in captured.out


def test_parse_listener_args_url_reconstruction():
    """Test that URLs split by RF's colon separator are reconstructed."""
    from robotframework_tracer.listener import TracingListener

    # RF splits 'endpoint=http://localhost:4318/v1/traces:service_name=test' on ':'
    # becomes: ('endpoint=http', '//localhost', '4318/v1/traces', 'service_name=test')
    args = ("endpoint=http", "//localhost", "4318/v1/traces", "service_name=test")
    result = TracingListener._parse_listener_args(args)

    assert result["endpoint"] == "http://localhost:4318/v1/traces"
    assert result["service_name"] == "test"


def test_parse_listener_args_empty():
    """Test empty args returns empty dict."""
    from robotframework_tracer.listener import TracingListener

    assert TracingListener._parse_listener_args(()) == {}


def test_parse_listener_args_simple():
    """Test simple key=value parsing with colon separator."""
    from robotframework_tracer.listener import TracingListener

    # RF splits 'service_name=mytest:capture_logs=true' on ':'
    args = ("service_name=mytest", "capture_logs=true")
    result = TracingListener._parse_listener_args(args)

    assert result["service_name"] == "mytest"
    assert result["capture_logs"] == "true"


def test_parse_listener_args_multiple_options_with_url():
    """Test multiple options including a URL."""
    from robotframework_tracer.listener import TracingListener

    # RF splits 'endpoint=http://jaeger:4318/v1/traces:service_name=api-tests:capture_logs=true'
    args = (
        "endpoint=http",
        "//jaeger",
        "4318/v1/traces",
        "service_name=api-tests",
        "capture_logs=true",
    )
    result = TracingListener._parse_listener_args(args)

    assert result["endpoint"] == "http://jaeger:4318/v1/traces"
    assert result["service_name"] == "api-tests"
    assert result["capture_logs"] == "true"


def test_parse_listener_args_https_url():
    """Test HTTPS URL reconstruction."""
    from robotframework_tracer.listener import TracingListener

    # RF splits 'endpoint=https://tempo.example.com:443/v1/traces'
    args = ("endpoint=https", "//tempo.example.com", "443/v1/traces")
    result = TracingListener._parse_listener_args(args)

    assert result["endpoint"] == "https://tempo.example.com:443/v1/traces"


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_extract_parent_context_from_traceparent(
    mock_trace, mock_provider, mock_exporter, monkeypatch
):
    """Test that TRACEPARENT env var is used to create parent context."""
    monkeypatch.setenv("TRACEPARENT", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")

    listener = TracingListener()

    assert listener.parent_context is not None


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_extract_parent_context_with_tracestate(
    mock_trace, mock_provider, mock_exporter, monkeypatch
):
    """Test that TRACESTATE env var is included in parent context."""
    monkeypatch.setenv("TRACEPARENT", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
    monkeypatch.setenv("TRACESTATE", "vendor1=value1")

    listener = TracingListener()

    assert listener.parent_context is not None


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_no_parent_context_when_traceparent_absent(
    mock_trace, mock_provider, mock_exporter, monkeypatch
):
    """Test that parent_context is None when TRACEPARENT is not set."""
    monkeypatch.delenv("TRACEPARENT", raising=False)

    listener = TracingListener()

    assert listener.parent_context is None


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_start_suite_passes_parent_context(mock_trace, mock_provider, mock_exporter, monkeypatch):
    """Test that start_suite passes parent_context to SpanBuilder."""
    monkeypatch.setenv("TRACEPARENT", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")

    listener = TracingListener()
    mock_span = Mock()
    listener.tracer = Mock()
    listener.tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Test Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    listener.start_suite(data, result)

    # Verify the suite span was created with a context (not None)
    call_args = listener.tracer.start_span.call_args
    assert call_args.kwargs.get("context") is not None or call_args[1].get("context") is not None
