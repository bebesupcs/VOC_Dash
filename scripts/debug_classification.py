# -*- coding: utf-8 -*-
import glob
import pandas as pd

files = glob.glob(r'X:\11. VOC, CCM 자료 등\1. VOC 불만접수현황\26년\**\*2026-10-22*.xlsx', recursive=True)
df = pd.read_excel(files[0])

def get_tag_parts(t):
    if not isinstance(t, str):
        return ('(미분류)', '', '')
    parts = [p.strip() for p in t.split('/')]
    a = parts[0] if len(parts) > 0 else ''
    b = parts[1] if len(parts) > 1 else ''
    c = parts[2] if len(parts) > 2 else ''
    return (a, b, c)

tags_parsed = df['tags'].apply(get_tag_parts)
df['tag_a'] = [p[0] for p in tags_parsed]
df['tag_b'] = [p[1] for p in tags_parsed]
df['tag_c'] = [p[2] for p in tags_parsed]

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total rows: {len(df)}\n")
    f.write("\n=== tag_a breakdown ===\n")
    f.write(df['tag_a'].value_counts().to_string() + "\n")
    
    f.write("\n=== tag_a x tag_b breakdown ===\n")
    f.write(pd.crosstab(df['tag_a'], df['tag_b']).to_string() + "\n")
    
    f.write("\n=== tag_a by mediumName & direction ===\n")
    df['medium_clean'] = df['mediumName'].fillna('').astype(str).str.strip().replace({'': 'Chat', 'appNaverTalk': 'Chat', 'phoneNumber': 'Phone'})
    f.write(pd.crosstab(df['tag_a'], [df['medium_clean'], df['direction']]).to_string() + "\n")

    f.write("\n=== Detailed tag list ===\n")
    f.write(df['tags'].value_counts().to_string() + "\n")

print("Done! Written to debug_output.txt")
