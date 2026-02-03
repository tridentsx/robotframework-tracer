import platform
import sys

import robot
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPExporter
from opentelemetry.propagate import inject
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.semconv.resource import ResourceAttributes

from .config import TracerConfig
from .span_builder import SpanBuilder

# Try to import Robot Framework BuiltIn library for variable setting
try:
    from robot.libraries.BuiltIn import BuiltIn

    BUILTIN_AVAILABLE = True
except ImportError:
    BUILTIN_AVAILABLE = False

# Try to import gRPC exporter (optional dependency)
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter as GRPCExporter,
    )

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False


class TracingListener:
    """Robot Framework Listener v3 for distributed tracing."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, *args):
        """Initialize the tracing listener.

        Args are colon-separated key=value pairs from Robot Framework.
        Example: robot --listener "TracingListener:service_name=test:capture_logs=true"

        For URLs with colons, they are automatically reconstructed:
        Example: robot --listener "TracingListener:endpoint=http://host:4318/v1/traces"

        Recommended: Use environment variables for endpoints:
            OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
            OTEL_SERVICE_NAME=my-tests
        """
        parsed_kwargs = self._parse_listener_args(args)
        self.config = TracerConfig(**parsed_kwargs)

        # Initialize OpenTelemetry with automatic resource detection
        resource_attrs = {
            SERVICE_NAME: self.config.service_name,
            ResourceAttributes.TELEMETRY_SDK_NAME: "robotframework-tracer",
            ResourceAttributes.TELEMETRY_SDK_LANGUAGE: "python",
            ResourceAttributes.TELEMETRY_SDK_VERSION: "0.1.0",
            "rf.version": robot.version.get_version(),
            "python.version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            ResourceAttributes.HOST_NAME: platform.node(),
            ResourceAttributes.OS_TYPE: platform.system(),
            ResourceAttributes.OS_VERSION: platform.release(),
        }
        resource = Resource.create(resource_attrs)

        # Configure sampling only if sample_rate < 1.0
        if self.config.sample_rate < 1.0:
            sampler = ParentBased(root=TraceIdRatioBased(self.config.sample_rate))
            provider = TracerProvider(resource=resource, sampler=sampler)
        else:
            provider = TracerProvider(resource=resource)

        # Select exporter based on protocol
        if self.config.protocol == "grpc":
            if not GRPC_AVAILABLE:
                print(
                    "Warning: gRPC exporter not available. Install with: pip install opentelemetry-exporter-otlp-proto-grpc"
                )
                print("Falling back to HTTP exporter")
                exporter = HTTPExporter(endpoint=self.config.endpoint)
            else:
                exporter = GRPCExporter(endpoint=self.config.endpoint)
        else:
            exporter = HTTPExporter(endpoint=self.config.endpoint)

        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        self.tracer = trace.get_tracer(__name__)
        self.span_stack = []

    @staticmethod
    def _parse_listener_args(args):
        """Parse Robot Framework listener arguments.

        RF splits arguments on ':' and passes each as a separate arg.
        Example: 'listener:endpoint=http://host:4318:service_name=test'
        becomes args = ('endpoint=http', '//host', '4318', 'service_name=test')

        This method reconstructs URLs and parses key=value pairs.
        """
        if not args:
            return {}

        kwargs = {}
        i = 0
        while i < len(args):
            arg = args[i]

            if "=" in arg:
                key, value = arg.split("=", 1)
                # Check if value is start of a URL that got split
                if value in ("http", "https") and i + 1 < len(args) and args[i + 1].startswith("//"):
                    # Reconstruct URL: scheme + :// + rest
                    url_parts = [value]
                    i += 1
                    while i < len(args) and "=" not in args[i]:
                        url_parts.append(args[i])
                        i += 1
                    kwargs[key.strip()] = ":".join(url_parts)
                    continue
                else:
                    kwargs[key.strip()] = value.strip()
            i += 1

        return kwargs

    def _set_trace_context_variables(self):
        """Set Robot Framework variables with current trace context."""
        if not BUILTIN_AVAILABLE:
            return

        try:
            # Get current trace context
            headers = {}
            inject(headers)  # Injects traceparent, tracestate headers

            # Get current span info
            current_span = trace.get_current_span()
            trace_id = None
            span_id = None

            if current_span.is_recording():
                span_context = current_span.get_span_context()
                trace_id = format(span_context.trace_id, "032x")
                span_id = format(span_context.span_id, "016x")

            # Set RF variables for different protocols
            builtin = BuiltIn()

            # HTTP headers (for REST APIs, web services)
            builtin.set_test_variable("${TRACE_HEADERS}", headers)

            # Individual trace components (for custom protocols like Diameter)
            if trace_id:
                builtin.set_test_variable("${TRACE_ID}", trace_id)
            if span_id:
                builtin.set_test_variable("${SPAN_ID}", span_id)

            # W3C traceparent format (for manual header construction)
            if headers.get("traceparent"):
                builtin.set_test_variable("${TRACEPARENT}", headers["traceparent"])

            # Tracestate (for vendor-specific data)
            if headers.get("tracestate"):
                builtin.set_test_variable("${TRACESTATE}", headers["tracestate"])

        except Exception:
            # Silently ignore errors to avoid breaking tests
            pass

    def start_suite(self, data, result):
        """Create root span for suite."""
        try:
            span = SpanBuilder.create_suite_span(
                self.tracer, data, result, self.config.span_prefix_style
            )
            self.span_stack.append(span)
        except Exception as e:
            print(f"TracingListener error in start_suite: {e}")

    def end_suite(self, data, result):
        """Close suite span."""
        try:
            if self.span_stack:
                span = self.span_stack.pop()
                SpanBuilder.set_span_status(span, result)
                span.end()
        except Exception as e:
            print(f"TracingListener error in end_suite: {e}")

    def start_test(self, data, result):
        """Create child span for test case."""
        try:
            parent_context = (
                trace.set_span_in_context(self.span_stack[-1]) if self.span_stack else None
            )
            span = SpanBuilder.create_test_span(
                self.tracer, data, result, parent_context, self.config.span_prefix_style
            )
            self.span_stack.append(span)

            # Set trace context variables within the span context
            with trace.use_span(span):
                self._set_trace_context_variables()

        except Exception as e:
            print(f"TracingListener error in start_test: {e}")

    def end_test(self, data, result):
        """Close test span with verdict."""
        try:
            if self.span_stack:
                span = self.span_stack.pop()
                SpanBuilder.set_span_status(span, result)
                if result.status == "FAIL":
                    SpanBuilder.add_error_event(span, result)
                span.end()
        except Exception as e:
            print(f"TracingListener error in end_test: {e}")

    def start_keyword(self, data, result):
        """Create child span for keyword/step."""
        try:
            if not self.config.capture_arguments and data.args:
                return

            parent_context = (
                trace.set_span_in_context(self.span_stack[-1]) if self.span_stack else None
            )
            span = SpanBuilder.create_keyword_span(
                self.tracer,
                data,
                result,
                parent_context,
                self.config.max_arg_length,
                self.config.span_prefix_style,
            )
            self.span_stack.append(span)

            # Add event for setup/teardown start
            if data.type in ("SETUP", "TEARDOWN"):
                span.add_event(f"{data.type.lower()}.start", {"keyword": data.name})
        except Exception as e:
            print(f"TracingListener error in start_keyword: {e}")

    def end_keyword(self, data, result):
        """Close keyword span."""
        try:
            if self.span_stack:
                span = self.span_stack.pop()

                # Add event for setup/teardown end
                if data.type in ("SETUP", "TEARDOWN"):
                    span.add_event(
                        f"{data.type.lower()}.end", {"keyword": data.name, "status": result.status}
                    )

                SpanBuilder.set_span_status(span, result)
                if result.status == "FAIL":
                    SpanBuilder.add_error_event(span, result)
                span.end()
        except Exception as e:
            print(f"TracingListener error in end_keyword: {e}")

    def close(self):
        """Cleanup on listener close."""
        try:
            while self.span_stack:
                span = self.span_stack.pop()
                span.end()
            trace.get_tracer_provider().force_flush()
        except Exception as e:
            print(f"TracingListener error in close: {e}")

    def log_message(self, message):
        """Capture log messages as span events."""
        try:
            if not self.config.capture_logs or not self.span_stack:
                return

            # Filter by log level
            log_levels = {"TRACE": 0, "DEBUG": 1, "INFO": 2, "WARN": 3, "ERROR": 4, "FAIL": 5}
            min_level = log_levels.get(self.config.log_level, 2)
            msg_level = log_levels.get(message.level, 2)

            if msg_level < min_level:
                return

            # Get current span
            current_span = self.span_stack[-1]

            # Limit message length
            log_text = message.message
            if len(log_text) > self.config.max_log_length:
                log_text = log_text[: self.config.max_log_length] + "..."

            # Add log as span event (convert timestamp to string)
            event_attrs = {
                "message": log_text,
                "level": message.level,
            }
            if hasattr(message, "timestamp") and message.timestamp:
                event_attrs["timestamp"] = str(message.timestamp)

            current_span.add_event(f"log.{message.level.lower()}", event_attrs)
        except RecursionError:
            # Avoid infinite recursion if logging causes more logs
            pass
        except Exception:
            # Silently ignore errors in log capture to avoid breaking tests
            pass
