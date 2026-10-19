"""
Core Data Analytics & Dataset Profiler Engine

Provides statistical profiling, missing-value audits, duplicate detection,
schema validation, in-memory dataset inspection, and safe multi-format export.
"""

import io
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from .models import ColumnStats, DatasetProfile, DatasetSummaryItem


class DatasetAnalyzer:
    """Enterprise-grade dataset analysis and statistical profiling engine."""

    KNOWN_DATASETS = {
        "hourly_404_errors": {
            "name": "Hourly 404 Error Distribution",
            "rel_path": "hourly_404_errors.csv",
            "format": "csv",
            "description": "Hourly count of HTTP 404 errors across the 24-hour cycle"
        },
        "status_code_breakdown": {
            "name": "HTTP Status Code Breakdown",
            "rel_path": "status_code_breakdown.csv",
            "format": "csv",
            "description": "Frequency distribution across 200, 301, 403, 404, and 500 status codes"
        },
        "top_404_paths": {
            "name": "Top 404 Missing Endpoints",
            "rel_path": "top_404_paths.csv",
            "format": "csv",
            "description": "Most frequently probed non-existent URLs and attack vectors"
        },
        "daily_404_trend": {
            "name": "Daily 404 Failure Trend",
            "rel_path": "daily_404_trend.csv",
            "format": "csv",
            "description": "Day-over-day failure volumes and baseline anomaly patterns"
        },
        "heatmap_day_hour_404": {
            "name": "Day & Hour 404 Heatmap Matrix",
            "rel_path": "heatmap_day_hour_404.csv",
            "format": "csv",
            "description": "7-day by 24-hour failure density matrix for temporal scheduling"
        },
        "web_dashboard_data": {
            "name": "Web Dashboard Aggregated Data",
            "rel_path": "web_dashboard_data.json",
            "format": "json",
            "description": "Pre-computed telemetry, KPIs, and visualization series"
        },
        "gold_kpis": {
            "name": "Lakehouse Gold KPIs",
            "rel_path": "data/gold/gold_kpis.json",
            "format": "json",
            "description": "PySpark curated business metrics and telemetry aggregates"
        },
        "integrity_manifest": {
            "name": "Cryptographic Integrity Manifest",
            "rel_path": "integrity_manifest.json",
            "format": "json",
            "description": "SHA-256 and MD5 forensic checksums of system artifacts"
        }
    }

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = (base_dir or Path.cwd()).resolve()

    def discover_datasets(self) -> List[DatasetSummaryItem]:
        """Scans and lists all available project datasets with current row counts and sizes."""
        items: List[DatasetSummaryItem] = []

        for ds_id, meta in self.KNOWN_DATASETS.items():
            path = (self.base_dir / meta["rel_path"]).resolve()
            if not path.is_file():
                continue

            # Ensure path stays within base_dir
            if not str(path).startswith(str(self.base_dir)):
                continue

            try:
                stat = path.stat()
                size_bytes = stat.st_size
                mtime_iso = datetime.fromtimestamp(stat.st_mtime).isoformat()

                rows = 0
                cols = 0
                if meta["format"] == "csv":
                    df = pd.read_csv(path)
                    rows, cols = df.shape
                elif meta["format"] == "json":
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        rows = len(data)
                        cols = len(data[0].keys()) if rows > 0 and isinstance(data[0], dict) else 1
                    elif isinstance(data, dict):
                        rows = len(data)
                        cols = 2

                items.append(
                    DatasetSummaryItem(
                        id=ds_id,
                        name=meta["name"],
                        file_path=meta["rel_path"],
                        format=meta["format"],
                        rows=rows,
                        columns=cols,
                        size_bytes=size_bytes,
                        last_modified=mtime_iso
                    )
                )
            except Exception:
                continue

        return items

    def _resolve_safe_path(self, dataset_id: str) -> Path:
        """Resolves dataset ID or relative path safely against base directory."""
        if dataset_id in self.KNOWN_DATASETS:
            rel = self.KNOWN_DATASETS[dataset_id]["rel_path"]
            resolved = (self.base_dir / rel).resolve()
        else:
            # Prevent directory traversal attacks
            cleaned = dataset_id.lstrip("/\\")
            resolved = (self.base_dir / cleaned).resolve()

        if not str(resolved).startswith(str(self.base_dir)):
            raise ValueError("Access denied: Path traversal detected outside workspace.")

        if not resolved.is_file():
            raise FileNotFoundError(f"Dataset file not found: {resolved.name}")

        return resolved

    def load_dataframe(self, dataset_id: str) -> Tuple[pd.DataFrame, str, str]:
        """Loads a dataset into a pandas DataFrame, returning (df, dataset_name, format)."""
        path = self._resolve_safe_path(dataset_id)
        name = self.KNOWN_DATASETS.get(dataset_id, {}).get("name", path.stem)

        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
            fmt = "csv"
        elif path.suffix.lower() == ".json":
            fmt = "json"
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                df = pd.json_normalize(data)
            elif isinstance(data, dict):
                # Flatten or create key-value rows
                if all(isinstance(v, (int, float, str, bool)) or v is None for v in data.values()):
                    df = pd.DataFrame(list(data.items()), columns=["metric", "value"])
                else:
                    df = pd.json_normalize(data)
            else:
                df = pd.DataFrame([{"raw": str(data)}])
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        return df, name, fmt

    def profile_dataframe(
        self,
        df: pd.DataFrame,
        dataset_id: str,
        dataset_name: str,
        file_type: str,
        max_sample_rows: int = 50
    ) -> DatasetProfile:
        """Performs comprehensive statistical profiling and data hygiene audits."""
        total_rows, total_cols = df.shape
        duplicate_rows = int(df.duplicated().sum()) if total_rows > 0 else 0
        duplicate_pct = round((duplicate_rows / total_rows * 100), 2) if total_rows > 0 else 0.0

        try:
            mem_bytes = int(df.memory_usage(deep=True).sum())
        except Exception:
            mem_bytes = 0

        columns_stats: List[ColumnStats] = []
        total_null_pcts = []

        for col in df.columns:
            series = df[col]
            null_count = int(series.isna().sum())
            if series.dtype == object:
                # Also treat blank / whitespace-only strings as missing
                empty_str_count = int((series.astype(str).str.strip() == "").sum())
                null_count = max(null_count, empty_str_count)

            null_pct = round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0
            total_null_pcts.append(null_pct)
            unique_count = int(series.nunique(dropna=True))

            min_val = None
            max_val = None
            mean_val = None
            std_val = None
            p25_val = None
            median_val = None
            p75_val = None
            top_values = []

            if pd.api.types.is_bool_dtype(series):
                dtype_name = "boolean"
                clean = series.dropna()
                if not clean.empty:
                    min_val = str(bool(clean.min()))
                    max_val = str(bool(clean.max()))
            elif pd.api.types.is_numeric_dtype(series):
                dtype_name = "numeric"
                clean = series.dropna()
                if not clean.empty:
                    min_val = float(clean.min()) if not math.isnan(clean.min()) else None
                    max_val = float(clean.max()) if not math.isnan(clean.max()) else None
                    mean_val = round(float(clean.mean()), 4) if not math.isnan(clean.mean()) else None
                    try:
                        std_calc = clean.std()
                        std_val = round(float(std_calc), 4) if not math.isnan(std_calc) else 0.0
                    except Exception:
                        std_val = 0.0
                    try:
                        p25_val = round(float(clean.quantile(0.25)), 4)
                        median_val = round(float(clean.median()), 4)
                        p75_val = round(float(clean.quantile(0.75)), 4)
                    except Exception:
                        pass
            elif pd.api.types.is_datetime64_any_dtype(series):
                dtype_name = "datetime"
                clean = series.dropna()
                if not clean.empty:
                    min_val = str(clean.min())
                    max_val = str(clean.max())
            else:
                dtype_name = "string"


            # Top value frequency
            try:
                vc = series.value_counts(dropna=True).head(5)
                for val, cnt in vc.items():
                    top_values.append({"value": str(val), "count": int(cnt)})
            except Exception:
                pass

            columns_stats.append(
                ColumnStats(
                    name=str(col),
                    dtype=dtype_name,
                    total_count=total_rows,
                    null_count=null_count,
                    null_percentage=null_pct,
                    unique_count=unique_count,
                    min_val=min_val,
                    max_val=max_val,
                    mean=mean_val,
                    std=std_val,
                    p25=p25_val,
                    median=median_val,
                    p75=p75_val,
                    top_values=top_values
                )
            )

        # Calculate Data Quality Hygiene Score (0-100)
        avg_null_pct = sum(total_null_pcts) / len(total_null_pcts) if total_null_pcts else 0.0
        completeness = max(0.0, 100.0 - avg_null_pct)
        uniqueness = max(0.0, 100.0 - duplicate_pct)
        quality_score = round(completeness * 0.6 + uniqueness * 0.4, 1)

        # Sanitize sample rows for JSON serialization
        sample_df = df.head(max_sample_rows).copy()
        sample_df = sample_df.replace({float("nan"): None, float("inf"): None, float("-inf"): None})
        sample_rows = sample_df.to_dict(orient="records")

        return DatasetProfile(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            file_type=file_type,
            total_rows=total_rows,
            total_columns=total_cols,
            columns=columns_stats,
            duplicate_rows=duplicate_rows,
            duplicate_percentage=duplicate_pct,
            memory_size_bytes=mem_bytes,
            sample_rows=sample_rows,
            quality_score=quality_score
        )

    def profile_dataset(self, dataset_id: str, max_sample_rows: int = 50) -> DatasetProfile:
        """Profiles a saved dataset by its identifier or relative path."""
        df, name, fmt = self.load_dataframe(dataset_id)
        return self.profile_dataframe(df, dataset_id, name, fmt, max_sample_rows=max_sample_rows)

    def inspect_in_memory(
        self,
        content: str,
        format: str = "csv",
        name: str = "custom_dataset"
    ) -> DatasetProfile:
        """Parses and profiles raw user-supplied CSV or JSON content in-memory."""
        if not content or not content.strip():
            raise ValueError("Input dataset content cannot be empty.")

        fmt = format.lower().strip()
        if fmt == "csv":
            try:
                df = pd.read_csv(io.StringIO(content))
            except Exception as e:
                raise ValueError(f"CSV Parsing Error: {str(e)}")
        elif fmt == "json":
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    df = pd.json_normalize(parsed)
                elif isinstance(parsed, dict):
                    if all(isinstance(v, (int, float, str, bool)) or v is None for v in parsed.values()):
                        df = pd.DataFrame(list(parsed.items()), columns=["key", "value"])
                    else:
                        df = pd.json_normalize(parsed)
                else:
                    raise ValueError("JSON must be an array of objects or key-value dictionary.")
            except Exception as e:
                raise ValueError(f"JSON Parsing Error: {str(e)}")
        else:
            raise ValueError(f"Unsupported format '{format}'. Must be 'csv' or 'json'.")

        return self.profile_dataframe(df, "in_memory_dataset", name, fmt)

    def export_dataset(
        self,
        dataset_id: str,
        format: str = "csv",
        filter_column: Optional[str] = None,
        filter_value: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_descending: bool = False,
        limit: int = 1000
    ) -> str:
        """Filters, sorts, and exports dataset in CSV, JSON, or Markdown format."""
        df, _, _ = self.load_dataframe(dataset_id)

        # Apply filtering if requested
        if filter_column and filter_column in df.columns and filter_value:
            df = df[df[filter_column].astype(str).str.contains(filter_value, case=False, na=False)]

        # Apply sorting if requested
        if sort_column and sort_column in df.columns:
            df = df.sort_values(by=sort_column, ascending=not sort_descending)

        # Apply row limiting
        df = df.head(max(1, min(limit, 5000)))

        fmt = format.lower().strip()
        if fmt == "csv":
            return df.to_csv(index=False)
        elif fmt == "json":
            # Sanitize NaNs
            df_sanitized = df.replace({float("nan"): None, float("inf"): None, float("-inf"): None})
            return json.dumps(df_sanitized.to_dict(orient="records"), indent=2)
        elif fmt == "markdown":
            headers = [str(c) for c in df.columns]
            rows = []
            for _, r in df.iterrows():
                rows.append([str(val) if pd.notna(val) else "" for val in r])
            col_widths = [max(len(h), 3) for h in headers]
            for r in rows:
                for idx, v in enumerate(r):
                    if len(v) > col_widths[idx]:
                        col_widths[idx] = len(v)
            header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
            sep_line = "| " + " | ".join("-" * col_widths[i] for i in range(len(headers))) + " |"
            data_lines = [
                "| " + " | ".join(val.ljust(col_widths[i]) for i, val in enumerate(r)) + " |"
                for r in rows
            ]
            return "\n".join([header_line, sep_line] + data_lines)
        else:
            raise ValueError(f"Unsupported export format '{format}'. Use 'csv', 'json', or 'markdown'.")

