"""Robot Framework Tracer - OpenTelemetry distributed tracing for Robot Framework."""

from .listener import TracingListener
from .version import __version__

__all__ = ["TracingListener", "__version__"]
