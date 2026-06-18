"""OpenTelemetry helpers shared by Python SDK examples."""
from __future__ import annotations

import os
from collections.abc import Callable

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def init_tracer(service_name: str) -> Callable[[], None]:
    """Initialize OTLP tracing for a short-lived example process."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")

    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
            }
        )
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    propagate.set_global_textmap(TraceContextTextMapPropagator())

    def shutdown() -> None:
        provider.force_flush()
        provider.shutdown()

    return shutdown
