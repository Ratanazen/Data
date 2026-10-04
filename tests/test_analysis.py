"""
Test Suite for Log File Analysis Pipeline (Cross-Platform)
"""

import os
import re
import json
import csv
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent

class TestLogFileAnalysis(unittest.TestCase):

    def test_01_server_log_exists(self):
        log_path = DIR / 'server.log'
        self.assertTrue(log_path.exists(), "server.log must exist")
        self.assertGreater(log_path.stat().st_size, 1_000_000, "server.log should be > 1MB")

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
        stats_path = DIR / 'summary_stats.txt'
        self.assertTrue(stats_path.exists(), "summary_stats.txt must exist")
        with open(stats_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('total_requests=200000', content)
        self.assertIn('total_404=43153', content)
        self.assertIn('error_rate=21.58', content)

    def test_04_hourly_errors_csv(self):
        csv_path = DIR / 'hourly_404_errors.csv'
        self.assertTrue(csv_path.exists(), "hourly_404_errors.csv must exist")
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
        self.assertEqual(len(reader), 24, "Must have exactly 24 hourly rows")
        peak_row = max(reader, key=lambda r: int(r['error_count']))
        self.assertEqual(int(peak_row['hour']), 3, "Peak failure hour must be 3 (03:00 AM)")
        self.assertGreater(int(peak_row['error_count']), 4000)

    def test_05_status_code_breakdown_csv(self):
        csv_path = DIR / 'status_code_breakdown.csv'
        self.assertTrue(csv_path.exists(), "status_code_breakdown.csv must exist")
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = list(csv.DictReader(f))
        statuses = {int(r['status']): int(r['count']) for r in reader}
        self.assertIn(200, statuses)
        self.assertIn(404, statuses)
        self.assertEqual(statuses[404], 43153)
        self.assertEqual(statuses[200], 136415)

    def test_06_top_endpoints_csv(self):
        csv_path = DIR / 'top_404_paths.csv'
        self.assertTrue(csv_path.exists(), "top_404_paths.csv must exist")
        with open(csv_path, 'r', encoding='utf-8') as f:
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
            img_path = DIR / img
            self.assertTrue(img_path.exists(), f"{img} must exist")
            self.assertGreater(img_path.stat().st_size, 10_000, f"{img} should be > 10KB")

    def test_08_web_dashboard_data_json(self):
        json_path = DIR / 'web_dashboard_data.json'
        self.assertTrue(json_path.exists(), "web_dashboard_data.json must exist")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn('metadata', data)
        self.assertIn('hourly_distribution', data)
        self.assertIn('status_breakdown', data)
        self.assertIn('top_endpoints', data)
        self.assertIn('heatmap_matrix', data)
        self.assertEqual(data['metadata']['peak_hour'], 3)

    def test_09_web_dashboard_html(self):
        html_path = DIR / 'index.html'
        self.assertTrue(html_path.exists(), "index.html must exist")
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        self.assertIn('hourlyChart', html)
        self.assertIn('statusChart', html)
        self.assertIn('endpointsChart', html)
        self.assertIn('heatmap', html)
        self.assertIn('assets/favicon.svg', html)

    def test_10_serve_mime_types(self):
        import serve
        handler = serve.CrossPlatformHandler
        self.assertEqual(handler.extensions_map.get('.svg'), 'image/svg+xml')
        self.assertEqual(handler.extensions_map.get('.json'), 'application/json')
        self.assertEqual(handler.extensions_map.get('.js'), 'application/javascript')

    def test_11_cluster_sizing_computation(self):
        from run_analysis import compute_cluster_sizing
        sizing = compute_cluster_sizing(num_nodes=4, cores_per_node=8, ram_gb_per_node=32, storage_tb_per_node=2.0)
        self.assertEqual(sizing['num_nodes'], 4)
        self.assertEqual(sizing['usable_cores_per_node'], 7) # 8 - 1
        self.assertEqual(sizing['usable_ram_per_node_gb'], 30) # 32 - 2
        self.assertEqual(sizing['executor_cores'], 5) # min(5, 7)
        self.assertGreaterEqual(sizing['total_executors'], 1)
        self.assertGreaterEqual(sizing['overhead_memory_mb'], 384)
        self.assertGreater(sizing['shuffle_partitions'], 0)
        self.assertAlmostEqual(sizing['usable_hdfs_tb'], round(8.0 / 3.0, 2))

    def test_12_generate_cluster_configs(self):
        import tempfile
        from run_analysis import compute_cluster_sizing, generate_cluster_configs
        sizing = compute_cluster_sizing(num_nodes=4, cores_per_node=8, ram_gb_per_node=32)
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_cluster_configs(sizing, tmpdir)
            p = Path(tmpdir)
            for fname in ['spark-defaults.conf', 'core-site.xml', 'hdfs-site.xml', 'yarn-site.xml']:
                f = p / fname
                self.assertTrue(f.exists(), f"{fname} must be generated")
                self.assertGreater(f.stat().st_size, 50, f"{fname} must be non-empty")

    def test_13_docker_compose_cluster(self):
        compose_path = DIR / 'docker-compose.cluster.yml'
        self.assertTrue(compose_path.exists(), "docker-compose.cluster.yml must exist")
        with open(compose_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('namenode:', content)
        self.assertIn('datanode:', content)
        self.assertIn('spark-master:', content)
        self.assertIn('spark-worker:', content)
        self.assertIn('dashboard:', content)

    def test_14_web_dashboard_advanced_features(self):
        html_path = DIR / 'index.html'
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
        self.assertIn('id="log-inspector-modal"', html)
        self.assertIn('id="chart-zoom-modal"', html)
        self.assertIn('calc-nodes', html)
        self.assertIn('updateClusterCalculations', html)
        self.assertIn('openLogInspector', html)
        self.assertIn('exportFilteredLogsJSON', html)
        self.assertIn('exportFilteredLogsMarkdown', html)
        self.assertIn('yarn-site', html)

if __name__ == '__main__':
    unittest.main()
