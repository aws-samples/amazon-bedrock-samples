import json
import logging
import time
from contextlib import contextmanager
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, Optional
from threading import Lock
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActionGroupTiming:
    def __init__(self):
        self.start_time = None
        self.last_event_time = None
        self.timings = []

    def start(self):
        self.start_time = time.time()
        self.last_event_time = self.start_time

    def record_event(self):
        current_time = time.time()
        if self.last_event_time:
            latency = current_time - self.last_event_time
            self.timings.append({
                'timestamp': current_time,
                'latency': latency,
                'total_duration': current_time - self.start_time
            })
        self.last_event_time = current_time

    def get_total_duration(self):
        if self.start_time and self.last_event_time:
            return self.last_event_time - self.start_time
        return 0
    
class TimingMetrics:
    def __init__(self):
        self.component_timings = defaultdict(list)

    @contextmanager
    def measure(self, component_name: str):
        start_time = time.time_ns() // 1_000_000  # Convert to milliseconds
        try:
            yield
        finally:
            end_time = time.time_ns() // 1_000_000
            duration = end_time - start_time
            self.component_timings[component_name].append(duration)
            current_span = trace.get_current_span()
            if current_span:
                current_span.set_attribute("duration_ms", duration)

# Initialize timing metrics
timing_metrics = TimingMetrics()

# Thread-safe trace storage using context
class TraceContext:
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, Any] = {}
        self._session_data: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()  # Thread safety
        
    def get(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._storage.get(trace_id)
    
    def set(self, trace_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._storage[trace_id] = {
                **data,
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'trace_version': '1.0',
                    **self._metadata.get(trace_id, {})
                }
            }
    
    def delete(self, trace_id: str) -> None:
        with self._lock:
            self._storage.pop(trace_id, None)
            self._metadata.pop(trace_id, None)
            self._session_data.pop(trace_id, None)
    
    def add_metadata(self, trace_id: str, metadata: Dict[str, Any]) -> None:
        """Add metadata to a specific trace"""
        with self._lock:
            if trace_id not in self._metadata:
                self._metadata[trace_id] = {}
            self._metadata[trace_id].update(metadata)
    
    def set_session_data(self, trace_id: str, session_id: str, data: Dict[str, Any]) -> None:
        """Store session-specific data"""
        with self._lock:
            if trace_id not in self._session_data:
                self._session_data[trace_id] = {}
            self._session_data[trace_id][session_id] = {
                **data,
                'last_updated': datetime.now().isoformat()
            }
    
    def get_session_data(self, trace_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session-specific data"""
        with self._lock:
            return self._session_data.get(trace_id, {}).get(session_id)
    
    def get_trace_metadata(self, trace_id: str) -> Dict[str, Any]:
        """Get all metadata for a trace"""
        with self._lock:
            return self._metadata.get(trace_id, {})
    
    def clear_old_traces(self, max_age_seconds: int = 3600) -> None:
        """Clear traces older than max_age_seconds"""
        with self._lock:
            current_time = datetime.now()
            for trace_id in list(self._storage.keys()):
                trace_time = datetime.fromisoformat(
                    self._storage[trace_id]['metadata']['timestamp']
                )
                if (current_time - trace_time).total_seconds() > max_age_seconds:
                    self.delete(trace_id)

# Initialize trace context
trace_context = TraceContext()

@contextmanager
def safe_span_operation():
    """Context manager for safe span operations with error handling"""
    try:
        yield
    except Exception as e:
        logger.exception("Error in span operation")
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_status(Status(StatusCode.ERROR))
            current_span.record_exception(e)
            current_span.set_attribute("error.message", str(e))
        raise
    else:
        # If no exception occurred and status is UNSET, set to OK
        current_span = trace.get_current_span()
        if current_span and current_span.status.status_code == StatusCode.UNSET:
            current_span.set_status(Status(StatusCode.OK))

def set_common_attributes(span, attributes: Dict[str, Any]) -> None:
    for key, value in attributes.items():
        if value is not None and value != "":
            span.set_attribute(key, value)

def enhance_span_attributes(span, trace_data: dict):
    """Enhances span with comprehensive attributes"""
    common_attributes = {
        "trace.step_number": trace_data.get("step_number", 0),
        "trace.component_type": trace_data.get("type", "unknown"),
        "trace.timestamp": datetime.now().isoformat(),
    }

    if "metadata" in trace_data and "usage" in trace_data["metadata"]:
        usage = trace_data["metadata"]["usage"]
        common_attributes.update({
            "llm.token_count.input": usage.get("inputTokens", 0),
            "llm.token_count.output": usage.get("outputTokens", 0),
            "llm.token_count.total": usage.get("inputTokens", 0) + usage.get("outputTokens", 0)
        })

    if "duration" in trace_data:
        common_attributes["trace.duration"] = trace_data["duration"]

    if "metadata" in trace_data:
        common_attributes["trace.metadata"] = json.dumps(trace_data["metadata"])

    for key, value in common_attributes.items():
        if value is not None:
            span.set_attribute(key, value)