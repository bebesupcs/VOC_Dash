with open('dashboard/engine.js', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'board' in line.lower():
            print(f"engine.js {i+1}: {line.strip()[:100]}")
