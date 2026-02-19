"""Tests for trace output file feature."""

import io
import json
import os
from unittest.mock import MagicMock, Mock, patch

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from robotframework_tracer.config import TracerConfig
from robotframework_tracer.listener import TracingListener, _OtlpJsonFileExporter
from robotframework_tracer.output_filter import apply_filter

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
    """Test auto mode with gz format creates a per-process temp file."""
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
    assert listener._trace_file.name.endswith(".tmp")
    assert listener._gz_final_path is not None
    assert listener._gz_final_path.endswith("_traces.json.gz")
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
    """Test that gz format opens a per-process temp file for later compression."""
    filepath = str(tmp_path / "traces.json")
    listener = TracingListener(f"trace_output_file={filepath}", "trace_output_format=gz")
    assert listener._trace_file is not None
    assert listener._trace_file.name.endswith(".tmp")
    assert listener._gz_final_path == filepath + ".gz"
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


def _export_to_tempfile(spans, tmp_path, output_filter=None):
    """Helper: export spans to a real temp file and return parsed JSON."""
    filepath = str(tmp_path / "test_traces.json")
    with open(filepath, "w") as f:
        exporter = _OtlpJsonFileExporter(f, output_filter=output_filter)
        result = exporter.export(spans)
    with open(filepath) as f:
        content = f.read().strip()
    return result, content


def test_otlp_exporter_writes_valid_json(tmp_path):
    """Test _OtlpJsonFileExporter writes valid OTLP JSON."""
    spans = _collect_spans(
        lambda t: t.start_span("test_span", attributes={"rf.test.name": "T1"}).end()
    )

    result, content = _export_to_tempfile(spans, tmp_path)

    assert result == SpanExportResult.SUCCESS
    record = json.loads(content)
    assert "resource_spans" in record


def test_otlp_exporter_has_correct_structure(tmp_path):
    """Test OTLP JSON has resourceSpans > scopeSpans > spans structure."""
    spans = _collect_spans(lambda t: t.start_span("my_span", attributes={"k": "v"}).end())

    _, content = _export_to_tempfile(spans, tmp_path)
    record = json.loads(content)

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


def test_otlp_exporter_hex_trace_ids(tmp_path):
    """Test that trace_id and span_id are hex strings, not base64."""
    spans = _collect_spans(lambda t: t.start_span("hex_test").end())

    _, content = _export_to_tempfile(spans, tmp_path)
    record = json.loads(content)

    span = record["resource_spans"][0]["scope_spans"][0]["spans"][0]
    assert len(span["trace_id"]) == 32
    assert len(span["span_id"]) == 16
    int(span["trace_id"], 16)  # Should not raise
    int(span["span_id"], 16)  # Should not raise


def test_otlp_exporter_attributes_format(tmp_path):
    """Test attributes use OTLP key/value array format."""
    spans = _collect_spans(
        lambda t: t.start_span("attr_test", attributes={"rf.test.name": "My Test"}).end()
    )

    _, content = _export_to_tempfile(spans, tmp_path)
    record = json.loads(content)

    span = record["resource_spans"][0]["scope_spans"][0]["spans"][0]
    attrs = span["attributes"]
    assert isinstance(attrs, list)
    attr_dict = {a["key"]: a["value"] for a in attrs}
    assert "rf.test.name" in attr_dict
    assert attr_dict["rf.test.name"]["string_value"] == "My Test"


def test_otlp_exporter_resource_included(tmp_path):
    """Test resource attributes are included in output."""
    spans = _collect_spans(lambda t: t.start_span("res_test").end())

    _, content = _export_to_tempfile(spans, tmp_path)
    record = json.loads(content)

    resource = record["resource_spans"][0]["resource"]
    assert "attributes" in resource
    attr_keys = [a["key"] for a in resource["attributes"]]
    assert "service.name" in attr_keys


