from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased
from opentelemetry.semconv.resource import ResourceAttributes
import platform
import sys
import robot

from .config import TracerConfig
from .span_builder import SpanBuilder

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

    def __init__(
        self,
        endpoint=None,
        service_name=None,
        protocol=None,
        capture_arguments=None,
        max_arg_length=None,
        capture_logs=None,
        sample_rate=None,
        span_prefix_style=None,
        log_level=None,
        max_log_length=None,
    ):
        """Initialize the tracing listener.

        Args:
            endpoint: OTLP endpoint URL
            service_name: Service name for traces
            protocol: Protocol (http or grpc)
            capture_arguments: Whether to capture keyword arguments
            max_arg_length: Maximum length for arguments
            capture_logs: Whether to capture log messages
            sample_rate: Sampling rate (0.0-1.0)
            span_prefix_style: Span prefix style (none, text, emoji)
            log_level: Minimum log level to capture (DEBUG, INFO, WARN, ERROR)
            max_log_length: Maximum length for log messages
        """
        # Build kwargs dict from provided arguments
        kwargs = {}
        if endpoint is not None:
            kwargs["endpoint"] = endpoint
        if service_name is not None:
            kwargs["service_name"] = service_name
        if protocol is not None:
            kwargs["protocol"] = protocol
        if capture_arguments is not None:
            kwargs["capture_arguments"] = capture_arguments
        if max_arg_length is not None:
            kwargs["max_arg_length"] = max_arg_length
        if capture_logs is not None:
            kwargs["capture_logs"] = capture_logs
        if sample_rate is not None:
            kwargs["sample_rate"] = sample_rate
        if span_prefix_style is not None:
            kwargs["span_prefix_style"] = span_prefix_style
        if log_level is not None:
            kwargs["log_level"] = log_level
        if max_log_length is not None:
            kwargs["max_log_length"] = max_log_length

        self.config = TracerConfig(**kwargs)

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
