"""Kafka Log Consumer for real-time ingestion monitoring and testing."""

from __future__ import annotations

from collections.abc import Iterator

from src.logshield.config import get_settings
from src.logshield.utils.logging import get_logger

logger = get_logger("logshield.streaming.consumer")


class LogConsumer:
    """Consumes server log events from an Apache Kafka topic."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
        group_id: str = "logshield-analytics-group",
        auto_offset_reset: str = "latest",
    ):
        settings = get_settings()
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.kafka_topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.consumer = None

        try:
            from kafka import KafkaConsumer

            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers.split(","),
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                value_deserializer=lambda v: v.decode("utf-8", errors="replace"),
                enable_auto_commit=True,
            )
            logger.info("Kafka consumer connected to %s (topic: %s)", self.bootstrap_servers, self.topic)
        except Exception as exc:
            logger.warning("Kafka broker unavailable for consumer (%s). Operating in offline mode.", exc)

    def consume(self, max_records: int | None = None) -> Iterator[str]:
        """Yield raw log string lines from Kafka topic."""
        if self.consumer is None:
            logger.warning("Consumer is offline. No records will be emitted.")
            return

        count = 0
        try:
            for message in self.consumer:
                yield message.value
                count += 1
                if max_records and count >= max_records:
                    break
        except KeyboardInterrupt:
            logger.info("Consumption interrupted by user.")
        finally:
            self.close()

    def close(self) -> None:
        """Close Kafka consumer session."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed.")
