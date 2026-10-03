"""
Test Suite for Log File Analysis Pipeline
"""

import os
import re
import json
import csv
import unittest

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestLogFileAnalysis(unittest.TestCase):

    def test_01_server_log_exists(self):
        log_path = os.path.join(DIR, 'server.log')
        self.assertTrue(os.path.exists(log_path), "server.log must exist")
        self.assertGreater(os.path.getsize(log_path), 1_000_000, "server.log should be > 1MB")

    def test_02_regex_pattern(self):
        pattern = re.compile(
            r'^(\S+) \S+ \S+ \[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}) [^\]]+\] "(\S+) (\S+) [^"]*" (\d{3}) (\d+)'
        )
        sample_line = '10.0.12.45 - - [01/Sep/2026:03:14:22 +0000] "GET /admin/login HTTP/1.1" 404 342'
        m = pattern.match(sample_line)
        self.assertIsNotNone(m, "Regex must match Common Log Format sample line")
        self.assertEqual(m.group(1), '10.0.12.45')
        self.assertEqual(m.group(3), 'GET')
        self.assertEqual(m.group(4), '/admin/login')
        self.assertEqual(m.group(5), '404')
        self.assertEqual(m.group(6), '342')

    def test_03_summary_stats(self):
        stats_path = os.path.join(DIR, 'summary_stats.txt')
        self.assertTrue(os.path.exists(stats_path), "summary_stats.txt must exist")
        with open(stats_path) as f:
            content = f.read()
        self.assertIn('total_requests=200000', content)
        self.assertIn('total_404=43153', content)
        self.assertIn('error_rate=21.58', content)

    def test_04_hourly_errors_csv(self):
        csv_path = os.path.join(DIR, 'hourly_404_errors.csv')
        self.assertTrue(os.path.exists(csv_path), "hourly_404_errors.csv must exist")
        with open(csv_path) as f:
            reader = list(csv.DictReader(f))
        self.assertEqual(len(reader), 24, "Must have exactly 24 hourly rows")
        # Find peak hour
        peak_row = max(reader, key=lambda r: int(r['error_count']))
        self.assertEqual(int(peak_row['hour']), 3, "Peak failure hour must be 3 (03:00 AM)")
        self.assertGreater(int(peak_row['error_count']), 4000)

    def test_05_status_code_breakdown_csv(self):
        csv_path = os.path.join(DIR, 'status_code_breakdown.csv')
        self.assertTrue(os.path.exists(csv_path), "status_code_breakdown.csv must exist")
        with open(csv_path) as f:
            reader = list(csv.DictReader(f))
        statuses = {int(r['status']): int(r['count']) for r in reader}
        self.assertIn(200, statuses)
        self.assertIn(404, statuses)
        self.assertEqual(statuses[404], 43153)
        self.assertEqual(statuses[200], 136415)

    def test_06_top_endpoints_csv(self):
        csv_path = os.path.join(DIR, 'top_404_paths.csv')
        self.assertTrue(os.path.exists(csv_path), "top_404_paths.csv must exist")
        with open(csv_path) as f:
            reader = list(csv.DictReader(f))
        self.assertEqual(len(reader), 10, "Must have top 10 endpoints")
        self.assertEqual(reader[0]['path'], '/admin/login')

    def test_07_chart_images_generated(self):
        images = [
            '404_errors_by_hour.png',
            '404_heatmap_day_hour.png',
            'top_404_paths.png',
            '404_daily_trend.png'
        ]
        for img in images:
            img_path = os.path.join(DIR, img)
            self.assertTrue(os.path.exists(img_path), f"{img} must exist")
            self.assertGreater(os.path.getsize(img_path), 10_000, f"{img} should be > 10KB")

    def test_08_web_dashboard_data_json(self):
        json_path = os.path.join(DIR, 'web_dashboard_data.json')
        self.assertTrue(os.path.exists(json_path), "web_dashboard_data.json must exist")
        with open(json_path) as f:
            data = json.load(f)
        self.assertIn('metadata', data)
        self.assertIn('hourly_distribution', data)
        self.assertIn('status_breakdown', data)
        self.assertIn('top_endpoints', data)
        self.assertIn('heatmap_matrix', data)
        self.assertEqual(data['metadata']['peak_hour'], 3)

    def test_09_web_dashboard_html(self):
        html_path = os.path.join(DIR, 'index.html')
        self.assertTrue(os.path.exists(html_path), "index.html must exist")
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        self.assertIn('hourlyChart', html)
        self.assertIn('statusChart', html)
        self.assertIn('endpointsChart', html)
        self.assertIn('heatmap', html)

if __name__ == '__main__':
    unittest.main()
