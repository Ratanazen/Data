#!/usr/bin/env python3
"""
Clean up, validate, and ensure cross-platform UTF-8 encoding in both notebooks:
  1. Log_File_Analysis_PySpark.ipynb
  2. Log_File_Analysis_Report.ipynb
"""

import json

def fix_pyspark_notebook():
    path = 'Log_File_Analysis_PySpark.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Remove empty trailing cells
    nb['cells'] = [c for c in nb['cells'] if ''.join(c.get('source', [])).strip() != '']

    # Ensure open() uses encoding='utf-8' for cross-platform Windows compatibility
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            new_source = []
            for line in cell.get('source', []):
                if 'open("server.log", "w")' in line:
                    line = line.replace('open("server.log", "w")', 'open("server.log", "w", encoding="utf-8")')
                elif 'open("summary_stats.txt", "w")' in line:
                    line = line.replace('open("summary_stats.txt", "w")', 'open("summary_stats.txt", "w", encoding="utf-8")')
                new_source.append(line)
            cell['source'] = new_source

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print(f"[+] Fixed {path}: cross-platform UTF-8 encoding ensured (cells: {len(nb['cells'])})")

def fix_report_notebook():
    path = 'Log_File_Analysis_Report.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    new_cells = []
    for cell in nb['cells']:
        src = ''.join(cell.get('source', []))
        if '## 9. Key Findings' in src and '## 10. Recommendations' in src:
            parts = src.split('## 10. Recommendations')
            part1 = parts[0].strip() + '\n'
            part2 = '## 10. Recommendations\n\n' + parts[1].strip() + '\n'
            
            c1 = {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [line + '\n' for line in part1.split('\n') if line]
            }
            c2 = {
                'cell_type': 'markdown',
                'metadata': {},
                'source': [line + '\n' for line in part2.split('\n') if line]
            }
            new_cells.extend([c1, c2])
        else:
            new_cells.append(cell)

    nb['cells'] = new_cells
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print(f"[+] Fixed {path}: separated sections 9 & 10 (cells: {len(nb['cells'])})")

if __name__ == '__main__':
    fix_pyspark_notebook()
    fix_report_notebook()
