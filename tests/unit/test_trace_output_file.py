"""Tests for trace output file feature."""

import io
import json
import os
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from robotframework_tracer.config import TracerConfig
from robotframework_tracer.listener import TracingListener, _OtlpJsonFileExporter

# --- Config tests ---


def test_config_trace_output_file_default():
    """Test that trace_output_file defaults to empty string (disabled)."""
    config = TracerConfig()
    assert config.trace_output_file == ""


def test_config_trace_output_file_from_kwargs():
    """Test trace_output_file from kwargs."""
    config = TracerConfig(trace_output_file="auto")
    assert config.trace_output_file == "auto"


def test_config_trace_output_file_from_env(monkeypatch):
    """Test trace_output_file from environment variable."""
    monkeypatch.setenv("RF_TRACER_OUTPUT_FILE", "my_traces.json")
    config = TracerConfig()
    assert config.trace_output_file == "my_traces.json"


def test_config_trace_output_format_default():
    """Test that trace_output_format defaults to json."""
    config = TracerConfig()
    assert config.trace_output_format == "json"


def test_config_trace_output_format_gz():
    """Test trace_output_format set to gz."""
    config = TracerConfig(trace_output_format="gz")
    assert config.trace_output_format == "gz"


# --- Listener file handling tests ---


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_no_file_opened_when_disabled(mock_trace, mock_provider, mock_exporter):
    """Test that no file is opened when trace_output_file is empty."""
    listener = TracingListener()
    assert listener._trace_file is None


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_explicit_file_opened_on_init(mock_trace, mock_provider, mock_exporter, tmp_path):
    """Test that an explicit file path is opened during init."""
    filepath = str(tmp_path / "traces.json")
    listener = TracingListener(f"trace_output_file={filepath}")
    assert listener._trace_file is not None
    assert not listener._trace_file.closed
    listener._trace_file.close()


@patch("robotframework_tracer.listener.HTTPExporter")
@patch("robotframework_tracer.listener.TracerProvider")
@patch("robotframework_tracer.listener.trace")
def test_auto_file_not_opened_on_init(mock_trace, mock_provider, mock_exporter):
    """Test that 'auto' mode defers file creation to start_suite."""
    listener = TracingListener("trace_output_file=auto")
    assert listener._trace_file is None
    assert listener.config.trace_output_file == "auto"


def test_sanitize_filename():
    """Test suite name to filename sanitization."""
    assert TracingListener._sanitize_filename("Diverse Suite") == "diverse_suite"
    assert TracingListener._sanitize_filename("My Test Suite!") == "my_test_suite"
    assert TracingListener._sanitize_filename("suite/with/slashes") == "suite_with_slashes"
    assert TracingListener._sanitize_filename("") == "trace"


@patch("robotframework_tracer.listener.HTTPExporter")
def test_auto_file_created_on_start_suite(mock_exporter, tmp_path):
    """Test that auto mode creates file with suite name and trace ID on start_suite."""
    os.chdir(tmp_path)
    listener = TracingListener("trace_output_file=auto")

    data = Mock()
    data.name = "My Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    listener.start_suite(data, result)

    assert listener._trace_file is not None
    filename = listener._trace_file.name
    assert "my_suite_" in filename
    assert filename.endswith("_traces.json")
    listener._trace_file.close()


@patch("robotframework_tracer.listener.HTTPExporter")
def test_auto_gz_file_created_on_start_suite(mock_exporter, tmp_path):
    """Test auto mode with gz format creates .json.gz file."""
    os.chdir(tmp_path)
    listener = TracingListener("trace_output_file=auto", "trace_output_format=gz")

    data = Mock()
    data.name = "Gzip Suite"
    data.source = "/path/to/suite.robot"
    data.metadata = {}

    result = Mock()
    result.id = "s1"
    result.starttime = None
    result.endtime = None

    listener.start_suite(data, result)

    assert listener._trace_file is not None
    assert "gzip_suite_" in listener._trace_file.name
    assert listener._trace_file.name.endswith("_traces.json.gz")
    listener._trace_file.close()


@patch("robotframework_tracer.listener.HTTPExporter")
def test_close_flushes_and_closes_file(mock_exporter, tmp_path):
    """Test that close() properly closes the trace file."""
    filepath = str(tmp_path / "traces.json")
    listener = TracingListener(f"trace_output_file={filepath}")

    assert listener._trace_file is not None
    file_ref = listener._trace_file

    listener.close()

    assert file_ref.closed
    assert listener._trace_file is None


