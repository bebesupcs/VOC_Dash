# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r'C:\Users\hshwa\.gemini\antigravity\brain\c242c6aa-5cff-40f3-9191-3e1057b67357\.system_generated\logs\transcript_full.jsonl'
with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if 'Showing lines 2595-2735' in line:
            pos = line.find('Showing lines 2595-2735')
            chunk = line[pos:pos+7000]
            chunk = chunk.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\"', '"')
            with open('recovered_export_full.txt', 'w', encoding='utf-8') as out:
                out.write(chunk)
            print("Extracted to recovered_export_full.txt successfully!")
            break
