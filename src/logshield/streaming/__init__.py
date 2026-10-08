"""LogShield Streaming module for Kafka and PySpark Structured Streaming."""

from src.logshield.streaming.producer import LogProducer
from src.logshield.streaming.streaming_job import run_streaming_job
from src.logshield.streaming.windowing import (
    apply_sliding_window,
    apply_tumbling_window,
)

__all__ = [
    "LogProducer",
    "apply_sliding_window",
    "apply_tumbling_window",
    "run_streaming_job",
]