@patch("robotframework_tracer.listener.HTTPExporter")
def test_gz_file_opened_on_init(mock_exporter, tmp_path):
    """Test that gz format opens a gzip file."""
    filepath = str(tmp_path / "traces.json")
    listener = TracingListener(f"trace_output_file={filepath}", "trace_output_format=gz")
    assert listener._trace_file is not None
    assert listener._trace_file.name.endswith(".gz")
    listener._trace_file.close()


@patch("robotframework_tracer.listener.HTTPExporter")
def test_open_trace_file_error_handling(mock_exporter, capsys):
    """Test _open_trace_file handles errors gracefully."""
    listener = TracingListener()
    listener._open_trace_file("/nonexistent/path/traces.json")
    assert listener._trace_file is None
    captured = capsys.readouterr()
    assert "Warning: Failed to open trace output file" in captured.out


# --- OTLP JSON exporter tests (using real SDK spans) ---


def _collect_spans(fn):
    """Run fn(tracer) and return collected ReadableSpan objects."""
    provider = TracerProvider()
    collected = []

    class _Collector(SpanExporter):
        def export(self, batch):
            collected.extend(batch)
            return SpanExportResult.SUCCESS

        def shutdown(self):
            pass

    provider.add_span_processor(SimpleSpanProcessor(_Collector()))
    tracer = provider.get_tracer("test")
    fn(tracer)
    provider.force_flush()
    return collected


def test_otlp_exporter_writes_valid_json():
    """Test _OtlpJsonFileExporter writes valid OTLP JSON."""
    spans = _collect_spans(
        lambda t: t.start_span("test_span", attributes={"rf.test.name": "T1"}).end()
    )

    buf = io.StringIO()
    exporter = _OtlpJsonFileExporter(buf)
    result = exporter.export(spans)

    assert result == SpanExportResult.SUCCESS
    record = json.loads(buf.getvalue().strip())
    assert "resource_spans" in record


def test_otlp_exporter_has_correct_structure():
    """Test OTLP JSON has resourceSpans > scopeSpans > spans structure."""
    spans = _collect_spans(lambda t: t.start_span("my_span", attributes={"k": "v"}).end())

    buf = io.StringIO()
    _OtlpJsonFileExporter(buf).export(spans)
    record = json.loads(buf.getvalue().strip())

    rs = record["resource_spans"]
    assert len(rs) >= 1
    ss = rs[0]["scope_spans"]
    assert len(ss) >= 1
    span_list = ss[0]["spans"]
    assert len(span_list) >= 1
    span = span_list[0]
    assert span["name"] == "my_span"
    assert "trace_id" in span
    assert "span_id" in span


def test_otlp_exporter_hex_trace_ids():
    """Test that trace_id and span_id are hex strings, not base64."""
    spans = _collect_spans(lambda t: t.start_span("hex_test").end())

    buf = io.StringIO()
    _OtlpJsonFileExporter(buf).export(spans)
    record = json.loads(buf.getvalue().strip())

    span = record["resource_spans"][0]["scope_spans"][0]["spans"][0]
    # Hex trace_id is 32 chars, span_id is 16 chars, no 0x prefix, no base64 chars like = or /
    assert len(span["trace_id"]) == 32
    assert len(span["span_id"]) == 16
    int(span["trace_id"], 16)  # Should not raise
    int(span["span_id"], 16)  # Should not raise


def test_otlp_exporter_attributes_format():
    """Test attributes use OTLP key/value array format."""
    spans = _collect_spans(
        lambda t: t.start_span("attr_test", attributes={"rf.test.name": "My Test"}).end()
    )

    buf = io.StringIO()
    _OtlpJsonFileExporter(buf).export(spans)
    record = json.loads(buf.getvalue().strip())

    span = record["resource_spans"][0]["scope_spans"][0]["spans"][0]
    attrs = span["attributes"]
    # OTLP format: list of {"key": ..., "value": {"stringValue": ...}}
    assert isinstance(attrs, list)
    attr_dict = {a["key"]: a["value"] for a in attrs}
    assert "rf.test.name" in attr_dict
    assert attr_dict["rf.test.name"]["string_value"] == "My Test"


def test_otlp_exporter_resource_included():
    """Test resource attributes are included in output."""
    spans = _collect_spans(lambda t: t.start_span("res_test").end())

    buf = io.StringIO()
    _OtlpJsonFileExporter(buf).export(spans)
    record = json.loads(buf.getvalue().strip())

    resource = record["resource_spans"][0]["resource"]
    assert "attributes" in resource
    attr_keys = [a["key"] for a in resource["attributes"]]
    assert "service.name" in attr_keys


