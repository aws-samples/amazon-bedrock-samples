"""
Core module for Bedrock Agent OpenTelemetry integration.
"""

from .agent import instrument_agent_invocation
from .tracing import flush_telemetry