def test_otlp_exporter_parent_span_id(tmp_path):
    """Test parent_span_id is present for child spans."""

    def create_spans(tracer):
        with tracer.start_as_current_span("parent"):
            tracer.start_span("child").end()

    spans = _collect_spans(create_spans)

    _, content = _export_to_tempfile(spans, tmp_path)
    record = json.loads(content)

    span_list = record["resource_spans"][0]["scope_spans"][0]["spans"]
    child = next(s for s in span_list if s["name"] == "child")
    assert "parent_span_id" in child
    assert len(child["parent_span_id"]) == 16


def test_otlp_exporter_compact_output(tmp_path):
    """Test output is compact (no extra whitespace)."""
    spans = _collect_spans(lambda t: t.start_span("compact").end())

    _, content = _export_to_tempfile(spans, tmp_path)
    # Compact JSON should not have newlines within the record
    assert "\n" not in content
    # Should not have "  " (indentation)
    assert "  " not in content


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


# --- Output filter validation tests ---


def test_load_filter_valid_preset():
    """Test loading a valid built-in preset."""
    from robotframework_tracer.output_filter import load_filter

    cfg = load_filter("full")
    assert cfg is not None
    assert cfg["version"] == "1.0.0"


def test_load_filter_minimal_preset():
    """Test loading the minimal preset passes validation."""
    from robotframework_tracer.output_filter import load_filter

    cfg = load_filter("minimal")
    assert cfg is not None
    assert cfg["version"] == "1.0.0"


def test_load_filter_invalid_schema(tmp_path, capsys):
    """Test that an invalid filter file is rejected with warnings."""
    from robotframework_tracer.output_filter import load_filter

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"version": "1.0.0", "spans": {"bogus_key": True}}))
    cfg = load_filter(str(bad))
    assert cfg is None
    captured = capsys.readouterr()
    assert "validation errors" in captured.out
    assert "bogus_key" in captured.out


def test_load_filter_invalid_type(tmp_path, capsys):
    """Test that wrong types are caught by schema validation."""
    from robotframework_tracer.output_filter import load_filter

    bad = tmp_path / "bad_type.json"
    bad.write_text(json.dumps({"version": "1.0.0", "spans": {"include_suites": "yes"}}))
    cfg = load_filter(str(bad))
    assert cfg is None
    captured = capsys.readouterr()
    assert "validation errors" in captured.out


def test_load_filter_invalid_keyword_type(tmp_path, capsys):
    """Test that invalid keyword types are caught."""
    from robotframework_tracer.output_filter import load_filter

    bad = tmp_path / "bad_kw.json"
    bad.write_text(
        json.dumps({"version": "1.0.0", "spans": {"keyword_types": ["KEYWORD", "INVALID"]}})
    )
    cfg = load_filter(str(bad))
    assert cfg is None
    captured = capsys.readouterr()
    assert "validation errors" in captured.out


def test_load_filter_unsupported_version(tmp_path, capsys):
    """Test that version 2.x is rejected."""
    from robotframework_tracer.output_filter import load_filter

    bad = tmp_path / "v2.json"
    bad.write_text(json.dumps({"version": "2.0.0"}))
    cfg = load_filter(str(bad))
    assert cfg is None
    captured = capsys.readouterr()
    assert "Unsupported output filter version" in captured.out


def test_load_filter_empty_path():
    """Test that empty path returns None."""
    from robotframework_tracer.output_filter import load_filter

    assert load_filter("") is None
    assert load_filter(None) is None


def test_load_filter_missing_file(capsys):
    """Test that missing file prints warning and returns None."""
    from robotframework_tracer.output_filter import load_filter

    cfg = load_filter("/nonexistent/filter.json")
    assert cfg is None
    captured = capsys.readouterr()
    assert "not found" in captured.out


# --- Output filter apply_filter tests ---


def _make_otlp(spans, resource_attrs=None):
    """Build a minimal OTLP JSON dict for testing apply_filter."""
    return {
        "resource_spans": [
            {
                "resource": {
                    "attributes": resource_attrs
                    or [
                        {"key": "service.name", "value": {"string_value": "rf"}},
                        {"key": "telemetry.sdk.name", "value": {"string_value": "test"}},
                        {"key": "host.name", "value": {"string_value": "localhost"}},
                    ]
                },
                "scope_spans": [{"scope": {"name": "test"}, "spans": spans}],
            }
        ]
    }


