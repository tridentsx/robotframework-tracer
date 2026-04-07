import base64
import gzip
import json
import os
import platform
import re
import sys

# Platform-specific file locking (Unix only, Windows skips locking)
if sys.platform != "win32":
    import fcntl

    def _lock_file(fd):
        fcntl.flock(fd, fcntl.LOCK_EX)

    def _unlock_file(fd):
        fcntl.flock(fd, fcntl.LOCK_UN)

else:
    # Windows: skip file locking (msvcrt.locking is too finicky for this use case)
    def _lock_file(fd):
        pass

    def _unlock_file(fd):
        pass


import robot
from google.protobuf.json_format import MessageToDict

# Import metrics API
from opentelemetry import metrics, trace
from opentelemetry.context import attach, detach
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPExporter
from opentelemetry.propagate import extract, inject

# Import logs API
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.semconv.resource import ResourceAttributes

from .config import TracerConfig
from .output_filter import apply_filter, load_filter
from .span_builder import SpanBuilder
from .version import __version__

# Try to import Robot Framework BuiltIn library for variable setting
try:
    from robot.libraries.BuiltIn import BuiltIn

    BUILTIN_AVAILABLE = True
except ImportError:
    BUILTIN_AVAILABLE = False

# Try to import gRPC exporters (optional dependency)
try:
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter as GRPCMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter as GRPCExporter,
    )

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False


