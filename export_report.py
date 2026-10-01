#!/usr/bin/env python3
"""
Convert Log_File_Analysis_Report.ipynb into a clean, standalone HTML report.
"""

import json
import re
import os

def markdown_to_html(md_text):
    # Convert markdown tables
    lines = md_text.split('\n')
    in_table = False
    table_lines = []
    output_lines = []

    def flush_table(tbl):
        if not tbl:
            return ""
        html = '<div class="overflow-x-auto my-4"><table class="min-w-full divide-y divide-slate-700 border border-slate-700 rounded-lg text-sm">'
        header_done = False
        for line in tbl:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if all(set(c).issubset({'-', ':'}) for c in cells):
                header_done = True
                continue
            if not header_done:
                html += '<tr class="bg-slate-800 text-white font-semibold">'
                for c in cells:
                    html += f'<th class="px-4 py-2 border-b border-slate-700 text-left">{c}</th>'
                html += '</tr>'
            else:
                html += '<tr class="hover:bg-slate-800/40 text-slate-300">'
                for c in cells:
                    html += f'<td class="px-4 py-2 border-b border-slate-800">{c}</td>'
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

    # Headers
    text = re.sub(r'^### (.*?)$', r'<h3 class="text-lg font-bold text-slate-200 mt-6 mb-2">\1</h3>', text, flags=re.M)
    text = re.sub(r'^## (.*?)$', r'<h2 class="text-xl font-bold text-white mt-8 mb-3 pb-2 border-b border-slate-800 flex items-center gap-2">\1</h2>', text, flags=re.M)
    text = re.sub(r'^# (.*?)$', r'<h1 class="text-3xl font-extrabold text-white mb-2">\1</h1>', text, flags=re.M)

    # Bold and italics
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong class="text-white font-semibold">\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em class="text-slate-300">\1</em>', text)

    # Inline code
    text = re.sub(r'`(.*?)`', r'<code class="px-1.5 py-0.5 rounded bg-slate-800 text-rose-400 font-mono text-xs">\1</code>', text)

    # Lists
    text = re.sub(r'^- (.*?)$', r'<li class="ml-4 list-disc text-slate-300 text-sm my-1">\1</li>', text, flags=re.M)
    text = re.sub(r'^\d+\. (.*?)$', r'<li class="ml-4 list-decimal text-slate-300 text-sm my-1">\1</li>', text, flags=re.M)

    return text

def generate_report():
    with open('Log_File_Analysis_Report.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)

    body_html = ""
    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'markdown':
            source = ''.join(cell.get('source', []))
            body_html += f'<div class="my-4 leading-relaxed">{markdown_to_html(source)}</div>\n'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Log File Analysis Report — PySpark & Hadoop</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-200 min-h-screen py-10 px-4 sm:px-8">
  <div class="max-w-4xl mx-auto bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 shadow-2xl space-y-6">
    <div class="flex items-center justify-between pb-4 border-b border-slate-800 text-xs text-slate-400">
      <span>Assignment 2 • Hadoop & PySpark</span>
      <div class="flex gap-3">
        <a href="index.html" class="text-indigo-400 hover:underline">← Open Web Dashboard</a>
        <button onclick="window.print()" class="text-slate-300 hover:underline">Print Report</button>
      </div>
    </div>
    {body_html}
  </div>
</body>
</html>
"""

    with open('Log_File_Analysis_Report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("[+] Generated: Log_File_Analysis_Report.html")

if __name__ == '__main__':
    generate_report()
