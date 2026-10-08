"""Synthetic Log Generator for LogShield benchmarking and verification.

Generates Apache/Nginx Common Log Format records with configurable:
- Total records count
- Peak hours and error spikes
- 404/403/500 error distributions
- Security threat vectors (admin brute-force, directory traversal, bot scanning)
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

POPULAR_PATHS = [
    "/index.html",
    "/home",
    "/product/123",
    "/product/456",
    "/product/999",
    "/images/logo.png",
    "/css/style.css",
    "/js/app.js",
    "/checkout",
    "/api/orders",
    "/api/users",
    "/about",
    "/contact",
]

BROKEN_PATHS = [
    "/admin/login",
    "/old-promo-page",
    "/deprecated-api/v1",
    "/admin/config.php",
    "/wp-login.php",
    "/phpmyadmin",
    "/static/v1/bundle.js",
    "/assets/old-banner.png",
]

ATTACK_PATHS = [
    "/admin/login",
    "/admin/wp-login.php",
    "/etc/passwd",
    "/../../etc/shadow",
    "/.env",
    "/config/database.yml",
    "/api/v1/debug",
    "/server-status",
]

METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]
STATUSES = [200, 301, 403, 404, 500]


def generate_logs(
    output_path: str,
    total_records: int = 10000,
    error_rate: float = 0.21,
    peak_hour: int = 3,
    start_date: datetime | None = None,
    attack_ratio: float = 0.05,
) -> int:
    """Generate synthetic Apache access logs and save to output_path."""
    start_dt = start_date or datetime(2026, 9, 1, 0, 0, 0)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    attacker_ips = [f"192.168.100.{i}" for i in range(10, 25)]
    normal_ips = [f"10.0.{random.randint(1, 50)}.{random.randint(1, 254)}" for _ in range(200)]

    print(f"[+] Generating {total_records:,} synthetic log records to {out_file}...")

    with open(out_file, "w", encoding="utf-8") as f:
        for i in range(total_records):
            # Time distribution: boost probability during peak_hour
            day_offset = random.randint(0, 6)
            is_peak = random.random() < 0.35
            hour = peak_hour if is_peak else random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)

            rec_dt = start_dt + timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
            ts_str = rec_dt.strftime("%d/%b/%Y:%H:%M:%S +0000")

            # Determine if this record is a security attack
            is_attack = random.random() < attack_ratio
            if is_attack:
                ip = random.choice(attacker_ips)
                path = random.choice(ATTACK_PATHS)
                method = "POST" if "login" in path else "GET"
                status = random.choice([404, 403, 401])
                bytes_sent = random.randint(120, 450)
            else:
                ip = random.choice(normal_ips)
                method = random.choices(["GET", "POST", "HEAD"], weights=[0.85, 0.12, 0.03])[0]
                if random.random() < error_rate:
                    status = random.choices([404, 403, 500, 301], weights=[0.70, 0.10, 0.10, 0.10])[0]
                    path = random.choice(BROKEN_PATHS)
                    bytes_sent = random.randint(200, 600)
                else:
                    status = 200
                    path = random.choice(POPULAR_PATHS)
                    bytes_sent = random.randint(1000, 25000)

            log_line = f'{ip} - - [{ts_str}] "{method} {path} HTTP/1.1" {status} {bytes_sent}\n'
            f.write(log_line)

            if (i + 1) % 25000 == 0:
                print(f"  Processed {i + 1:,} records...")

    print(f"[OK] Finished generating {total_records:,} records in {out_file}.")
    return total_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LogShield Synthetic Log Generator")
    parser.add_argument("--output", "-o", default="data/raw/synthetic_access.log", help="Output log path")
    parser.add_argument("--records", "-n", type=int, default=10000, help="Number of records to generate")
    parser.add_argument("--error-rate", type=float, default=0.21, help="Error rate (0.0 to 1.0)")
    parser.add_argument("--peak-hour", type=int, default=3, help="Hour of peak failure (0-23)")
    parser.add_argument("--attacks", type=float, default=0.05, help="Ratio of security attack patterns")
    args = parser.parse_args()

    generate_logs(
        output_path=args.output,
        total_records=args.records,
        error_rate=args.error_rate,
        peak_hour=args.peak_hour,
        attack_ratio=args.attacks,
    )
