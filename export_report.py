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
    in_code_block = False
    table_lines = []
    code_lines = []
    output_blocks = []

    def flush_table(tbl):
        if not tbl:
            return ""
        html = '<div class="overflow-x-auto my-5"><table class="w-full text-xs text-left border-collapse border border-slate-700 dark:border-slate-800 rounded-2xl overflow-hidden shadow-lg">'
        header_done = False
        for line in tbl:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if all(set(c).issubset({'-', ':', ' '}) for c in cells):
                header_done = True
                continue
            if not header_done:
                html += '<tr class="bg-slate-100 dark:bg-gradient-to-r dark:from-slate-900 dark:via-indigo-950 dark:to-slate-900 text-slate-800 dark:text-slate-100 font-bold uppercase tracking-wider text-[11px] border-b border-slate-300 dark:border-slate-700">'
                for c in cells:
                    html += f'<th class="px-4 py-3 border-r border-slate-200 dark:border-slate-800/80">{c}</th>'
                html += '</tr>'
            else:
                html += '<tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-850 transition">'
                for c in cells:
                    html += f'<td class="px-4 py-2.5 font-medium border-r border-slate-200 dark:border-slate-850/60">{c}</td>'
                html += '</tr>'
        html += '</table></div>'
        return html

    def flush_code(lines_list):
        if not lines_list:
            return ""
        code_str = "\n".join(lines_list)
        return f'<pre class="p-4 my-4 bg-slate-900 dark:bg-slate-950 text-cyan-300 dark:text-cyan-300 font-mono text-xs rounded-2xl border border-slate-700 dark:border-slate-800 overflow-x-auto shadow-inner"><code>{code_str}</code></pre>'

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith('```'):
            if in_code_block:
                output_blocks.append(flush_code(code_lines))
                code_lines = []
                in_code_block = False
            else:
                if table_lines:
                    output_blocks.append(flush_table(table_lines))
                    table_lines = []
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        if line.strip().startswith('|') and '|' in line.strip()[1:]:
            table_lines.append(line)
        else:
            if table_lines:
                output_blocks.append(flush_table(table_lines))
                table_lines = []
            output_blocks.append(line)
        i += 1

    if in_code_block:
        output_blocks.append(flush_code(code_lines))
    if table_lines:
        output_blocks.append(flush_table(table_lines))

    text = '\n'.join(output_blocks)

    # Section Icons & Colors Map
    section_icons = {
        '1. Objective': 'assets/chart-bar.svg',
        '2. Methodology / Pipeline': 'assets/spark.svg',
        '3. Dataset Summary': 'assets/chart-bar.svg',
        '4. HTTP Status Code Breakdown': 'assets/chart-bar.svg',
        '5. 404 Errors by Hour of Day': 'assets/clock.svg',
        '6. Error Pattern by Day of Week and Hour': 'assets/heatmap.svg',
        '7. Top Endpoints Causing 404 Errors': 'assets/shield-check.svg',
        '8. Daily Trend': 'assets/chart-bar.svg',
        '9. Key Findings': 'assets/shield-check.svg',
        '10. Recommendations': 'assets/shield-check.svg',
        '11. Technology Stack': 'assets/hadoop.svg',
        '12. Deliverables & Interactive Web Dashboard': 'assets/favicon.svg'
    }

    def replace_h2(m):
        header_title = m.group(1).strip()
        icon_html = '<span class="w-2.5 h-2.5 rounded-full bg-rose-500 mr-2"></span>'
        for k, icon_src in section_icons.items():
            if k in header_title:
                icon_html = f'<img src="{icon_src}" class="w-5 h-5 mr-2.5 inline-block" alt="icon">'
                break
        return f'<h2 class="text-xl font-extrabold text-slate-900 dark:text-white mt-10 mb-4 pb-2.5 border-b border-slate-200 dark:border-slate-800 flex items-center">{icon_html}{header_title}</h2>'

    text = re.sub(r'^## (.*?)$', replace_h2, text, flags=re.M)
    text = re.sub(r'^### (.*?)$', r'<h3 class="text-base font-bold text-slate-800 dark:text-slate-200 mt-6 mb-2 flex items-center gap-2"><span class="w-2 h-2 rounded bg-indigo-500"></span> \1</h3>', text, flags=re.M)
    text = re.sub(r'^# (.*?)$', r'<h1 class="text-3xl font-black text-slate-900 dark:text-white mb-2 bg-gradient-to-r from-slate-900 via-indigo-900 to-rose-600 dark:from-white dark:via-slate-100 dark:to-slate-400 bg-clip-text text-transparent">\1</h1>', text, flags=re.M)

    # Bold & italic formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-slate-900 dark:text-white font-bold">\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em class="text-slate-600 dark:text-slate-300">\1</em>', text)

    # Inline code (avoid pre/code tags)
    text = re.sub(r'(?<!<code>)`([^`\n]+)`(?!</code>)', r'<code class="px-1.5 py-0.5 rounded-md bg-slate-200 dark:bg-slate-800 text-rose-600 dark:text-rose-400 font-mono text-xs font-semibold">\1</code>', text)

    # Lists
    text = re.sub(r'^- (.*?)$', r'<li class="ml-4 list-disc text-slate-700 dark:text-slate-300 text-sm my-1.5">\1</li>', text, flags=re.M)
    text = re.sub(r'^\d+\. (.*?)$', r'<li class="ml-4 list-decimal text-slate-700 dark:text-slate-300 text-sm my-1.5">\1</li>', text, flags=re.M)

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
<html lang="en" class="dark scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📄 Log File Analysis Executive Report — Hadoop & PySpark</title>
  <link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <script>
    tailwind.config = {{
      darkMode: 'class',
      theme: {{
        extend: {{
          colors: {{
            obsidian: {{ 900: '#060a12', 950: '#030712' }},
            cyber: {{
              crimson: '#ff0055',
              amber: '#f59e0b',
              emerald: '#10b981',
              cyan: '#06b6d4',
              violet: '#8b5cf6'
            }}
          }}
        }}
      }}
    }}
  </script>
  <style>
    @media print {{
      body {{ background: white !important; color: black !important; }}
      .no-print {{ display: none !important; }}
      .shadow-2xl {{ box-shadow: none !important; }}
      .border {{ border-color: #cbd5e1 !important; }}
      .bg-slate-900, .bg-slate-950, .dark\\:bg-slate-900, .dark\\:bg-slate-950 {{ background: white !important; color: black !important; }}
      h1, h2, h3, strong {{ color: black !important; }}
      p, li, td {{ color: #334155 !important; }}
    }}
  </style>
</head>
<body class="bg-slate-100 text-slate-800 dark:bg-obsidian-950 dark:text-slate-200 min-h-screen py-8 px-4 sm:px-6 lg:px-8 font-sans antialiased transition-colors duration-300">
  
  <!-- Navigation Top Bar -->
  <header class="max-w-4xl mx-auto mb-6 flex items-center justify-between no-print">
    <div class="flex items-center gap-2.5">
      <a href="index.html" class="flex items-center gap-2.5 group">
        <img src="assets/favicon.svg" alt="Logo" class="w-6 h-6 group-hover:scale-110 transition">
        <span class="text-xs font-bold text-slate-700 dark:text-slate-300">Assignment 2 • Hadoop & Apache PySpark</span>
      </a>
    </div>
    <div class="flex items-center gap-2.5">
      <!-- Dark/Light Mode Switcher -->
      <button id="theme-toggle-btn" class="p-2 rounded-xl bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-800 hover:border-indigo-500 shadow-sm transition" title="Toggle Dark/Light Mode">
        <i data-lucide="sun" class="w-4 h-4 hidden dark:block text-amber-400"></i>
        <i data-lucide="moon" class="w-4 h-4 block dark:hidden text-indigo-600"></i>
      </button>

      <!-- GitHub Repo Link -->
      <a href="https://github.com/Ratanazen/Data" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 text-xs font-semibold rounded-xl bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700 flex items-center gap-1.5 shadow-sm transition">
        <i data-lucide="github" class="w-3.5 h-3.5"></i>
        <span class="hidden sm:inline">GitHub</span>
      </a>

      <!-- Web Dashboard Link -->
      <a href="index.html" class="px-3.5 py-1.5 text-xs font-bold rounded-xl bg-gradient-to-r from-cyber-crimson to-purple-600 hover:from-rose-500 hover:to-indigo-500 text-white flex items-center gap-1.5 shadow-lg shadow-rose-600/20 transition">
        <i data-lucide="layout-dashboard" class="w-3.5 h-3.5"></i>
        <span>Dashboard</span>
      </a>

      <!-- Print / PDF -->
      <button onclick="window.print()" class="px-3 py-1.5 text-xs font-semibold rounded-xl bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700 flex items-center gap-1.5 transition">
        <i data-lucide="printer" class="w-3.5 h-3.5"></i>
        <span class="hidden sm:inline">PDF</span>
      </button>
    </div>
  </header>

  <!-- Document Card with Obsidian Backdrop -->
  <main class="max-w-4xl mx-auto bg-white/95 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-12 shadow-2xl space-y-6">
    {body_html}
  </main>

  <footer class="max-w-4xl mx-auto mt-8 text-center text-xs text-slate-500 py-4 no-print flex flex-col sm:flex-row items-center justify-between gap-3">
    <span>Assignment 2 Log File Analysis • Apache PySpark & Hadoop Pipeline • Group IDK</span>
    <a href="https://github.com/Ratanazen/Data" target="_blank" rel="noopener noreferrer" class="hover:text-indigo-400 flex items-center gap-1">
      <i data-lucide="github" class="w-3 h-3"></i> Ratanazen/Data
    </a>
  </footer>

  <script>
    const themeBtn = document.getElementById('theme-toggle-btn');
    const isDark = () => document.documentElement.classList.contains('dark');
    
    if (localStorage.theme === 'light') {{
      document.documentElement.classList.remove('dark');
    }} else {{
      document.documentElement.classList.add('dark');
    }}

    themeBtn.addEventListener('click', () => {{
      if (isDark()) {{
        document.documentElement.classList.remove('dark');
        localStorage.theme = 'light';
      }} else {{
        document.documentElement.classList.add('dark');
        localStorage.theme = 'dark';
      }}
      lucide.createIcons();
    }});

    document.addEventListener('DOMContentLoaded', () => {{
      lucide.createIcons();
    }});
  </script>
</body>
</html>
"""

    out_file = BASE_DIR / 'Log_File_Analysis_Report.html'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[+] Generated: {out_file.name}")

if __name__ == '__main__':
    generate_report()

