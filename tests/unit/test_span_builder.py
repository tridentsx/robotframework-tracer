from unittest.mock import Mock

from opentelemetry.trace import StatusCode

from robotframework_tracer.attributes import RFAttributes
from robotframework_tracer.span_builder import SpanBuilder


def test_create_suite_span():
    """Test creating a suite span."""
    tracer = Mock()
    mock_span = Mock()
    tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Test Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}  # Empty dict

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    span = SpanBuilder.create_suite_span(tracer, data, result)

    assert span == mock_span
    tracer.start_span.assert_called_once()
    call_args = tracer.start_span.call_args
    assert call_args[0][0] == "Test Suite"


def test_create_suite_span_with_parent_context():
    """Test creating a suite span with external parent context."""
    from opentelemetry.context import Context

    tracer = Mock()
    mock_span = Mock()
    tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Test Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    # Use a real Context object so baggage operations work
    parent_context = Context()

    span = SpanBuilder.create_suite_span(tracer, data, result, parent_context=parent_context)

    assert span == mock_span
    tracer.start_span.assert_called_once()
    call_args = tracer.start_span.call_args
    # Context should not be None when parent_context is provided
    assert call_args.kwargs.get("context") is not None or call_args[1].get("context") is not None


def test_create_test_span():
    """Test creating a test span."""
    tracer = Mock()
    mock_span = Mock()
    tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Test Case"
    data.tags = ["smoke"]

    result = Mock()
    result.id = "s1-t1"

    parent_context = Mock()

    span = SpanBuilder.create_test_span(tracer, data, result, parent_context)

    assert span == mock_span
    tracer.start_span.assert_called_once()


def test_create_keyword_span():
    """Test creating a keyword span."""
    tracer = Mock()
    mock_span = Mock()
    tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Should Be Equal"
    data.libname = "BuiltIn"
    data.type = "KEYWORD"
    data.args = ["Hello", "Hello"]

    result = Mock()

    parent_context = Mock()

    span = SpanBuilder.create_keyword_span(tracer, data, result, parent_context)

    assert span == mock_span
    tracer.start_span.assert_called_once()
    call_args = tracer.start_span.call_args
    assert call_args[0][0] == "Should Be Equal Hello, Hello"


def test_set_span_status_pass():
    """Test setting span status for passed result."""
    span = Mock()
    result = Mock()
    result.status = "PASS"
    result.elapsedtime = 1500
    result.message = ""

    SpanBuilder.set_span_status(span, result)

    span.set_attribute.assert_any_call(RFAttributes.STATUS, "PASS")
    span.set_attribute.assert_any_call(RFAttributes.ELAPSED_TIME, 1.5)
    span.set_status.assert_called_once()
    status = span.set_status.call_args[0][0]
    assert status.status_code == StatusCode.OK


def test_set_span_status_fail():
    """Test setting span status for failed result."""
    span = Mock()
    result = Mock()
    result.status = "FAIL"
    result.elapsedtime = 2000
    result.message = "Test failed"

    SpanBuilder.set_span_status(span, result)

    span.set_attribute.assert_any_call(RFAttributes.STATUS, "FAIL")
    span.set_attribute.assert_any_call(RFAttributes.ELAPSED_TIME, 2.0)
    span.set_status.assert_called_once()
    status = span.set_status.call_args[0][0]
    assert status.status_code == StatusCode.ERROR


def test_add_error_event():
    """Test adding error event to span."""
    span = Mock()
    result = Mock()
    result.status = "FAIL"
    result.message = "Assertion failed"
    result.error = None
    result.endtime = None

    SpanBuilder.add_error_event(span, result)

    # Check that add_event was called with test.failed
    span.add_event.assert_called_once()
    call_args = span.add_event.call_args
    assert call_args[0][0] == "test.failed"
    assert "message" in call_args[0][1]
    assert call_args[0][1]["message"] == "Assertion failed"


def test_add_error_event_no_message():
    """Test that no event is added when there's no message."""
    span = Mock()
    result = Mock()
    result.status = "FAIL"
    result.message = ""

    SpanBuilder.add_error_event(span, result)

    span.add_event.assert_not_called()


def test_add_prefix_text_style():
    """Test text prefix style for all span types."""
    assert SpanBuilder._add_prefix("My Suite", "SUITE", "text") == "[SUITE] My Suite"
    assert SpanBuilder._add_prefix("My Test", "TEST", "text") == "[TEST CASE] My Test"
    assert SpanBuilder._add_prefix("My KW", "KEYWORD", "text") == "[TEST STEP] My KW"
    assert SpanBuilder._add_prefix("Setup", "SETUP", "text") == "[SETUP] Setup"
    assert SpanBuilder._add_prefix("Teardown", "TEARDOWN", "text") == "[TEARDOWN] Teardown"


def test_add_prefix_emoji_style():
    """Test emoji prefix style for all span types."""
    assert SpanBuilder._add_prefix("My Suite", "SUITE", "emoji") == "📦 My Suite"
    assert SpanBuilder._add_prefix("My Test", "TEST", "emoji") == "🧪 My Test"
    assert SpanBuilder._add_prefix("My KW", "KEYWORD", "emoji") == "👟 My KW"
    assert SpanBuilder._add_prefix("Setup", "SETUP", "emoji") == "🔧 Setup"
    assert SpanBuilder._add_prefix("Teardown", "TEARDOWN", "emoji") == "🧹 Teardown"


def test_add_prefix_none_style():
    """Test none prefix style returns name unchanged."""
    assert SpanBuilder._add_prefix("My Suite", "SUITE", "none") == "My Suite"
    assert SpanBuilder._add_prefix("My Suite", "SUITE", "") == "My Suite"


def test_create_suite_span_with_metadata():
    """Test suite span includes metadata in baggage."""
    tracer = Mock()
    mock_span = Mock()
    tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Suite With Meta"
    data.source = "/path/to/suite.robot"
    data.metadata = {"Version": "1.0", "Author": "Test"}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    span = SpanBuilder.create_suite_span(tracer, data, result)
    assert span == mock_span


def test_create_keyword_span_setup_type():
    """Test keyword span with SETUP type uses correct prefix."""
    tracer = Mock()
    mock_span = Mock()
    tracer.start_span.return_value = mock_span

    data = Mock()
    data.name = "Suite Setup"
    data.libname = "BuiltIn"
    data.type = "SETUP"
    data.args = []

    result = Mock()
    parent_context = Mock()

    SpanBuilder.create_keyword_span(tracer, data, result, parent_context, prefix_style="text")
    call_args = tracer.start_span.call_args
    assert call_args[0][0] == "[SETUP] Suite Setup"
