"""Generic configuration for OpenTelemetry with any OTLP-compatible backend."""

import os
from typing import Dict, Optional, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

def create_tracer_provider(
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    resource_attributes: Optional[Dict[str, Any]] = None,
    endpoint: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    use_batch_processor: bool = True,
) -> TracerProvider:
    """
    Create a generic OpenTelemetry TracerProvider configurable for any backend
    """
    service_name = service_name or os.environ.get("OTEL_SERVICE_NAME", 
                   os.environ.get("SERVICE_NAME", "opentelemetry-service"))
    environment = environment or os.environ.get("DEPLOYMENT_ENVIRONMENT", "production")
    
    # Create base resource attributes
    attributes = {
        "service.name": service_name,
        "deployment.environment": environment
    }
    if resource_attributes:
        attributes.update(resource_attributes)
    resource = Resource.create(attributes)
    
    # Create tracer provider with resource
    tracer_provider = TracerProvider(resource=resource)
    
    # Get endpoint from parameter or environment variable
    final_endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    # Parse headers from OTEL_EXPORTER_OTLP_HEADERS if not provided as parameter
    if not headers and "OTEL_EXPORTER_OTLP_HEADERS" in os.environ:
        headers_str = os.environ["OTEL_EXPORTER_OTLP_HEADERS"]
        headers = {}
        
        # Parse header string (format: key1=value1,key2=value2)
        for header_pair in headers_str.split(","):
            if "=" in header_pair:
                key, value = header_pair.split("=", 1)
                headers[key.strip()] = value.strip()
    
    # Configure OTLP exporter if endpoint is available
    if final_endpoint:
        try:
            # Create OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=final_endpoint,
                headers=headers,
                timeout=30
            )
            
            # Add appropriate span processor
            processor_cls = BatchSpanProcessor if use_batch_processor else SimpleSpanProcessor
            tracer_provider.add_span_processor(processor_cls(otlp_exporter))            
        except Exception as e:
            print(f"Failed to configure OTLP exporter: {str(e)}")
    else:
        print("No telemetry endpoint configured, spans will not be exported")
    
    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)
    return tracer_provider