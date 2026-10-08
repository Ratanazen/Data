"""Streaming time-windowing and stateful aggregations for PySpark Structured Streaming."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


def apply_tumbling_window(
    df: DataFrame,
    time_col: str = "timestamp",
    window_duration: str = "5 minutes",
    watermark: str = "10 minutes",
) -> DataFrame:
    """Apply tumbling time windows with watermarking on a streaming DataFrame.

    Aggregates:
    - total_requests: Count of all requests in window
    - errors_404: Count of 404 errors
    - errors_403: Count of 403 errors
    - errors_500: Count of 500 errors
    """
    from pyspark.sql import functions as F

    windowed = (
        df.withWatermark(time_col, watermark)
        .groupBy(F.window(F.col(time_col), window_duration))
        .agg(
            F.count("*").alias("total_requests"),
            F.sum(F.when(F.col("status") == 404, 1).otherwise(0)).alias("errors_404"),
            F.sum(F.when(F.col("status") == 403, 1).otherwise(0)).alias("errors_403"),
            F.sum(F.when(F.col("status") >= 500, 1).otherwise(0)).alias("errors_500"),
        )
        .withColumn("window_start", F.col("window.start"))
        .withColumn("window_end", F.col("window.end"))
        .drop("window")
    )
    return windowed


def apply_sliding_window(
    df: DataFrame,
    time_col: str = "timestamp",
    window_duration: str = "10 minutes",
    slide_duration: str = "2 minutes",
    watermark: str = "15 minutes",
) -> DataFrame:
    """Apply sliding time windows to detect sudden error spikes and rate anomalies."""
    from pyspark.sql import functions as F

    sliding = (
        df.withWatermark(time_col, watermark)
        .groupBy(F.window(F.col(time_col), window_duration, slide_duration), F.col("ip"))
        .agg(
            F.count("*").alias("window_requests"),
            F.sum(F.when(F.col("status") == 404, 1).otherwise(0)).alias("window_404"),
            F.sum(F.when(F.col("status") == 403, 1).otherwise(0)).alias("window_403"),
            F.sum(F.when(F.col("status") >= 500, 1).otherwise(0)).alias("window_500"),
        )
        .withColumn("window_start", F.col("window.start"))
        .withColumn("window_end", F.col("window.end"))
        .drop("window")
    )
    return sliding