def _suite_span(span_id="a1", parent=""):
    return {
        "trace_id": "abc123",
        "span_id": span_id,
        "parent_span_id": parent,
        "name": "My Suite",
        "kind": 1,
        "start_time_unix_nano": "100",
        "end_time_unix_nano": "200",
        "status": {"code": 1},
        "attributes": [{"key": "rf.suite.name", "value": {"string_value": "My Suite"}}],
        "events": [{"name": "suite.start"}],
    }


def _test_span(span_id="b1", parent="a1"):
    return {
        "trace_id": "abc123",
        "span_id": span_id,
        "parent_span_id": parent,
        "name": "Test 1",
        "kind": 1,
        "start_time_unix_nano": "110",
        "end_time_unix_nano": "190",
        "status": {"code": 1},
        "attributes": [
            {"key": "rf.test.name", "value": {"string_value": "Test 1"}},
            {"key": "rf.elapsed_time", "value": {"string_value": "80"}},
        ],
        "events": [],
    }


def _kw_span(span_id="c1", parent="b1", kw_type="KEYWORD"):
    return {
        "trace_id": "abc123",
        "span_id": span_id,
        "parent_span_id": parent,
        "name": "Log",
        "kind": 1,
        "start_time_unix_nano": "120",
        "end_time_unix_nano": "130",
        "status": {"code": 1},
        "attributes": [
            {"key": "rf.keyword.type", "value": {"string_value": kw_type}},
            {"key": "rf.keyword.name", "value": {"string_value": "Log"}},
            {"key": "rf.keyword.args", "value": {"string_value": "hello"}},
        ],
        "events": [{"name": "log"}],
    }


def test_apply_filter_none_returns_unchanged():
    d = _make_otlp([_suite_span()])
    result = apply_filter(d, None)
    assert len(result["resource_spans"][0]["scope_spans"][0]["spans"]) == 1


def test_apply_filter_exclude_suites():
    d = _make_otlp([_suite_span(), _test_span(), _kw_span()])
    cfg = {"version": "1.0.0", "spans": {"include_suites": False}}
    result = apply_filter(d, cfg)
    names = [s["name"] for s in result["resource_spans"][0]["scope_spans"][0]["spans"]]
    assert "My Suite" not in names
    assert "Test 1" in names


def test_apply_filter_exclude_tests():
    d = _make_otlp([_suite_span(), _test_span(), _kw_span()])
    cfg = {"version": "1.0.0", "spans": {"include_tests": False}}
    result = apply_filter(d, cfg)
    names = [s["name"] for s in result["resource_spans"][0]["scope_spans"][0]["spans"]]
    assert "Test 1" not in names
    assert "My Suite" in names


def test_apply_filter_exclude_keywords():
    d = _make_otlp([_suite_span(), _test_span(), _kw_span()])
    cfg = {"version": "1.0.0", "spans": {"include_keywords": False}}
    result = apply_filter(d, cfg)
    names = [s["name"] for s in result["resource_spans"][0]["scope_spans"][0]["spans"]]
    assert "Log" not in names
    assert "Test 1" in names


def test_apply_filter_keyword_types():
    spans = [_kw_span("c1", kw_type="KEYWORD"), _kw_span("c2", kw_type="SETUP")]
    d = _make_otlp(spans)
    cfg = {"version": "1.0.0", "spans": {"keyword_types": ["SETUP"]}}
    result = apply_filter(d, cfg)
    remaining = result["resource_spans"][0]["scope_spans"][0]["spans"]
    assert len(remaining) == 1
    kw_attrs = {a["key"]: a["value"]["string_value"] for a in remaining[0]["attributes"]}
    assert kw_attrs["rf.keyword.type"] == "SETUP"


def test_apply_filter_exclude_events():
    d = _make_otlp([_suite_span(), _kw_span()])
    cfg = {"version": "1.0.0", "spans": {"include_events": False}}
    result = apply_filter(d, cfg)
    for span in result["resource_spans"][0]["scope_spans"][0]["spans"]:
        assert "events" not in span


