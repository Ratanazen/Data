"""
Explicit PySpark Schemas for Bronze, Silver, and Gold Data Layers
"""

try:
    from pyspark.sql.types import (
        DateType,
        DoubleType,
        IntegerType,
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    BRONZE_SCHEMA = StructType([
        StructField("raw_line", StringType(), False),
        StructField("source_file", StringType(), False),
        StructField("line_number", LongType(), False),
        StructField("ingestion_time", TimestampType(), False),
        StructField("date", StringType(), False),
    ])

    SILVER_SCHEMA = StructType([
        StructField("timestamp", TimestampType(), False),
        StructField("ip", StringType(), False),
        StructField("method", StringType(), False),
        StructField("path", StringType(), False),
        StructField("protocol", StringType(), True),
        StructField("status", IntegerType(), False),
        StructField("response_bytes", LongType(), False),
        StructField("referer", StringType(), True),
        StructField("user_agent", StringType(), True),
        StructField("host", StringType(), True),
        StructField("source_file", StringType(), False),
        StructField("ingestion_time", TimestampType(), False),
        StructField("date", StringType(), False),
        StructField("hour", IntegerType(), False),
    ])

    GOLD_HOURLY_TRAFFIC_SCHEMA = StructType([
        StructField("hour", IntegerType(), False),
        StructField("total_requests", LongType(), False),
        StructField("errors_404", LongType(), False),
        StructField("errors_403", LongType(), False),
        StructField("errors_500", LongType(), False),
        StructField("successes_200", LongType(), False),
        StructField("redirects_301", LongType(), False),
        StructField("error_rate", DoubleType(), False),
    ])

    GOLD_TOP_URLS_SCHEMA = StructType([
        StructField("path", StringType(), False),
        StructField("hits", LongType(), False),
        StructField("errors_404", LongType(), False),
    ])

except ImportError:
    BRONZE_SCHEMA = None
    SILVER_SCHEMA = None
    GOLD_HOURLY_TRAFFIC_SCHEMA = None
    GOLD_TOP_URLS_SCHEMA = None
