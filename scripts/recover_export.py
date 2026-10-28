# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

log = r'C:\Users\hshwa\.gemini\antigravity\brain\c242c6aa-5cff-40f3-9191-3e1057b67357\.system_generated\logs\transcript_full.jsonl'
with open(log, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if 'async function exportReportExcel()' in line:
            idx = line.find('async function exportReportExcel()')
            # Look for function barChart after it
            end_idx = line.find('function barChart', idx)
            if end_idx != -1:
                chunk = line[idx:end_idx]
                chunk = chunk.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\"', '"')
                with open('recovered_export_excel.js', 'w', encoding='utf-8') as out:
                    out.write(chunk)
                print(f"Recovered {len(chunk)} characters to recovered_export_excel.js")
                break
