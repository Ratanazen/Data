#!/usr/bin/env python3
"""
Convert Log_File_Analysis_Report.ipynb into an executive-grade HTML report
with upgraded Obsidian & Neon Cyberpunk palette, custom SVG icons, and print styling.
"""

import json
import re
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def markdown_to_html(md_text):
    lines = md_text.split('\n')
    in_table = False
    table_lines = []
    output_lines = []

    def flush_table(tbl):
        if not tbl:
            return ""
        html = '<div class="overflow-x-auto my-5"><table class="w-full text-xs text-left border-collapse border border-slate-800 rounded-2xl overflow-hidden shadow-lg">'
        header_done = False
        for line in tbl:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if all(set(c).issubset({'-', ':', ' '}) for c in cells):
                header_done = True
                continue
            if not header_done:
                html += '<tr class="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-slate-100 font-bold uppercase tracking-wider text-[11px] border-b border-slate-700">'
                for c in cells:
                    html += f'<th class="px-4 py-3 border-r border-slate-800/80">{c}</th>'
                html += '</tr>'
            else:
                html += '<tr class="hover:bg-slate-800/50 text-slate-300 border-b border-slate-850 transition">'
                for c in cells:
                    html += f'<td class="px-4 py-2.5 font-medium border-r border-slate-850/60">{c}</td>'
                html += '</tr>'
        html += '</table></div>'
        return html

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('|') and '|' in line.strip()[1:]:
            table_lines.append(line)
        else:
            if table_lines:
                output_lines.append(flush_table(table_lines))
                table_lines = []
            output_lines.append(line)
        i += 1
    if table_lines:
        output_lines.append(flush_table(table_lines))

    text = '\n'.join(output_lines)

    # Section Icons & Colors Map
    section_icons = {
        '1. Objective': ('assets/chart-bar.svg', 'text-sky-400'),
        '2. Methodology / Pipeline': ('assets/spark.svg', 'text-amber-400'),
        '3. Dataset Summary': ('assets/chart-bar.svg', 'text-indigo-400'),
        '4. HTTP Status Code Breakdown': ('assets/chart-bar.svg', 'text-emerald-400'),
        '5. 404 Errors by Hour of Day': ('assets/clock.svg', 'text-rose-400'),
        '6. Error Pattern by Day of Week and Hour': ('assets/heatmap.svg', 'text-amber-400'),
        '7. Top Endpoints Causing 404 Errors': ('assets/shield-check.svg', 'text-purple-400'),
        '8. Daily Trend': ('assets/chart-bar.svg', 'text-indigo-400'),
        '9. Key Findings': ('assets/shield-check.svg', 'text-rose-400'),
        '10. Recommendations': ('assets/shield-check.svg', 'text-emerald-400'),
        '11. Technology Stack': ('assets/hadoop.svg', 'text-amber-400'),
        '12. Deliverables & Interactive Web Dashboard': ('assets/favicon.svg', 'text-cyan-400')
    }

    def replace_h2(m):
        header_title = m.group(1).strip()
        icon_html = '<span class="w-2.5 h-2.5 rounded-full bg-rose-500 mr-2"></span>'
        for k, (icon_src, icon_color) in section_icons.items():
            if k in header_title:
                icon_html = f'<img src="{icon_src}" class="w-5 h-5 mr-2.5 inline-block" alt="icon">'
                break
        return f'<h2 class="text-xl font-extrabold text-white mt-10 mb-4 pb-2.5 border-b border-slate-800 flex items-center">{icon_html}{header_title}</h2>'

    text = re.sub(r'^## (.*?)$', replace_h2, text, flags=re.M)
    text = re.sub(r'^### (.*?)$', r'<h3 class="text-base font-bold text-slate-200 mt-6 mb-2 flex items-center gap-2"><span class="w-2 h-2 rounded bg-indigo-500"></span> \1</h3>', text, flags=re.M)
    text = re.sub(r'^# (.*?)$', r'<h1 class="text-3xl font-black text-white mb-2 bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">\1</h1>', text, flags=re.M)

    # Bold & italic formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-white font-bold">\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em class="text-slate-300">\1</em>', text)

    # Inline code
    text = re.sub(r'`(.*?)`', r'<code class="px-1.5 py-0.5 rounded-md bg-slate-800 text-rose-400 font-mono text-xs font-semibold">\1</code>', text)

    # Lists
    text = re.sub(r'^- (.*?)$', r'<li class="ml-4 list-disc text-slate-300 text-sm my-1.5">\1</li>', text, flags=re.M)
    text = re.sub(r'^\d+\. (.*?)$', r'<li class="ml-4 list-decimal text-slate-300 text-sm my-1.5">\1</li>', text, flags=re.M)

    return text

def generate_report():
    report_nb_path = BASE_DIR / 'Log_File_Analysis_Report.ipynb'
    with open(report_nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    body_html = ""
    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'markdown':
            source = ''.join(cell.get('source', []))
            body_html += f'<div class="my-4 leading-relaxed">{markdown_to_html(source)}</div>\n'

    html_content = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📄 Log File Analysis Executive Report — Hadoop & PySpark</title>
  <link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @media print {{
      body {{ background: white !important; color: black !important; }}
      .no-print {{ display: none !important; }}
      .shadow-2xl {{ box-shadow: none !important; }}
      .border {{ border-color: #cbd5e1 !important; }}
      .bg-slate-900, .bg-slate-950 {{ background: white !important; color: black !important; }}
      h1, h2, h3, strong {{ color: black !important; }}
      p, li, td {{ color: #334155 !important; }}
    }}
  </style>
</head>
<body class="bg-slate-950 text-slate-200 min-h-screen py-8 px-4 sm:px-6 lg:px-8 font-sans antialiased">
  
  <!-- Navigation Top Bar -->
  <header class="max-w-4xl mx-auto mb-6 flex items-center justify-between no-print">
    <div class="flex items-center gap-2.5">
      <img src="assets/favicon.svg" alt="Logo" class="w-6 h-6">
      <span class="text-xs font-bold text-slate-300">Assignment 2 • Hadoop & Apache PySpark</span>
    </div>
    <div class="flex items-center gap-3">
      <a href="index.html" class="px-3.5 py-1.5 text-xs font-bold rounded-xl bg-gradient-to-r from-rose-600 to-indigo-600 hover:from-rose-500 hover:to-indigo-500 text-white flex items-center gap-1.5 shadow-lg transition">
        <span>🌐</span> Open Web Dashboard
      </a>
      <button onclick="window.print()" class="px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition">
        <span>🖨️</span> Print / PDF
      </button>
    </div>
  </header>

  <!-- Document Card with Obsidian Backdrop -->
  <main class="max-w-4xl mx-auto bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-12 shadow-2xl space-y-6">
    {body_html}
  </main>

  <footer class="max-w-4xl mx-auto mt-8 text-center text-xs text-slate-500 py-4 no-print">
    Assignment 2 Log File Analysis • Apache PySpark & Hadoop Pipeline • Group IDK
  </footer>
</body>
</html>
"""

    out_file = BASE_DIR / 'Log_File_Analysis_Report.html'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[+] Generated: {out_file.name}")

if __name__ == '__main__':
    generate_report()
