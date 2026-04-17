import json
import os
from pathlib import Path

from .screenshot import ScreenshotConfig

# Config file search names (checked in order)
CONFIG_FILE_NAMES = [".rf-tracer.json", "rf-tracer.json"]


def _find_config_file():
    """Find config file in current directory or via env var.

    Search order:
    1. RF_TRACER_CONFIG env var (explicit path)
    2. .rf-tracer.json in current directory
    3. rf-tracer.json in current directory
    """
    env_path = os.environ.get("RF_TRACER_CONFIG", "")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        print(f"Warning: RF_TRACER_CONFIG points to non-existent file: {env_path}")
        return None

    for name in CONFIG_FILE_NAMES:
        p = Path(name)
        if p.is_file():
            return p
    return None


def _load_config_file(path):
    """Load and validate a config JSON file. Returns dict or empty dict on error."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load config file '{path}': {e}")
        return {}

    if not isinstance(data, dict):
        print(f"Warning: Config file '{path}' must be a JSON object")
        return {}

    # Validate version
    version = data.get("version", "")
    if not version or not version.startswith("1."):
        print(f"Warning: Config file '{path}' has unsupported version: {version}")
        return {}

    # Validate with JSON Schema if jsonschema is installed
    schema_path = Path(__file__).parent / "schemas" / "config-v1.json"
    if schema_path.is_file():
        try:
            import jsonschema

            with open(schema_path) as f:
                schema = json.load(f)
            validator = jsonschema.Draft7Validator(schema)
            errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
            if errors:
                print(f"Warning: Config file '{path}' validation errors:")
                for error in errors:
                    err_path = ".".join(str(p) for p in error.absolute_path) or "(root)"
                    print(f"  - {err_path}: {error.message}")
                print("Config file will be ignored.")
                return {}
        except ImportError:
            pass  # jsonschema not installed, skip validation

    return data


def _flatten_config_file(data):
    """Flatten config file data into a flat key-value dict for TracerConfig.

    Handles the nested 'output' section by mapping:
      output.file   -> trace_output_file
      output.format -> trace_output_format
      output.filter -> trace_output_filter

    The 'screenshots' section is preserved as-is (dict) for ScreenshotConfig.
    """
    flat = {}
    for key, value in data.items():
        if key in ("version", "description"):
            continue
        if key == "output" and isinstance(value, dict):
            if "file" in value:
                flat["trace_output_file"] = value["file"]
            if "format" in value:
                flat["trace_output_format"] = value["format"]
            if "filter" in value:
                flat["trace_output_filter"] = value["filter"]
        elif key == "screenshots" and isinstance(value, dict):
            # Keep as dict — ScreenshotConfig.from_dict() handles it
            flat["screenshots"] = value
        else:
            flat[key] = value
    return flat


class TracerConfig:
    """Configuration for the Robot Framework tracer.

    Precedence (highest to lowest):
    1. Listener arguments (kwargs)
    2. Environment variables
    3. Config file (.rf-tracer.json)
    4. Defaults
    """

    def __init__(self, **kwargs):
        # Load config file (lowest precedence, above defaults)
        self._file_config = {}
        config_path = _find_config_file()
        if config_path:
            raw = _load_config_file(config_path)
            if raw:
                self._file_config = _flatten_config_file(raw)
                print(f"Loaded config from: {config_path}")

        self.endpoint = self._get_config(
            "endpoint", kwargs, "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
        )
        # Multi-endpoint support (config file only)
        self.endpoints = self._file_config.get("endpoints", [])
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
        self.capture_metrics = self._get_bool_config(
            "capture_metrics", kwargs, "RF_TRACER_CAPTURE_METRICS", True
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

        # Screenshot capture config (from 'screenshots' section in config file)
        screenshots_dict = self._file_config.get("screenshots", {})
        # Allow env var override for mode
        env_mode = os.environ.get("RF_TRACER_SCREENSHOT_MODE", "")
        if env_mode:
            screenshots_dict = dict(screenshots_dict)  # copy to avoid mutating
            screenshots_dict["mode"] = env_mode
        # Allow listener kwarg override for mode
        if "screenshot_mode" in kwargs:
            screenshots_dict = dict(screenshots_dict)
            screenshots_dict["mode"] = kwargs["screenshot_mode"]
        self.screenshots = ScreenshotConfig.from_dict(screenshots_dict)

    def _get_config(self, key, kwargs, env_var, default):
        """Get config value. Precedence: kwargs > env > config file > default."""
        if key in kwargs:
            return kwargs[key]
        env_val = os.environ.get(env_var)
        if env_val is not None:
            return env_val
        if key in self._file_config:
            val = self._file_config[key]
            return str(val) if not isinstance(val, str) else val
        return default

    def _get_bool_config(self, key, kwargs, env_var, default):
        """Get boolean config value. Precedence: kwargs > env > config file > default."""
        if key in kwargs:
            value = kwargs[key]
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes")
        env_val = os.environ.get(env_var)
        if env_val is not None:
            return env_val.lower() in ("true", "1", "yes")
        if key in self._file_config:
            value = self._file_config[key]
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "1", "yes")
        return default

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
