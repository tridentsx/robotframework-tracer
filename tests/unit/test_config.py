import json

from robotframework_tracer.config import TracerConfig


def test_default_config():
    """Test default configuration values."""
    config = TracerConfig()
    assert config.endpoint == "http://localhost:4318/v1/traces"
    assert config.service_name == "rf"
    assert config.protocol == "http"
    assert config.capture_arguments is True
    assert config.max_arg_length == 200
    assert config.capture_logs is False
    assert config.sample_rate == 1.0


def test_config_from_kwargs():
    """Test configuration from keyword arguments."""
    config = TracerConfig(
        endpoint="http://jaeger:4318/v1/traces",
        service_name="my-service",
        protocol="grpc",
        capture_arguments=False,
        max_arg_length=100,
    )
    assert config.endpoint == "http://jaeger:4318/v1/traces"
    assert config.service_name == "my-service"
    assert config.protocol == "grpc"
    assert config.capture_arguments is False
    assert config.max_arg_length == 100


def test_config_from_env_vars(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "env-service")
    monkeypatch.setenv("RF_TRACER_CAPTURE_ARGUMENTS", "false")

    config = TracerConfig()
    assert config.endpoint == "http://tempo:4318"
    assert config.service_name == "env-service"
    assert config.capture_arguments is False


def test_config_precedence(monkeypatch):
    """Test that kwargs take precedence over env vars."""
    monkeypatch.setenv("OTEL_SERVICE_NAME", "env-service")

    config = TracerConfig(service_name="kwarg-service")
    assert config.service_name == "kwarg-service"


def test_from_listener_args_single_string():
    """Test parsing listener arguments from single string."""
    config = TracerConfig.from_listener_args(
        "endpoint=http://jaeger:4318,service_name=test-service"
    )
    assert config.endpoint == "http://jaeger:4318"
    assert config.service_name == "test-service"


def test_from_listener_args_multiple_strings():
    """Test parsing listener arguments from multiple strings."""
    config = TracerConfig.from_listener_args(
        "endpoint=http://jaeger:4318", "service_name=test-service"
    )
    assert config.endpoint == "http://jaeger:4318"
    assert config.service_name == "test-service"


def test_bool_config_parsing():
    """Test boolean configuration parsing."""
    config1 = TracerConfig(capture_arguments="true")
    assert config1.capture_arguments is True

    config2 = TracerConfig(capture_arguments="false")
    assert config2.capture_arguments is False

    config3 = TracerConfig(capture_arguments="1")
    assert config3.capture_arguments is True

    config4 = TracerConfig(capture_arguments=True)
    assert config4.capture_arguments is True


# --- Config file tests ---


def test_config_file_loading(tmp_path, monkeypatch):
    """Test loading configuration from .rf-tracer.json file."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "service_name": "file-service",
                "endpoint": "http://file-endpoint:4318/v1/traces",
                "capture_logs": True,
                "log_level": "DEBUG",
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.service_name == "file-service"
    assert config.endpoint == "http://file-endpoint:4318/v1/traces"
    assert config.capture_logs is True
    assert config.log_level == "DEBUG"


def test_config_file_output_section(tmp_path, monkeypatch):
    """Test nested output section in config file."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "output": {
                    "file": "auto",
                    "format": "gz",
                    "filter": "minimal",
                },
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.trace_output_file == "auto"
    assert config.trace_output_format == "gz"
    assert config.trace_output_filter == "minimal"


def test_config_file_precedence_env_over_file(tmp_path, monkeypatch):
    """Test that env vars take precedence over config file."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "service_name": "file-service",
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OTEL_SERVICE_NAME", "env-service")
    config = TracerConfig()
    assert config.service_name == "env-service"


def test_config_file_precedence_kwargs_over_file(tmp_path, monkeypatch):
    """Test that kwargs take precedence over config file."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "service_name": "file-service",
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig(service_name="kwarg-service")
    assert config.service_name == "kwarg-service"


def test_config_file_via_env_var(tmp_path, monkeypatch):
    """Test loading config file via RF_TRACER_CONFIG env var."""
    config_file = tmp_path / "custom-config.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "service_name": "custom-service",
                "span_prefix_style": "emoji",
            }
        )
    )
    monkeypatch.setenv("RF_TRACER_CONFIG", str(config_file))
    config = TracerConfig()
    assert config.service_name == "custom-service"
    assert config.span_prefix_style == "emoji"


def test_config_file_invalid_version(tmp_path, monkeypatch):
    """Test that invalid version in config file is rejected."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "2.0.0",
                "service_name": "bad-version",
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.service_name == "rf"  # Falls back to default


def test_config_file_invalid_json(tmp_path, monkeypatch):
    """Test that invalid JSON in config file is handled gracefully."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text("not valid json {{{")
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.service_name == "rf"  # Falls back to default


def test_config_file_schema_validation_error(tmp_path, monkeypatch):
    """Test that schema validation errors are handled gracefully."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "sample_rate": 5.0,  # Invalid: max is 1.0
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.sample_rate == 1.0  # Falls back to default


def test_config_file_not_found(tmp_path, monkeypatch):
    """Test that missing config file is handled gracefully."""
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.service_name == "rf"  # Default


def test_config_file_bool_values(tmp_path, monkeypatch):
    """Test boolean values from config file."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "capture_arguments": False,
                "capture_logs": True,
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.capture_arguments is False
    assert config.capture_logs is True


def test_config_file_numeric_values(tmp_path, monkeypatch):
    """Test numeric values from config file."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "max_arg_length": 500,
                "sample_rate": 0.5,
                "max_log_length": 1000,
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.max_arg_length == 500
    assert config.sample_rate == 0.5
    assert config.max_log_length == 1000


def test_config_file_invalid_enum(tmp_path, monkeypatch):
    """Test that invalid enum values are rejected by schema validation."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "protocol": "websocket",  # Invalid: must be http or grpc
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.protocol == "http"  # Falls back to default


def test_config_file_additional_properties_rejected(tmp_path, monkeypatch):
    """Test that unknown properties are rejected by schema validation."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "service_name": "test",
                "unknown_field": "should fail",
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.service_name == "rf"  # Falls back to default (file rejected)


def test_config_file_all_validation_errors_reported(tmp_path, monkeypatch, capsys):
    """Test that all validation errors are reported, not just the first."""
    config_file = tmp_path / ".rf-tracer.json"
    config_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "protocol": "websocket",
                "log_level": "VERBOSE",
                "sample_rate": 5.0,
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    captured = capsys.readouterr()
    assert "validation errors" in captured.out
    assert config.protocol == "http"  # Falls back to default


def test_endpoints_list_from_config_file(tmp_path, monkeypatch):
    """Test that endpoints list is read from config file."""
    (tmp_path / ".rf-tracer.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "endpoints": [
                    "http://jaeger:4318/v1/traces",
                    "http://tempo:4318/v1/traces",
                ],
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    config = TracerConfig()
    assert config.endpoints == [
        "http://jaeger:4318/v1/traces",
        "http://tempo:4318/v1/traces",
    ]


def test_endpoints_empty_by_default():
    """Test that endpoints is empty list when not in config file."""
    config = TracerConfig()
    assert config.endpoints == []
