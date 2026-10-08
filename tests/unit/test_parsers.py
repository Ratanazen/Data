"""Unit tests for LogShield log parsers (Apache, Nginx, JSON)."""

from src.logshield.ingestion.apache_parser import parse_apache_line
from src.logshield.ingestion.json_parser import parse_json_line
from src.logshield.ingestion.nginx_parser import parse_nginx_line


class TestApacheParser:
    def test_parse_valid_clf_record(self):
        line = '10.0.12.45 - - [01/Sep/2026:03:14:22 +0000] "GET /admin/login HTTP/1.1" 404 342'
        record = parse_apache_line(line)
        assert record is not None
        assert record.ip == "10.0.12.45"
        assert record.method == "GET"
        assert record.path == "/admin/login"
        assert record.status == 404
        assert record.response_bytes == 342
        assert record.hour == 3
        assert record.date == "2026-09-01"

    def test_parse_dash_bytes(self):
        line = '192.168.1.1 - - [02/Sep/2026:12:00:00 +0000] "HEAD /health HTTP/1.1" 200 -'
        record = parse_apache_line(line)
        assert record is not None
        assert record.response_bytes == 0

    def test_parse_malformed_line(self):
        line = "Malformed log line without proper formatting"
        record = parse_apache_line(line)
        assert record is None


class TestNginxParser:
    def test_parse_valid_nginx_record(self):
        line = '172.16.0.5 - - [01/Sep/2026:15:30:00 +0000] "POST /api/orders HTTP/1.1" 201 128'
        record = parse_nginx_line(line)
        assert record is not None
        assert record.ip == "172.16.0.5"
        assert record.status == 201


class TestJsonLogParser:
    def test_parse_valid_json_log(self):
        line = '{"ip": "10.0.8.99", "timestamp": "2026-09-01T03:22:15Z", "method": "GET", "path": "/deprecated-api/v1", "status": 404, "bytes": 512}'
        record = parse_json_line(line)
        assert record is not None
        assert record.ip == "10.0.8.99"
        assert record.status == 404
        assert record.path == "/deprecated-api/v1"

    def test_parse_invalid_json(self):
        line = "not a json string"
        record = parse_json_line(line)
        assert record is None
