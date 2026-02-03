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