class _OtlpJsonFileExporter(SpanExporter):
    """Write spans as OTLP-compatible JSON — one ExportTraceServiceRequest per batch."""

    def __init__(self, out, output_filter=None):
        self._out = out
        self._filter = output_filter

    @staticmethod
    def _fix_byte_ids(d):
        """Convert base64-encoded trace/span IDs to hex strings."""
        for rs in d.get("resource_spans", []):
            for ss in rs.get("scope_spans", []):
                for span in ss.get("spans", []):
                    for field in ("trace_id", "span_id", "parent_span_id"):
                        if field in span and isinstance(span[field], str):
                            span[field] = base64.b64decode(span[field]).hex()
        return d

    def export(self, spans):
        pb = encode_spans(spans)
        d = MessageToDict(pb, preserving_proto_field_name=True)
        d = self._fix_byte_ids(d)
        d = apply_filter(d, self._filter)
        line = json.dumps(d, separators=(",", ":")) + "\n"
        fd = self._out.fileno()
        _lock_file(fd)
        try:
            self._out.write(line)
            self._out.flush()
        finally:
            _unlock_file(fd)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


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

        self.tracer = None
        self._provider = None
        self.logger_provider = None
        self.logger = None
        self.meter_provider = None
        self.metrics = {}
        self.span_stack = []
        self._context_tokens = []  # Parallel to span_stack for OTel context attach/detach
        self._skipped_keywords = 0
        self.parent_context = self._extract_parent_context()
        self.is_pabot_run = os.environ.get("TRACEPARENT", "") != ""
        self.suite_span = None
        self._trace_file = None
        self._file_processor = None
        self._gz_final_path = None
        self._in_log_message = False  # Prevent recursion
        self._auto_service = self.config.service_name == "auto"
        self._suite_depth = 0

        # Defer provider init when service_name=auto (resolved in start_suite)
        if not self._auto_service:
            self._init_providers(self.config.service_name)

        # If an explicit file path is given, open it now
        if self.config.trace_output_file and self.config.trace_output_file != "auto":
            self._open_trace_file(self.config.trace_output_file)

    def _init_providers(self, service_name):
        """Initialize OpenTelemetry tracer, logs, and metrics providers.

        When service_name=auto, this may be called multiple times (once per suite).
        The exporter, processor, and logger provider are created once and reused.
        Only the TracerProvider changes per suite (for the service name resource).
        """
        # Flush spans from previous suite before switching provider
        if self._provider:
            try:
                self._provider.force_flush()
            except Exception:
                pass

        resource_attrs = {
            SERVICE_NAME: service_name,
            ResourceAttributes.TELEMETRY_SDK_NAME: "robotframework-tracer",
            ResourceAttributes.TELEMETRY_SDK_LANGUAGE: "python",
            ResourceAttributes.TELEMETRY_SDK_VERSION: __version__,
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

        use_grpc = self.config.protocol == "grpc" and GRPC_AVAILABLE

        # Create exporter and processor once, reuse across all suites.
        # This avoids gRPC channel churn and thread leaks from creating
        # new BatchSpanProcessors per suite.
        if not hasattr(self, "_trace_processors"):
            self._trace_processors = []
            endpoints = self.config.endpoints if self.config.endpoints else [self.config.endpoint]
            for ep in endpoints:
                if self.config.protocol == "grpc":
                    if not GRPC_AVAILABLE:
                        print(
                            "Warning: gRPC exporters not available. Install with: pip install robotframework-tracer[grpc]"
                        )
                        print("Falling back to HTTP exporters")
                        exporter = HTTPExporter(endpoint=ep)
                    else:
                        exporter = GRPCExporter(endpoint=ep)
                else:
                    exporter = HTTPExporter(endpoint=ep)
                self._trace_processors.append(BatchSpanProcessor(exporter))

        for proc in self._trace_processors:
            provider.add_span_processor(proc)
        self._provider = provider

        # Only set global provider once; subsequent calls use instance provider directly
        if not hasattr(self, "_global_provider_set"):
            trace.set_tracer_provider(provider)
            self._global_provider_set = True

        self.tracer = self._provider.get_tracer(__name__)

        # Initialize logs provider once and reuse across suites.
        # Reinitializing per suite adds flush/shutdown overhead that causes
        # gRPC trace exports to be dropped in rapid auto-mode cycling.
        # Logs are correlated via trace_id/span_id, not service.name.
        if self.config.capture_logs and self.logger_provider is None:
            http_base = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", self.config.endpoint)
            logs_endpoint = http_base.replace("/v1/traces", "/v1/logs")
            if logs_endpoint == http_base:
                logs_endpoint = f"{http_base.rstrip('/')}/v1/logs"
            log_exporter = OTLPLogExporter(endpoint=logs_endpoint)

            self.logger_provider = LoggerProvider(resource=resource)
            self.logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

            from opentelemetry._logs import set_logger_provider

            set_logger_provider(self.logger_provider)
            self.logger = self.logger_provider.get_logger(__name__)

        # Initialize metrics provider once and reuse across suites.
        if self.config.capture_metrics and self.meter_provider is None:
            if use_grpc:
                metric_exporter = GRPCMetricExporter(endpoint=self.config.endpoint)
            else:
                metrics_endpoint = self.config.endpoint.replace("/v1/traces", "/v1/metrics")
                if metrics_endpoint == self.config.endpoint:
                    base_url = self.config.endpoint.rstrip("/")
                    metrics_endpoint = f"{base_url}/v1/metrics"
                metric_exporter = OTLPMetricExporter(endpoint=metrics_endpoint)
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter, export_interval_millis=5000
            )
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            if not hasattr(self, "_global_meter_provider_set"):
                metrics.set_meter_provider(self.meter_provider)
                self._global_meter_provider_set = True

            meter = self.meter_provider.get_meter(__name__)

            self.metrics = {
                "tests_total": meter.create_counter(
                    "rf.tests.total", description="Total number of tests executed", unit="1"
                ),
                "tests_passed": meter.create_counter(
                    "rf.tests.passed", description="Number of tests that passed", unit="1"
                ),
                "tests_failed": meter.create_counter(
                    "rf.tests.failed", description="Number of tests that failed", unit="1"
                ),
                "tests_skipped": meter.create_counter(
                    "rf.tests.skipped", description="Number of tests that were skipped", unit="1"
                ),
                "test_duration": meter.create_histogram(
                    "rf.test.duration", description="Test execution duration", unit="ms"
                ),
                "suite_duration": meter.create_histogram(
                    "rf.suite.duration", description="Suite execution duration", unit="ms"
                ),
                "keywords_executed": meter.create_counter(
                    "rf.keywords.executed",
                    description="Total number of keywords executed",
                    unit="1",
                ),
                "keyword_duration": meter.create_histogram(
                    "rf.keyword.duration", description="Keyword execution duration", unit="ms"
                ),
            }

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
                if (
                    value in ("http", "https")
                    and i + 1 < len(args)
                    and args[i + 1].startswith("//")
                ):
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

    @staticmethod
    def _extract_parent_context():
        """Extract parent trace context from W3C environment variables.

        Reads TRACEPARENT (and optionally TRACESTATE) from the environment
        to establish a parent-child relationship with an external trace.
        This enables trace correlation with CI pipelines, wrapper scripts,
        and parallel execution tools like pabot.

        Returns:
            OpenTelemetry context with parent span, or None if not set.
        """
        traceparent = os.environ.get("TRACEPARENT", "")
        if not traceparent:
            return None

        carrier = {"traceparent": traceparent}
        tracestate = os.environ.get("TRACESTATE", "")
        if tracestate:
            carrier["tracestate"] = tracestate

        return extract(carrier)

    def _open_trace_file(self, filepath):
        """Open a trace output file and attach a compact JSON exporter to the provider.

        For gz format, each process writes to its own temporary JSON file, then
        compresses and appends to the final .gz file in close(). This avoids
        corruption from concurrent gzip writes with pabot.
        """
        try:
            if self.config.trace_output_format == "gz":
                # Ensure the final path ends with .gz
                if not filepath.endswith(".gz"):
                    filepath = filepath + ".gz"
                self._gz_final_path = filepath
                # Clean up stale .tmp files from previous crashed runs
                self._cleanup_stale_tmp_files(filepath)
                # Each process writes to its own temp file (PID-based)
                json_path = f"{filepath[: -len('.gz')]}.{os.getpid()}.tmp"
                self._trace_file = open(json_path, "a")
            else:
                self._trace_file = open(filepath, "a")
            output_filter = load_filter(self.config.trace_output_filter)
            file_exporter = _OtlpJsonFileExporter(out=self._trace_file, output_filter=output_filter)
            self._file_processor = BatchSpanProcessor(file_exporter)
            self._provider.add_span_processor(self._file_processor)
            print(f"Trace output file: {filepath}")
            if output_filter:
                print(f"Trace output filter: {self.config.trace_output_filter}")
        except Exception as e:
            print(f"Warning: Failed to open trace output file '{filepath}': {e}")
            self._trace_file = None

    @staticmethod
    def _cleanup_stale_tmp_files(gz_path):
        """Remove .tmp files left behind by crashed processes.

        Only removes files whose PID is no longer running to avoid
        interfering with concurrent pabot workers.
        """
        import glob

        pattern = gz_path[: -len(".gz")] + ".*.tmp"
        for tmp_file in glob.glob(pattern):
            try:
                # Extract PID from filename: ....<pid>.tmp
                pid_str = tmp_file.rsplit(".", 2)[-2]
                pid = int(pid_str)
                # Check if the process is still alive
                try:
                    os.kill(pid, 0)
                except OSError:
                    # Process is dead — safe to remove
                    os.remove(tmp_file)
            except (ValueError, IndexError, OSError):
                pass

    @staticmethod
    def _sanitize_filename(name):
        """Convert a suite name to a safe filename component."""
        # Replace spaces and non-alphanumeric chars with underscores
        safe = re.sub(r"[^\w]+", "_", name).strip("_").lower()
        return safe or "trace"

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
            self._suite_depth += 1

            # In auto mode, reinitialize provider per child suite so each
            # becomes its own service in the backend (e.g. SigNoz).
            # Depth 1 = root suite (directory), depth 2+ = actual test suites.
            if self._auto_service:
                if self._suite_depth == 1:
                    if data.tests:
                        # Single suite run (e.g. robot tests/jenkins/) — init now
                        self._init_providers(data.name)
                    else:
                        # Root wrapper suite (e.g. robot tests/) — skip span,
                        # will init per child suite at depth 2
                        return
                elif self._suite_depth == 2:
                    self._init_providers(data.name)
            elif not self.tracer:
                self._init_providers(self.config.service_name)

            # Attach parent context if this is the root suite (no spans yet)
            if self.parent_context and not self.span_stack:
                token = attach(self.parent_context)
                self._context_tokens.append(token)

            # Parent context is already current via attach, so tracer.start_span
            # automatically picks up the parent from the OTel context.
            if self.span_stack:
                span = SpanBuilder.create_suite_span(
                    self.tracer,
                    data,
                    result,
                    self.config.span_prefix_style,
                )
            else:
                span = SpanBuilder.create_suite_span(
                    self.tracer,
                    data,
                    result,
                    self.config.span_prefix_style,
                    parent_context=self.parent_context,
                )
            self.span_stack.append(span)
            self.suite_span = span

            # Attach the new span as current in OTel context
            ctx = trace.set_span_in_context(span)
            token = attach(ctx)
            self._context_tokens.append(token)

            # Auto-generate trace output filename on first suite span
            if self.config.trace_output_file == "auto" and self._trace_file is None:
                trace_id = format(span.get_span_context().trace_id, "032x")
                suite_name = self._sanitize_filename(data.name)
                ext = "json.gz" if self.config.trace_output_format == "gz" else "json"
                filename = f"{suite_name}_{trace_id[:8]}_traces.{ext}"
                self._open_trace_file(filename)
        except Exception as e:
            print(f"TracingListener error in start_suite: {e}")

    def end_suite(self, data, result):
        """Close suite span."""
        try:
            # In auto mode, root wrapper suite has no span — skip
            if self._auto_service and self._suite_depth == 1 and not data.tests:
                self._suite_depth -= 1
                return

            # Get trace_id BEFORE ending the span
            trace_id = "unknown"
            if self.span_stack:
                span = self.span_stack[-1]  # Peek at span before popping
                if span.is_recording():
                    span_context = span.get_span_context()
                    trace_id = format(span_context.trace_id, "032x")

                span = self.span_stack.pop()
                SpanBuilder.set_span_status(span, result)
                span.end()

            # Detach the context token for this suite span
            if self._context_tokens:
                detach(self._context_tokens.pop())

            # Emit suite metrics
            if self.metrics:
                self.metrics["suite_duration"].record(
                    result.elapsedtime,
                    {"suite": result.name, "status": result.status, "trace_id": trace_id},
                )

            # Flush metrics immediately when the test suite ends — pabot may
            # kill the worker before close() is called.
            if self.meter_provider:
                try:
                    self.meter_provider.force_flush()
                except Exception:
                    pass

            self._suite_depth -= 1

        except Exception as e:
            print(f"TracingListener error in end_suite: {e}")

    def start_test(self, data, result):
        """Create child span for test case."""
        try:
            # For pabot runs: rename suite span to include test name
            # and emit a signal span for live visibility in trace viewers.
            if self.is_pabot_run and self.suite_span:
                self.suite_span.update_name(f"{self.suite_span.name} - {data.name}")

            # Parent context is already current via attach, so tracer.start_span
            # automatically picks up the parent from the OTel context.
            span = SpanBuilder.create_test_span(
                self.tracer, data, result, None, self.config.span_prefix_style
            )
            self.span_stack.append(span)

            # Attach the new span as current in OTel context
            ctx = trace.set_span_in_context(span)
            token = attach(ctx)
            self._context_tokens.append(token)

            # For pabot runs: emit a signal span under the wrapper span
            # so it appears in trace viewer before the test finishes.
            if self.is_pabot_run and self.parent_context:
                with self.tracer.start_span(
                    f"Test Starting: {data.name}",
                    context=self.parent_context,
                ) as signal:
                    signal.set_attribute("rf.test.name", data.name)
                    signal.set_attribute("rf.signal", "test.starting")
                # No force_flush — BatchSpanProcessor exports within ~5s

            # Set trace context variables (now works because span is current via attach)
            self._set_trace_context_variables()

        except Exception as e:
            print(f"TracingListener error in start_test: {e}")

    def end_test(self, data, result):
        """Close test span with verdict."""
        try:
            # Get trace_id BEFORE ending the span
            trace_id = "unknown"
            if self.span_stack:
                span = self.span_stack[-1]  # Peek at span before popping
                if span.is_recording():
                    span_context = span.get_span_context()
                    trace_id = format(span_context.trace_id, "032x")

                span = self.span_stack.pop()
                SpanBuilder.set_span_status(span, result)
                if result.status == "FAIL":
                    SpanBuilder.add_error_event(span, result)
                span.end()

            # Detach the context token for this test span
            if self._context_tokens:
                detach(self._context_tokens.pop())

            # Emit test metrics
            if self.metrics:
                suite_name = result.parent.name if hasattr(result, "parent") else "unknown"
                base_attrs = {"suite": suite_name, "trace_id": trace_id}

                self.metrics["tests_total"].add(1, base_attrs)

                if result.status == "PASS":
                    self.metrics["tests_passed"].add(1, base_attrs)
                elif result.status == "FAIL":
                    attrs = base_attrs.copy()
                    if hasattr(result, "tags") and result.tags:
                        attrs["tags"] = ",".join(str(t) for t in list(result.tags)[:5])
                    self.metrics["tests_failed"].add(1, attrs)
                elif result.status == "SKIP":
                    self.metrics["tests_skipped"].add(1, base_attrs)

                # Record test duration
                duration_attrs = base_attrs.copy()
                duration_attrs["status"] = result.status
                self.metrics["test_duration"].record(result.elapsedtime, duration_attrs)

        except Exception as e:
            print(f"TracingListener error in end_test: {e}")

    def start_keyword(self, data, result):
        """Create child span for keyword/step."""
        try:
            if not self.config.capture_arguments and data.args:
                self._skipped_keywords += 1
                return

            # Parent context is already current via attach, so tracer.start_span
            # automatically picks up the parent from the OTel context.
            span = SpanBuilder.create_keyword_span(
                self.tracer,
                data,
                result,
                None,
                self.config.max_arg_length,
                self.config.span_prefix_style,
            )
            self.span_stack.append(span)

            # Attach the new span as current in OTel context
            ctx = trace.set_span_in_context(span)
            token = attach(ctx)
            self._context_tokens.append(token)

            # Add event for setup/teardown start
            if data.type in ("SETUP", "TEARDOWN"):
                span.add_event(f"{data.type.lower()}.start", {"keyword": data.name})
        except Exception as e:
            print(f"TracingListener error in start_keyword: {e}")

    def end_keyword(self, data, result):
        """Close keyword span."""
        try:
            if self._skipped_keywords > 0:
                self._skipped_keywords -= 1
                return

            # Get trace_id BEFORE ending the span
            trace_id = "unknown"
            if self.span_stack:
                span = self.span_stack[-1]  # Peek at span before popping
                if span.is_recording():
                    span_context = span.get_span_context()
                    trace_id = format(span_context.trace_id, "032x")

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

            # Detach the context token for this keyword span
            if self._context_tokens:
                detach(self._context_tokens.pop())

            # Emit keyword metrics
            if self.metrics:
                self.metrics["keywords_executed"].add(1, {"type": data.type, "trace_id": trace_id})
                self.metrics["keyword_duration"].record(
                    result.elapsedtime,
                    {"type": data.type, "status": result.status, "trace_id": trace_id},
                )

        except Exception as e:
            print(f"TracingListener error in end_keyword: {e}")

    def close(self):
        """Cleanup on listener close."""
        # Flush metrics FIRST — with pabot, file lock contention in later
        # steps can delay or prevent this if done last.
        try:
            if self.meter_provider:
                self.meter_provider.force_flush()
                self.meter_provider.shutdown()
        except Exception as e:
            print(f"TracingListener error shutting down metrics: {e}")

        try:
            while self.span_stack:
                span = self.span_stack.pop()
                span.end()
            # Detach any remaining context tokens
            while self._context_tokens:
                detach(self._context_tokens.pop())
        except Exception as e:
            print(f"TracingListener error ending spans in close: {e}")

        try:
            if self._provider:
                self._provider.force_flush()
                self._provider.shutdown()
        except Exception as e:
            print(f"TracingListener error flushing tracer: {e}")

        # Shut down the file processor before closing the file to ensure
        # all buffered spans are written and the background thread stops.
        if self._file_processor:
            try:
                self._file_processor.force_flush()
                self._file_processor.shutdown()
            except Exception as e:
                print(f"TracingListener error shutting down file processor: {e}")

        # Always close the trace file so all data is flushed to disk.
        self._trace_file_path = None
        if self._trace_file:
            try:
                self._trace_file_path = self._trace_file.name
                self._trace_file.close()
            except Exception as e:
                print(f"TracingListener error closing trace file: {e}")
            self._trace_file = None

        # Compress the process-local temp JSON file and append to the shared
        # .gz file. Each pabot worker compresses only its own data, using a
        # file lock on the gz file to serialize appends. The result is a valid
        # multi-member gzip file (concatenated gzip streams are valid per RFC 1952).
        if self._gz_final_path and self._trace_file_path:
            try:
                with open(self._trace_file_path, "rb") as f_in:
                    data = f_in.read()
                if data:
                    # Use a lock file to serialize gz appends across processes
                    lock_path = self._gz_final_path + ".lock"
                    lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT)
                    try:
                        _lock_file(lock_fd)
                        with gzip.open(self._gz_final_path, "ab") as f_out:
                            f_out.write(data)
                    finally:
                        _unlock_file(lock_fd)
                        os.close(lock_fd)
                        try:
                            os.remove(lock_path)
                        except OSError:
                            pass  # Another process may still need it
                os.remove(self._trace_file_path)
            except Exception as e:
                print(f"TracingListener error compressing trace file: {e}")
            self._gz_final_path = None

        try:
            if self.logger_provider:
                self.logger_provider.force_flush()
        except Exception as e:
            print(f"TracingListener error flushing logs: {e}")

    def log_message(self, message):
        """Capture log messages and send to logs API."""
        if self._in_log_message:
            return  # Prevent recursion

        self._in_log_message = True
        try:
            if not self.config.capture_logs or not self.logger:
                return

            # Filter by log level
            log_levels = {"TRACE": 0, "DEBUG": 1, "INFO": 2, "WARN": 3, "ERROR": 4, "FAIL": 5}
            min_level = log_levels.get(self.config.log_level, 2)
            msg_level = log_levels.get(message.level, 2)

            if msg_level < min_level:
                return

            # Limit message length
            log_text = message.message
            if len(log_text) > self.config.max_log_length:
                log_text = log_text[: self.config.max_log_length] + "..."

            # Map RF log levels to OTel severity
            severity_map = {
                "TRACE": 1,
                "DEBUG": 5,
                "INFO": 9,
                "WARN": 13,
                "ERROR": 17,
                "FAIL": 21,
            }
            severity_number = severity_map.get(message.level, 9)

            # Get trace context for correlation
            log_context = None
            if self.span_stack:
                # Use the current span's context
                log_context = trace.set_span_in_context(self.span_stack[-1])

            # Emit log using logger API
            self.logger.emit(
                body=log_text,
                severity_number=severity_number,
                severity_text=message.level,
                context=log_context,
                attributes={
                    "rf.log.level": message.level,
                },
            )

        except RecursionError:
            # Avoid infinite recursion if logging causes more logs
            pass
        except Exception:
            # Silently ignore errors in log capture to avoid breaking tests
            pass
        finally:
            self._in_log_message = False
