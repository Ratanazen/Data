"""
Bronze Layer Pipeline: Raw log ingestion into partitioned Parquet
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import settings
from ..utils import logger


def run_bronze_ingestion(
    input_log: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    batch_size: int = 50000,
    clean_output: bool = True
) -> Dict[str, Any]:
    """
    Ingests raw log lines into the Bronze Parquet layer partitioned by date.
    """
    raw_path = Path(input_log or settings.get_effective_raw_log())
    out_path = Path(output_dir or settings.BRONZE_PATH)
    if clean_output and out_path.exists():
        import shutil
        shutil.rmtree(out_path, ignore_errors=True)
    out_path.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        raise FileNotFoundError(f"Input log file not found: {raw_path}")

    logger.info(f"[*] Bronze Ingestion starting: {raw_path} -> {out_path}")
    source_name = raw_path.name
    now_ts = datetime.utcnow()
    default_date = now_ts.strftime("%Y-%m-%d")

    records = []
    line_no = 0
    total_written = 0

    with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_no += 1
            line_clean = line.rstrip("\r\n")
            if not line_clean:
                continue

            # Attempt coarse extraction of date from bracketed timestamp (e.g. 04/Sep/2026)
            date_val = default_date
            try:
                start_b = line_clean.find("[")
                end_b = line_clean.find(":", start_b)
                if start_b != -1 and end_b != -1:
                    raw_d = line_clean[start_b + 1:end_b]
                    dt = datetime.strptime(raw_d, "%d/%b/%Y")
                    date_val = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

            records.append({
                "raw_line": line_clean,
                "source_file": source_name,
                "line_number": line_no,
                "ingestion_time": now_ts,
                "date": date_val
            })

            if len(records) >= batch_size:
                df = pd.DataFrame(records)
                table = pa.Table.from_pandas(df)
                pq.write_to_dataset(
                    table,
                    root_path=str(out_path),
                    partition_cols=["date"],
                    compression="snappy"
                )
                total_written += len(records)
                records = []

    if records:
        df = pd.DataFrame(records)
        table = pa.Table.from_pandas(df)
        pq.write_to_dataset(
            table,
            root_path=str(out_path),
            partition_cols=["date"],
            compression="snappy"
        )
        total_written += len(records)

    logger.info(f"[+] Bronze Layer complete: {total_written:,} records written to {out_path}")
    return {
        "status": "success",
        "layer": "bronze",
        "records_written": total_written,
        "output_directory": str(out_path)
    }
