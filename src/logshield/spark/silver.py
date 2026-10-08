"""
Silver Layer Pipeline: Cleans, parses, validates, and normalizes log records
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import settings
from ..ingestion.log_reader import LogReader
from ..utils import logger


def run_silver_transformation(
    raw_log_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    batch_size: int = 50000,
    clean_output: bool = True
) -> Dict[str, Any]:
    """
    Cleans, validates, and transforms records into the normalized Silver Parquet layer.
    Partitioned by date and hour.
    """
    input_file = Path(raw_log_path or settings.get_effective_raw_log())
    out_path = Path(output_dir or settings.SILVER_PATH)
    if clean_output and out_path.exists():
        import shutil
        shutil.rmtree(out_path, ignore_errors=True)
    out_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"[*] Silver Transformation starting: parsing {input_file} -> {out_path}")
    reader = LogReader(quarantine_dir=settings.QUARANTINE_PATH)

    batch: List[Dict[str, Any]] = []
    total_written = 0

    for parsed_record in reader.read_file(input_file):
        rec_dict = parsed_record.model_dump()
        batch.append(rec_dict)

        if len(batch) >= batch_size:
            df = pd.DataFrame(batch)
            table = pa.Table.from_pandas(df)
            pq.write_to_dataset(
                table,
                root_path=str(out_path),
                partition_cols=["date", "hour"],
                compression="snappy"
            )
            total_written += len(batch)
            batch = []

    if batch:
        df = pd.DataFrame(batch)
        table = pa.Table.from_pandas(df)
        pq.write_to_dataset(
            table,
            root_path=str(out_path),
            partition_cols=["date", "hour"],
            compression="snappy"
        )
        total_written += len(batch)

    quality = reader.get_quality_report()
    logger.info(f"[+] Silver Layer complete: {total_written:,} clean records partitioned to {out_path}")

    return {
        "status": "success",
        "layer": "silver",
        "records_written": total_written,
        "output_directory": str(out_path),
        "data_quality": quality
    }
