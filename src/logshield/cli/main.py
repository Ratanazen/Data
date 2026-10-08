"""Unified CLI entrypoint for LogShield analytics platform."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from src.logshield import __version__
from src.logshield.utils.logging import get_logger

logger = get_logger("logshield.cli")


def cmd_ingest(args: argparse.Namespace) -> int:
    """Run Bronze ingestion from raw logs."""
    from src.logshield.spark.bronze import write_bronze_layer
    from src.logshield.spark.session import get_spark_session

    print("[+] Starting Bronze ingestion...")
    spark = get_spark_session(app_name="LogShield-CLI-Ingest")
    df = write_bronze_layer(spark, raw_file_path=args.input)
    count = df.count()
    print(f"[OK] Ingested {count:,} records into Bronze layer.")
    return 0


def cmd_process(args: argparse.Namespace) -> int:
    """Run Silver layer normalization and cleaning."""
    from src.logshield.spark.session import get_spark_session
    from src.logshield.spark.silver import write_silver_layer

    print("[+] Starting Silver layer processing...")
    spark = get_spark_session(app_name="LogShield-CLI-Silver")
    df = write_silver_layer(spark)
    count = df.count()
    print(f"[OK] Normalized {count:,} records into Silver layer.")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run Gold layer analytics and KPIs."""
    from src.logshield.spark.gold import write_gold_layer
    from src.logshield.spark.session import get_spark_session

    print("[+] Computing Gold analytics aggregations...")
    spark = get_spark_session(app_name="LogShield-CLI-Gold")
    tables = write_gold_layer(spark)
    print(f"[OK] Computed {len(tables)} Gold analytics tables.")
    return 0


def cmd_security(args: argparse.Namespace) -> int:
    """Run security incident detection and risk scoring engine."""
    from src.logshield.security.detectors import run_security_detection_pipeline
    from src.logshield.spark.session import get_spark_session

    print("[+] Running security threat detection pipeline...")
    spark = get_spark_session(app_name="LogShield-CLI-Security")
    results = run_security_detection_pipeline(spark)
    sec_count = results["security_events"].count()
    print(f"[OK] Detected {sec_count:,} security incidents.")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    """Run end-to-end lakehouse batch pipeline: Bronze -> Silver -> Gold -> Security."""
    from src.logshield.security.detectors import run_security_detection_pipeline
    from src.logshield.spark.etl import run_full_etl_pipeline
    from src.logshield.spark.session import get_spark_session

    print("==================================================")
    print(f"  LogShield v{__version__} — Full Lakehouse Batch Pipeline")
    print("==================================================")
    spark = get_spark_session(app_name="LogShield-Batch")
    etl_results = run_full_etl_pipeline(spark, raw_file_path=args.input)
    sec_results = run_security_detection_pipeline(spark)
    print(f"[OK] Complete batch pipeline finished in {etl_results['duration_seconds']:.2f}s.")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Run FastAPI REST API or Web Dashboard."""
    if args.target == "api":
        print(f"[+] Launching LogShield FastAPI REST API on http://{args.host}:{args.port}")
        import uvicorn

        uvicorn.run("src.logshield.api.main:app", host=args.host, port=args.port, reload=args.reload)
    elif args.target == "dashboard":
        print(f"[+] Launching LogShield Dashboard on http://{args.host}:{args.port}")
        import http.server
        import socketserver

        os.chdir(Path(__file__).resolve().parents[3])

        class Handler(http.server.SimpleHTTPRequestHandler):
            pass

        with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
            print(f"[OK] Serving HTTP on http://{args.host}:{args.port}/ (Press Ctrl+C to quit)")
            httpd.serve_forever()
    else:
        print("[!] Invalid target. Choose 'api' or 'dashboard'.")
        return 1
    return 0


def cmd_stream(args: argparse.Namespace) -> int:
    """Run streaming producer or PySpark Structured Streaming job."""
    if args.mode == "producer":
        from src.logshield.streaming.producer import LogProducer

        print(f"[+] Launching LogProducer for {args.file} -> topic '{args.topic}'...")
        prod = LogProducer(bootstrap_servers=args.bootstrap, topic=args.topic, simulate=args.simulate)
        try:
            prod.stream_file(args.file, delay_seconds=args.delay, max_records=args.limit)
        finally:
            prod.close()
    elif args.mode == "job":
        from src.logshield.streaming.streaming_job import run_streaming_job

        print("[+] Launching PySpark Structured Streaming job...")
        run_streaming_job(bootstrap_servers=args.bootstrap, topic=args.topic, duration_seconds=args.duration)
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Run automated pytest suite."""
    print("[+] Running test suite via pytest...")
    import pytest

    test_args = ["tests"]
    if args.fast:
        test_args.extend(["-m", "not slow"])
    if args.verbose:
        test_args.append("-v")
    exit_code = pytest.main(test_args)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint parser."""
    parser = argparse.ArgumentParser(
        prog="logshield",
        description="LogShield — Distributed Log Analytics & Security Platform",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"LogShield v{__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest raw logs into Bronze Parquet layer")
    p_ingest.add_argument("--input", "-i", type=str, default=None, help="Path to raw log file")
    p_ingest.set_defaults(func=cmd_ingest)

    # Process
    p_proc = subparsers.add_parser("process", help="Process Bronze logs into clean Silver layer")
    p_proc.set_defaults(func=cmd_process)

    # Analyze
    p_ana = subparsers.add_parser("analyze", help="Compute Gold analytics aggregations")
    p_ana.set_defaults(func=cmd_analyze)

    # Security
    p_sec = subparsers.add_parser("security", help="Run security detection & risk scoring")
    p_sec.set_defaults(func=cmd_security)

    # Batch (full)
    p_batch = subparsers.add_parser("batch", help="Run full batch pipeline (Bronze->Silver->Gold->Security)")
    p_batch.add_argument("--input", "-i", type=str, default=None, help="Path to raw log file")
    p_batch.set_defaults(func=cmd_batch)

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch web dashboard or FastAPI REST API")
    p_serve.add_argument("target", choices=["api", "dashboard"], default="api", nargs="?", help="Server target")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host binding")
    p_serve.add_argument("--port", "-p", type=int, default=8000, help="Port binding")
    p_serve.add_argument("--reload", action="store_true", help="Enable uvicorn hot reloading")
    p_serve.set_defaults(func=cmd_serve)

    # Stream
    p_stream = subparsers.add_parser("stream", help="Run Kafka streaming producer or PySpark stream job")
    p_stream.add_argument("--mode", choices=["producer", "job"], default="producer", help="Streaming mode")
    p_stream.add_argument("--bootstrap", default="localhost:9092", help="Kafka bootstrap servers")
    p_stream.add_argument("--topic", default="server-logs", help="Kafka topic name")
    p_stream.add_argument("--file", default="server.log", help="Log file to stream")
    p_stream.add_argument("--delay", type=float, default=0.01, help="Delay between messages (s)")
    p_stream.add_argument("--limit", type=int, default=1000, help="Max records to send")
    p_stream.add_argument("--duration", type=int, default=10, help="Streaming query duration (s)")
    p_stream.add_argument("--simulate", action="store_true", help="Simulate Kafka streaming offline")
    p_stream.set_defaults(func=cmd_stream)

    # Test
    p_test = subparsers.add_parser("test", help="Execute automated pytest test suite")
    p_test.add_argument("--fast", action="store_true", help="Skip slow integration tests")
    p_test.add_argument("-v", "--verbose", action="store_true", help="Verbose test reporting")
    p_test.set_defaults(func=cmd_test)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
