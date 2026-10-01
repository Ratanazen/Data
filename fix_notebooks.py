#!/usr/bin/env python3
"""
Clean up and validate both Jupyter Notebooks:
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
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)
    print(f"[+] Fixed {path}: cleaned empty cells (total cells: {len(nb['cells'])})")

def fix_report_notebook():
    path = 'Log_File_Analysis_Report.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Find cell with Key Findings & Recommendations
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
    print(f"[+] Fixed {path}: separated sections 9 & 10 (total cells: {len(nb['cells'])})")

if __name__ == '__main__':
    fix_pyspark_notebook()
    fix_report_notebook()
