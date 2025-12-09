"""
Minimal implementation skeleton for robotframework-tracer
This shows the core structure - copy to your new repository
"""

# ============================================================================
# src/robotframework_tracer/listener.py
# ============================================================================

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource


class TracingListener:
    """Robot Framework Listener v3 for distributed tracing."""
    
    ROBOT_LISTENER_API_VERSION = 3
    
    def __init__(self, endpoint="http://localhost:4318/v1/traces", 
                 service_name="robot-framework", **kwargs):
        # Initialize OpenTelemetry
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
        self.tracer = trace.get_tracer(__name__)
        self.span_stack = []  # Track span hierarchy
    
    def start_suite(self, data, result):
        """Create root span for suite."""
        span = self.tracer.start_span(
            data.name,
            kind=trace.SpanKind.INTERNAL,
            attributes={
                "rf.suite.name": data.name,
                "rf.suite.source": str(data.source) if data.source else "",
                "rf.suite.id": result.id,
            }
        )
        self.span_stack.append(span)
    
    def end_suite(self, data, result):
        """Close suite span."""
        if self.span_stack:
            span = self.span_stack.pop()
            span.set_attribute("rf.status", result.status)
            span.set_attribute("rf.elapsed_time", result.elapsedtime / 1000.0)
            span.end()
    
    def start_test(self, data, result):
        """Create child span for test case."""
        parent_context = trace.set_span_in_context(self.span_stack[-1]) if self.span_stack else None
        span = self.tracer.start_span(
            data.name,
            context=parent_context,
            kind=trace.SpanKind.INTERNAL,
            attributes={
                "rf.test.name": data.name,
                "rf.test.id": result.id,
                "rf.test.tags": list(data.tags),
            }
        )
        self.span_stack.append(span)
    
    def end_test(self, data, result):
        """Close test span with verdict."""
        if self.span_stack:
            span = self.span_stack.pop()
            span.set_attribute("rf.status", result.status)
            span.set_attribute("rf.elapsed_time", result.elapsedtime / 1000.0)
            
            if result.status == "FAIL":
                span.set_status(trace.Status(trace.StatusCode.ERROR, result.message))
                span.add_event("test.failed", {"message": result.message})
            
            span.end()
    
    def start_keyword(self, data, result):
        """Create child span for keyword/step."""
        parent_context = trace.set_span_in_context(self.span_stack[-1]) if self.span_stack else None
        
        # Build keyword name with library prefix
        kw_name = f"{data.libname}.{data.kwname}" if data.libname else data.kwname
        
        span = self.tracer.start_span(
            kw_name,
            context=parent_context,
            kind=trace.SpanKind.INTERNAL,
            attributes={
                "rf.keyword.name": data.kwname,
                "rf.keyword.type": data.type,
                "rf.keyword.library": data.libname or "",
            }
        )
        
        # Add arguments (with size limit)
        if data.args:
            args_str = ", ".join(str(arg)[:100] for arg in data.args[:5])
            span.set_attribute("rf.keyword.args", args_str)
        
        self.span_stack.append(span)
    
    def end_keyword(self, data, result):
        """Close keyword span."""
        if self.span_stack:
            span = self.span_stack.pop()
            span.set_attribute("rf.status", result.status)
            
            if result.status == "FAIL":
                span.set_status(trace.Status(trace.StatusCode.ERROR, result.message))
            
            span.end()
    
    def close(self):
        """Cleanup on listener close."""
        # Ensure all spans are closed
        while self.span_stack:
            span = self.span_stack.pop()
            span.end()
        
        # Flush remaining spans
        trace.get_tracer_provider().force_flush()


# ============================================================================
# setup.py
# ============================================================================

SETUP_PY = """
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="robotframework-tracer",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="OpenTelemetry distributed tracing for Robot Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/robotframework-tracer",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/robotframework-tracer/issues",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Robot Framework",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "robotframework>=6.0",
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-exporter-otlp-proto-http>=1.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov",
            "black",
            "ruff",
        ],
        "grpc": [
            "opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
        ],
    },
)
"""

# ============================================================================
# examples/simple_test.robot
# ============================================================================

EXAMPLE_ROBOT = """
*** Settings ***
Documentation     Simple test to demonstrate tracing

*** Test Cases ***
Simple Test
    [Tags]    smoke
    Log    Starting test
    Should Be Equal    1    1
    Log    Test completed

Failing Test
    [Tags]    negative
    Log    This test will fail
    Should Be Equal    1    2    This should fail

Test With Keywords
    [Tags]    keywords
    My Custom Keyword
    Another Keyword    arg1    arg2

*** Keywords ***
My Custom Keyword
    Log    Inside custom keyword
    Sleep    0.1s

Another Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log    Arguments: ${arg1}, ${arg2}
"""

# ============================================================================
# examples/docker-compose.yml
# ============================================================================

DOCKER_COMPOSE = """
version: '3.8'

services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4318:4318"    # OTLP HTTP receiver
      - "4317:4317"    # OTLP gRPC receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true
"""

# ============================================================================
# README.md
# ============================================================================

README = """
# Robot Framework Tracer

OpenTelemetry distributed tracing integration for Robot Framework.

## Installation

```bash
pip install robotframework-tracer
```

## Quick Start

1. Start Jaeger (or your preferred tracing backend):

```bash
docker-compose up -d
```

2. Run your tests with the listener:

```bash
robot --listener robotframework_tracer.TracingListener tests/
```

3. View traces at http://localhost:16686

## Configuration

### Basic Usage

```bash
robot --listener robotframework_tracer.TracingListener tests/
```

### Custom Endpoint

```bash
robot --listener robotframework_tracer.TracingListener:endpoint=http://jaeger:4318/v1/traces tests/
```

### Custom Service Name

```bash
robot --listener "robotframework_tracer.TracingListener:endpoint=http://jaeger:4318/v1/traces,service_name=my-tests" tests/
```

## Span Hierarchy

- **Suite Span**: Root span for each test suite
- **Test Span**: Child span for each test case
- **Keyword Span**: Child span for each keyword/step

## Attributes

Each span includes relevant Robot Framework metadata:

- Suite: name, source, id, metadata
- Test: name, id, tags, status
- Keyword: name, type, library, arguments

## Requirements

- Python 3.8+
- Robot Framework 6.0+
- OpenTelemetry SDK

## License

Apache License 2.0
"""

if __name__ == "__main__":
    print("This is a skeleton file. Copy components to your new repository.")
    print("\nFiles to create:")
    print("  src/robotframework_tracer/listener.py")
    print("  setup.py")
    print("  examples/simple_test.robot")
    print("  examples/docker-compose.yml")
    print("  README.md")