def test_apply_filter_fields():
    d = _make_otlp([_test_span()])
    cfg = {"version": "1.0.0", "spans": {"fields": ["trace_id", "span_id", "name", "attributes"]}}
    result = apply_filter(d, cfg)
    span = result["resource_spans"][0]["scope_spans"][0]["spans"][0]
    assert "trace_id" in span
    assert "name" in span
    assert "kind" not in span
    assert "start_time_unix_nano" not in span


def test_apply_filter_attribute_exclude():
    d = _make_otlp([_kw_span()])
    cfg = {
        "version": "1.0.0",
        "spans": {"attributes": {"include": [], "exclude": ["rf.keyword.args"]}},
    }
    result = apply_filter(d, cfg)
    span = result["resource_spans"][0]["scope_spans"][0]["spans"][0]
    keys = [a["key"] for a in span["attributes"]]
    assert "rf.keyword.args" not in keys
    assert "rf.keyword.name" in keys


def test_apply_filter_attribute_include():
    d = _make_otlp([_kw_span()])
    cfg = {
        "version": "1.0.0",
        "spans": {"attributes": {"include": ["rf.keyword.name"], "exclude": []}},
    }
    result = apply_filter(d, cfg)
    span = result["resource_spans"][0]["scope_spans"][0]["spans"][0]
    keys = [a["key"] for a in span["attributes"]]
    assert keys == ["rf.keyword.name"]


def test_apply_filter_resource_exclude_attributes():
    d = _make_otlp([_suite_span()])
    cfg = {"version": "1.0.0", "resource": {"include_attributes": False}}
    result = apply_filter(d, cfg)
    res = result["resource_spans"][0]["resource"]
    assert "attributes" not in res


def test_apply_filter_resource_attribute_keys():
    d = _make_otlp([_suite_span()])
    cfg = {
        "version": "1.0.0",
        "resource": {"include_attributes": True, "attribute_keys": ["service.*"]},
    }
    result = apply_filter(d, cfg)
    res = result["resource_spans"][0]["resource"]
    keys = [a["key"] for a in res["attributes"]]
    assert keys == ["service.name"]


def test_apply_filter_scope_exclude():
    d = _make_otlp([_suite_span()])
    cfg = {"version": "1.0.0", "scope": {"include": False}}
    result = apply_filter(d, cfg)
    ss = result["resource_spans"][0]["scope_spans"][0]
    assert "scope" not in ss


def test_apply_filter_max_depth():
    spans = [
        _suite_span("a1", ""),
        _test_span("b1", "a1"),
        _kw_span("c1", "b1"),
        _kw_span("d1", "c1"),  # depth 3
    ]
    d = _make_otlp(spans)
    cfg = {"version": "1.0.0", "spans": {"max_depth": 2}}
    result = apply_filter(d, cfg)
    ids = [s["span_id"] for s in result["resource_spans"][0]["scope_spans"][0]["spans"]]
    assert "a1" in ids
    assert "b1" in ids
    assert "c1" in ids
    assert "d1" not in ids


def test_apply_filter_full_preset_keeps_everything():
    """Full preset (empty arrays) should not filter anything."""
    from robotframework_tracer.output_filter import load_filter

    cfg = load_filter("full")
    spans = [_suite_span(), _test_span(), _kw_span()]
    d = _make_otlp(spans)
    result = apply_filter(d, cfg)
    assert len(result["resource_spans"][0]["scope_spans"][0]["spans"]) == 3


def test_apply_filter_minimal_preset():
    """Minimal preset should strip events and certain attributes."""
    from robotframework_tracer.output_filter import load_filter

    cfg = load_filter("minimal")
    d = _make_otlp([_test_span()])
    result = apply_filter(d, cfg)
    span = result["resource_spans"][0]["scope_spans"][0]["spans"][0]
    assert "events" not in span
    keys = [a["key"] for a in span["attributes"]]
    assert "rf.elapsed_time" not in keys
    assert "rf.test.name" in keys
