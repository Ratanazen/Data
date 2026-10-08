"""PySpark Structured Streaming job for real-time LogShield analytics."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.logshield.config import get_settings
from src.logshield.spark.session import get_spark_session
from src.logshield.streaming.windowing import apply_tumbling_window
from src.logshield.utils.logging import get_logger

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.streaming import StreamingQuery

logger = get_logger("logshield.streaming.job")


def build_kafka_stream_df(
    spark: SparkSession,
    bootstrap_servers: str,
    topic: str,
    starting_offsets: str = "latest",
) -> DataFrame:
    """Read streaming DataFrame from Kafka topic."""

    raw_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", topic)
        .option("startingOffsets", starting_offsets)
        .load()
    )

    # Decode value string
    return raw_df.selectExpr("CAST(value AS STRING) as raw_line")


def parse_streaming_log_lines(df: DataFrame) -> DataFrame:
    """Extract standard Apache log fields from streaming string column."""
    from pyspark.sql import functions as F

    log_pattern = (
        r'^(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"([A-Z]+)\s+([^"\s]+)(?:\s+HTTP/[\d\.]+)?\"\s+(\d{3})\s+(\d+|-)'
    )

    parsed = (
        df.select(
            F.regexp_extract("raw_line", log_pattern, 1).alias("ip"),
            F.regexp_extract("raw_line", log_pattern, 2).alias("timestamp_raw"),
            F.regexp_extract("raw_line", log_pattern, 3).alias("method"),
            F.regexp_extract("raw_line", log_pattern, 4).alias("url"),
            F.regexp_extract("raw_line", log_pattern, 5).cast("int").alias("status"),
            F.when(
                F.regexp_extract("raw_line", log_pattern, 6) == "-",
                F.lit(0),
            )
            .otherwise(F.regexp_extract("raw_line", log_pattern, 6).cast("long"))
            .alias("bytes"),
        )
        .filter(F.col("ip") != "")
        .withColumn(
            "timestamp",
            F.to_timestamp(F.col("timestamp_raw"), "dd/MMM/yyyy:HH:mm:ss"),
        )
    )
    return parsed


def run_streaming_job(
    bootstrap_servers: str | None = None,
    topic: str | None = None,
    output_mode: str = "complete",
    sink: str = "console",
    checkpoint_dir: str = "/tmp/logshield_checkpoint",
    duration_seconds: int | None = None,
) -> StreamingQuery | None:
    """Run the PySpark Structured Streaming pipeline.

    If Kafka is unavailable, performs a graceful standalone dry-run.
    """
    settings = get_settings()
    bootstrap = bootstrap_servers or settings.kafka_bootstrap_servers
    target_topic = topic or settings.kafka_topic

    logger.info("Initializing PySpark session for streaming...")
    spark = get_spark_session(app_name="LogShield-Streaming")

    try:
        logger.info(
            "Connecting Structured Streaming to Kafka: %s, topic: %s",
            bootstrap,
            target_topic,
        )
        raw_stream = build_kafka_stream_df(spark, bootstrap, target_topic)
        parsed_stream = parse_streaming_log_lines(raw_stream)
        windowed = apply_tumbling_window(parsed_stream)

        writer = (
            windowed.writeStream.outputMode(output_mode)
            .format(sink)
            .option("checkpointLocation", checkpoint_dir)
        )

        query = writer.start()
        logger.info("Streaming query started successfully (ID: %s)", query.id)

        if duration_seconds:
            query.awaitTermination(timeout=duration_seconds)
        return query

    except Exception as exc:
        logger.warning(
            "Streaming from Kafka broker '%s' encountered issue (%s). Running in standalone micro-batch simulation mode.",
            bootstrap,
            exc,
        )
        # Standalone local fallback: run micro-batch on sample log file
        log_file = Path(settings.raw_log_path)
        if log_file.is_file():
            logger.info("Executing static fallback verification on %s", log_file)
            static_raw = spark.read.text(str(log_file)).withColumnRenamed("value", "raw_line").limit(500)
            parsed_static = parse_streaming_log_lines(static_raw)
            parsed_static.groupBy("status").count().show(10)
        return None


if __name__ == "__main__":
    run_streaming_job(duration_seconds=5)
