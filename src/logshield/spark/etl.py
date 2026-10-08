"""
Master PySpark / Lakehouse ETL Orchestrator
Coordinates Bronze -> Silver -> Gold pipeline execution.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import settings
from ..utils import logger
from .bronze import run_bronze_ingestion
from .gold import run_gold_aggregation
from .silver import run_silver_transformation


def run_pipeline(
    input_log: Optional[Path] = None,
    bronze_dir: Optional[Path] = None,
    silver_dir: Optional[Path] = None,
    gold_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Executes the complete Bronze -> Silver -> Gold Lakehouse ETL pipeline.
    """
    start_time = datetime.utcnow()
    logger.info("==================================================================")
    logger.info("🚀 LOGSHIELD — DISTRIBUTED LAKEHOUSE ETL PIPELINE")
    logger.info(f"   Mode: {settings.MODE.upper()} | App Env: {settings.APP_ENV}")
    logger.info("==================================================================")

    # 1. Bronze Layer
    bronze_res = run_bronze_ingestion(
        input_log=input_log or settings.get_effective_raw_log(),
        output_dir=bronze_dir or settings.BRONZE_PATH
    )

    # 2. Silver Layer
    silver_res = run_silver_transformation(
        raw_log_path=input_log or settings.get_effective_raw_log(),
        output_dir=silver_dir or settings.SILVER_PATH
    )

    # 3. Gold Layer
    gold_res = run_gold_aggregation(
        silver_dir=silver_dir or settings.SILVER_PATH,
        output_dir=gold_dir or settings.GOLD_PATH
    )

    elapsed_sec = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"✨ LogShield ETL Pipeline succeeded in {elapsed_sec:.2f} seconds.")

    return {
        "status": "success",
        "duration_seconds": round(elapsed_sec, 2),
        "bronze": bronze_res,
        "silver": silver_res,
        "gold": gold_res
    }
