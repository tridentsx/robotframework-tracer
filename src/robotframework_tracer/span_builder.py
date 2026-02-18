import robot
from opentelemetry import baggage, trace
from opentelemetry.trace import Status, StatusCode

from .attributes import AttributeExtractor, RFAttributes


class SpanBuilder:
    """Build OpenTelemetry spans from Robot Framework objects."""

    # Prefix mappings
    TEXT_PREFIXES = {
        "SUITE": "[SUITE]",
        "TEST": "[TEST CASE]",
        "KEYWORD": "[TEST STEP]",
        "SETUP": "[SETUP]",
        "TEARDOWN": "[TEARDOWN]",
    }

    EMOJI_PREFIXES = {
        "SUITE": "📦",
        "TEST": "🧪",
        "KEYWORD": "👟",
        "SETUP": "🔧",
        "TEARDOWN": "🧹",
    }

    @staticmethod
    def _add_prefix(name, span_type, prefix_style):
        """Add prefix to span name based on style."""
        if prefix_style == "none" or not prefix_style:
            return name
        elif prefix_style == "text":
            prefix = SpanBuilder.TEXT_PREFIXES.get(span_type, "")
            return f"{prefix} {name}" if prefix else name
        elif prefix_style == "emoji":
            prefix = SpanBuilder.EMOJI_PREFIXES.get(span_type, "")
            return f"{prefix} {name}" if prefix else name
        return name

    @staticmethod
    def create_suite_span(tracer, data, result, prefix_style="none", parent_context=None):
        """Create root span for test suite.

        Args:
            tracer: OpenTelemetry tracer instance.
            data: Robot Framework suite data object.
            result: Robot Framework suite result object.
            prefix_style: Span name prefix style (none, text, emoji).
            parent_context: Optional parent context from W3C TRACEPARENT env var.
                When provided, the suite span becomes a child of the external parent,
                enabling trace correlation with CI pipelines or parallel runners.
        """
        attrs = AttributeExtractor.from_suite(data, result)
        name = SpanBuilder._add_prefix(data.name, "SUITE", prefix_style)

        # Start from parent context if provided, otherwise create a new root
        ctx = parent_context

        # Add baggage
        ctx = baggage.set_baggage("rf.suite.id", result.id, ctx)
        ctx = baggage.set_baggage("rf.version", robot.version.get_version(), ctx)

        # Add suite metadata to baggage (limit to avoid too much data)
        if hasattr(data, "metadata") and data.metadata:
            for key, value in list(data.metadata.items())[:5]:  # Limit to 5 metadata items
                ctx = baggage.set_baggage(f"rf.suite.metadata.{key}", str(value), ctx)

        span = tracer.start_span(name, context=ctx, kind=trace.SpanKind.INTERNAL, attributes=attrs)
        return span

    @staticmethod
    def create_test_span(tracer, data, result, parent_context, prefix_style="none"):
        """Create child span for test case."""
        attrs = AttributeExtractor.from_test(data, result)
        name = SpanBuilder._add_prefix(data.name, "TEST", prefix_style)
        span = tracer.start_span(
            name, context=parent_context, kind=trace.SpanKind.INTERNAL, attributes=attrs
        )
        return span

    @staticmethod
    def create_keyword_span(
        tracer, data, result, parent_context, max_arg_length=200, prefix_style="none"
    ):
        """Create child span for keyword."""
        attrs = AttributeExtractor.from_keyword(data, result, max_arg_length)

        # Build keyword name with arguments (like RF test step line)
        kw_name = data.name
        if data.args:
            # Join arguments with comma-space
            args_str = ", ".join(str(arg) for arg in data.args)
            # Limit total length to avoid extremely long span names
            if len(args_str) > 100:
                args_str = args_str[:100] + "..."
            kw_name = f"{data.name} {args_str}"

        # Determine span type for prefix
        if data.type in ("SETUP", "TEARDOWN"):
            span_type = data.type
        else:
            span_type = "KEYWORD"

        # Add prefix based on style
        kw_name = SpanBuilder._add_prefix(kw_name, span_type, prefix_style)

        span = tracer.start_span(
            kw_name, context=parent_context, kind=trace.SpanKind.INTERNAL, attributes=attrs
        )
        return span

    @staticmethod
    def set_span_status(span, result):
        """Set span status based on RF result."""
        span.set_attribute(RFAttributes.STATUS, result.status)
        span.set_attribute(RFAttributes.ELAPSED_TIME, result.elapsedtime / 1000.0)

        if result.status == "FAIL":
            span.set_status(Status(StatusCode.ERROR, result.message))
        else:
            span.set_status(Status(StatusCode.OK))

    @staticmethod
    def add_error_event(span, result):
        """Add error event with exception details."""
        if result.status == "FAIL" and result.message:
            # Create detailed error event
            event_attrs = {
                "message": result.message,
                "rf.status": "FAIL",
            }

            # Try to extract exception type if available
            if hasattr(result, "error") and result.error:
                event_attrs["exception.type"] = type(result.error).__name__
                event_attrs["exception.message"] = str(result.error)

            # Add timestamp
            if hasattr(result, "endtime") and result.endtime:
                event_attrs["timestamp"] = result.endtime

            span.add_event("test.failed", event_attrs)
