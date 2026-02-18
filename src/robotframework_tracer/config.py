import os


class TracerConfig:
    """Configuration for the Robot Framework tracer."""

    def __init__(self, **kwargs):
        self.endpoint = self._get_config(
            "endpoint", kwargs, "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
        )
        self.service_name = self._get_config("service_name", kwargs, "OTEL_SERVICE_NAME", "rf")
        self.protocol = self._get_config("protocol", kwargs, "RF_TRACER_PROTOCOL", "http")
        self.capture_arguments = self._get_bool_config(
            "capture_arguments", kwargs, "RF_TRACER_CAPTURE_ARGUMENTS", True
        )
        self.max_arg_length = int(
            self._get_config("max_arg_length", kwargs, "RF_TRACER_MAX_ARG_LENGTH", "200")
        )
        self.capture_logs = self._get_bool_config(
            "capture_logs", kwargs, "RF_TRACER_CAPTURE_LOGS", False
        )
        self.log_level = self._get_config(
            "log_level", kwargs, "RF_TRACER_LOG_LEVEL", "INFO"
        ).upper()
        self.max_log_length = int(
            self._get_config("max_log_length", kwargs, "RF_TRACER_MAX_LOG_LENGTH", "500")
        )
        self.sample_rate = float(
            self._get_config("sample_rate", kwargs, "RF_TRACER_SAMPLE_RATE", "1.0")
        )
        self.span_prefix_style = self._get_config(
            "span_prefix_style", kwargs, "RF_TRACER_SPAN_PREFIX_STYLE", "none"
        ).lower()
        self.trace_output_file = self._get_config(
            "trace_output_file", kwargs, "RF_TRACER_OUTPUT_FILE", ""
        )
        self.trace_output_format = self._get_config(
            "trace_output_format", kwargs, "RF_TRACER_OUTPUT_FORMAT", "json"
        ).lower()
        self.trace_output_filter = self._get_config(
            "trace_output_filter", kwargs, "RF_TRACER_OUTPUT_FILTER", ""
        )

    def _get_config(self, key, kwargs, env_var, default):
        """Get configuration value with precedence: kwargs > env > default."""
        return kwargs.get(key, os.environ.get(env_var, default))

    def _get_bool_config(self, key, kwargs, env_var, default):
        """Get boolean configuration value."""
        value = self._get_config(key, kwargs, env_var, str(default))
        if isinstance(value, bool):
            return value
        return value.lower() in ("true", "1", "yes")

    @staticmethod
    def from_listener_args(*args):
        """Parse listener arguments from Robot Framework.

        Args can be passed as:
        - Single string: "endpoint=http://localhost:4318,service_name=my-service"
        - Multiple strings: "endpoint=http://localhost:4318", "service_name=my-service"
        """
        kwargs = {}
        for arg in args:
            if "=" in arg:
                for pair in arg.split(","):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        kwargs[key.strip()] = value.strip()
        return TracerConfig(**kwargs)
