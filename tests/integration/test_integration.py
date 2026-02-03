from pathlib import Path
from unittest.mock import patch

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from robot import run


def test_simple_suite_tracing():
    """Test tracing of simple Robot test suite."""
    # Set up in-memory span exporter
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Patch the tracer provider in listener
    with patch("robotframework_tracer.listener.TracerProvider", return_value=provider):
        with patch("robotframework_tracer.listener.trace.set_tracer_provider"):
            with patch("robotframework_tracer.listener.trace.get_tracer") as mock_get_tracer:
                mock_get_tracer.return_value = provider.get_tracer(__name__)

                # Run Robot tests with listener
                test_suite = Path(__file__).parent / "test_suites" / "simple.robot"
                run(
                    str(test_suite),
                    listener="robotframework_tracer.TracingListener",
                    outputdir="/tmp/robot_output",
                    stdout=None,
                    stderr=None,
                )

    # Verify spans were created
    spans = exporter.get_finished_spans()
    assert len(spans) > 0, "No spans were created"

    # Verify suite span exists
    suite_spans = [s for s in spans if "simple" in s.name.lower()]
    assert len(suite_spans) > 0, "No suite span found"

    # Verify test spans exist
    test_spans = [s for s in spans if any(t in s.name.lower() for t in ["passing", "failing"])]
    assert len(test_spans) > 0, "No test spans found"

    print(f"Created {len(spans)} spans")
    for span in spans:
        print(f"  - {span.name}: {span.attributes}")


def test_nested_suite_tracing():
    """Test tracing of nested Robot test suite."""
    # Set up in-memory span exporter
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    # Patch the tracer provider in listener
    with patch("robotframework_tracer.listener.TracerProvider", return_value=provider):
        with patch("robotframework_tracer.listener.trace.set_tracer_provider"):
            with patch("robotframework_tracer.listener.trace.get_tracer") as mock_get_tracer:
                mock_get_tracer.return_value = provider.get_tracer(__name__)

                # Run Robot tests with listener
                test_suite = Path(__file__).parent / "test_suites" / "nested.robot"
                run(
                    str(test_suite),
                    listener="robotframework_tracer.TracingListener",
                    outputdir="/tmp/robot_output",
                    stdout=None,
                    stderr=None,
                )

    # Verify spans were created
    spans = exporter.get_finished_spans()
    assert len(spans) > 0, "No spans were created"

    # Verify custom keyword spans exist
    keyword_spans = [s for s in spans if "keyword" in s.name.lower()]
    assert len(keyword_spans) > 0, "No keyword spans found"

    print(f"Created {len(spans)} spans for nested suite")
    for span in spans:
        print(f"  - {span.name}: {span.attributes}")


if __name__ == "__main__":
    test_simple_suite_tracing()
    test_nested_suite_tracing()