def test_otlp_exporter_parent_span_id():
    """Test parent_span_id is present for child spans."""

    def create_spans(tracer):
        with tracer.start_as_current_span("parent"):
            tracer.start_span("child").end()

    spans = _collect_spans(create_spans)

    buf = io.StringIO()
    _OtlpJsonFileExporter(buf).export(spans)
    record = json.loads(buf.getvalue().strip())

    span_list = record["resource_spans"][0]["scope_spans"][0]["spans"]
    child = next(s for s in span_list if s["name"] == "child")
    assert "parent_span_id" in child
    assert len(child["parent_span_id"]) == 16


def test_otlp_exporter_compact_output():
    """Test output is compact (no extra whitespace)."""
    spans = _collect_spans(lambda t: t.start_span("compact").end())

    buf = io.StringIO()
    _OtlpJsonFileExporter(buf).export(spans)
    line = buf.getvalue().strip()
    # Compact JSON should not have newlines within the record
    assert "\n" not in line
    # Should not have "  " (indentation)
    assert "  " not in line


def test_otlp_exporter_shutdown():
    """Test shutdown is a no-op."""
    exporter = _OtlpJsonFileExporter(io.StringIO())
    exporter.shutdown()  # Should not raise


# --- Listener lifecycle tests ---


# NOTE: These tests are disabled because log capture now uses OpenTelemetry Logs API
# instead of span events. The logs are sent to /v1/logs endpoint, not as span events.
# See test_listener.py for updated log capture tests.

# @patch("robotframework_tracer.listener.HTTPExporter")
# def test_log_message_capture(mock_exporter):
#     """Test log_message captures log events on current span."""
#     listener = TracingListener("capture_logs=true")
#     mock_span = MagicMock()
#     listener.span_stack.append(mock_span)
#
#     message = MagicMock()
#     message.level = "INFO"
#     message.message = "Test log message"
#     message.timestamp = "20260217 12:00:00.000"
#
#     listener.log_message(message)
#     mock_span.add_event.assert_called_once()
#     call_args = mock_span.add_event.call_args
#     assert call_args[0][0] == "log.info"
#     assert call_args[0][1]["message"] == "Test log message"
#     assert call_args[0][1]["level"] == "INFO"


@patch("robotframework_tracer.listener.HTTPExporter")
def test_log_message_filtered_by_level(mock_exporter):
    """Test log_message filters messages below configured level."""
    listener = TracingListener("capture_logs=true", "log_level=WARN")
    mock_span = MagicMock()
    listener.span_stack.append(mock_span)

    message = MagicMock()
    message.level = "INFO"
    message.message = "Should be filtered"

    listener.log_message(message)
    mock_span.add_event.assert_not_called()


# NOTE: This test is disabled - logs now use OpenTelemetry Logs API, not span events
# @patch("robotframework_tracer.listener.HTTPExporter")
# def test_log_message_truncated(mock_exporter):
#     """Test log_message truncates long messages."""
#     listener = TracingListener("capture_logs=true", "max_log_length=10")
#     mock_span = MagicMock()
#     listener.span_stack.append(mock_span)
#
#     message = MagicMock()
#     message.level = "INFO"
#     message.message = "A" * 100
#     message.timestamp = None
#
#     listener.log_message(message)
#     call_args = mock_span.add_event.call_args
#     assert call_args[0][1]["message"] == "A" * 10 + "..."


@patch("robotframework_tracer.listener.HTTPExporter")
def test_log_message_disabled(mock_exporter):
    """Test log_message does nothing when capture_logs is false."""
    listener = TracingListener()
    mock_span = MagicMock()
    listener.span_stack.append(mock_span)

    message = MagicMock()
    message.level = "INFO"
    message.message = "Should not be captured"

    listener.log_message(message)
    mock_span.add_event.assert_not_called()


@patch("robotframework_tracer.listener.HTTPExporter")
def test_log_message_no_span_stack(mock_exporter):
    """Test log_message does nothing when span stack is empty."""
    listener = TracingListener("capture_logs=true")

    message = MagicMock()
    message.level = "INFO"
    message.message = "No span"

    listener.log_message(message)


@patch("robotframework_tracer.listener.HTTPExporter")
def test_keyword_setup_teardown_events(mock_exporter):
    """Test start/end_keyword pushes and pops spans for SETUP type."""
    listener = TracingListener()

    parent_span = MagicMock()
    listener.span_stack.append(parent_span)

    data = MagicMock()
    data.name = "Suite Setup"
    data.type = "SETUP"
    data.args = []
    data.owner = MagicMock()
    data.owner.name = "BuiltIn"

    result = MagicMock()
    result.id = "k1"
    result.status = "PASS"
    result.starttime = None
    result.endtime = None
    result.message = ""

    listener.start_keyword(data, result)
    assert len(listener.span_stack) == 2

    listener.end_keyword(data, result)
    assert len(listener.span_stack) == 1
