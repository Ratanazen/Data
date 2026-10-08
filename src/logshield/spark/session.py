"""
PySpark Session Management with local & cluster support
"""

from typing import Optional

from ..config import settings
from ..utils import logger

_SPARK_SESSION = None

def get_spark_session(app_name: Optional[str] = None) -> Optional["SparkSession"]:
    """
    Creates or retrieves the active PySpark SparkSession.
    Configures driver memory, Kryo serialization, and Snappy compression.
    Returns None if PySpark is unavailable or JVM initialization fails.
    """
    global _SPARK_SESSION
    if _SPARK_SESSION is not None:
        return _SPARK_SESSION

    try:
        from pyspark.sql import SparkSession
    except ImportError:
        logger.warning("PySpark package not installed; running in native Python lakehouse mode.")
        return None

    app = app_name or settings.SPARK_APP_NAME
    master = settings.SPARK_MASTER

    try:
        builder = (
            SparkSession.builder
            .appName(app)
            .master(master)
            .config("spark.driver.memory", settings.SPARK_DRIVER_MEMORY)
            .config("spark.sql.shuffle.partitions", str(settings.SPARK_SHUFFLE_PARTITIONS))
            .config("spark.sql.parquet.compression.codec", "snappy")
            .config("spark.ui.enabled", "false")
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        )

        # Configure HDFS defaultFS if running in hadoop mode
        if settings.MODE == "hadoop":
            builder = builder.config("spark.hadoop.fs.defaultFS", settings.HDFS_NAMENODE)

        _SPARK_SESSION = builder.getOrCreate()
        # Set log level to WARN to prevent noisy Spark logs
        _SPARK_SESSION.sparkContext.setLogLevel("WARN")
        logger.info(f"PySpark session active: {app} (master: {master})")
        return _SPARK_SESSION
    except Exception as e:
        logger.warning(f"Could not initialize PySpark session: {e}. Falling back to PyArrow engine.")
        return None

def stop_spark_session() -> None:
    """Stops the active PySpark session."""
    global _SPARK_SESSION
    if _SPARK_SESSION is not None:
        try:
            _SPARK_SESSION.stop()
        except Exception:
            pass
        _SPARK_SESSION = None
