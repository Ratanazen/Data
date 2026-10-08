"""Kafka Log Producer for real-time log ingestion into LogShield streaming pipeline."""

from __future__ import annotations

import json
import time
from pathlib import Path

from src.logshield.config import get_settings
from src.logshield.utils.logging import get_logger

logger = get_logger("logshield.streaming.producer")


class LogProducer:
    """Publishes server log records to Apache Kafka topic."""

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
        simulate: bool = False,
    ):
        settings = get_settings()
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.kafka_topic
        self.simulate = simulate
        self.producer = None

        if not self.simulate:
            try:
                from kafka import KafkaProducer

                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers.split(","),
                    value_serializer=lambda v: (
                        v.encode("utf-8") if isinstance(v, str) else json.dumps(v).encode("utf-8")
                    ),
                    retries=3,
                    acks="all",
                )
                logger.info("Kafka producer connected to %s", self.bootstrap_servers)
            except Exception as exc:
                logger.warning(
                    "Kafka broker unavailable (%s). Falling back to simulated streaming mode.",
                    exc,
                )
                self.simulate = True

    def publish_line(self, line: str) -> bool:
        """Publish a single raw log string to the topic."""
        clean = line.strip()
        if not clean:
            return False

        if self.simulate or self.producer is None:
            logger.debug("[SIMULATED KAFKA -> %s] %s", self.topic, clean[:80])
            return True

        try:
            future = self.producer.send(self.topic, value=clean)
            future.get(timeout=5.0)
            return True
        except Exception as exc:
            logger.error("Failed to publish record to Kafka: %s", exc)
            return False

    def stream_file(
        self,
        file_path: Path | str,
        delay_seconds: float = 0.01,
        max_records: int | None = None,
    ) -> int:
        """Stream an existing log file line-by-line into the topic."""
        path = Path(file_path)
        if not path.is_file():
            logger.error("Log file not found: %s", path)
            return 0

        logger.info(
            "Streaming logs from %s into topic '%s' (delay=%.4fs, max=%s)",
            path,
            self.topic,
            delay_seconds,
            max_records,
        )

        sent_count = 0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if max_records and sent_count >= max_records:
                    break
                if self.publish_line(line):
                    sent_count += 1
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)
                if sent_count % 1000 == 0 and sent_count > 0:
                    logger.info("Streamed %d records to Kafka topic '%s'...", sent_count, self.topic)

        if self.producer:
            self.producer.flush()
        logger.info("Completed streaming %d records to topic '%s'.", sent_count, self.topic)
        return sent_count

    def close(self) -> None:
        """Close producer connection."""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LogShield Kafka Log Streamer")
    parser.add_argument("--file", type=str, default="server.log", help="Path to log file")
    parser.add_argument("--topic", type=str, default="server-logs", help="Kafka topic name")
    parser.add_argument("--bootstrap", type=str, default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--rate", type=float, default=100.0, help="Messages per second")
    parser.add_argument("--limit", type=int, default=1000, help="Max records to send")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode without Kafka")
    args = parser.parse_args()

    delay = 1.0 / args.rate if args.rate > 0 else 0.0
    prod = LogProducer(bootstrap_servers=args.bootstrap, topic=args.topic, simulate=args.simulate)
    try:
        prod.stream_file(args.file, delay_seconds=delay, max_records=args.limit)
    finally:
        prod.close()
