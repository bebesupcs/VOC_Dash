# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard/render.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Find the claim module marker
marker = '// 클레임 처리 리드타임 & 세부 태그별 4사분면 리스크 분석 모듈 (고도화 도식화 완성)'
pos_m = text.find(marker)
if pos_m == -1:
    print("Claim module marker not found!")
    sys.exit()

# Extract the claim module text from marker to end of text (or wherever it ends)
pos_m_start = text.rfind('// ============================================================================', 0, pos_m)
claim_module_text = text[pos_m_start:].strip()

# Remove the claim module text from its current position
text = text[:pos_m_start].strip()

# Add window.toggleClaimRow = toggleClaimRow inside claim_module_text
claim_module_text += "\nwindow.toggleClaimRow = toggleClaimRow;\n"

# Now find `window.VOC_RENDER = {`
pos_render = text.find('window.VOC_RENDER = {')
if pos_render == -1:
    print("window.VOC_RENDER not found!")
    sys.exit()

# Insert claim module right before window.VOC_RENDER
text = text[:pos_render] + "\n\n" + claim_module_text + "\n\n" + text[pos_render:]

# Ensure render.js ends with })();
if not text.strip().endswith('})();'):
    # Check if there is an unclosed brace
    if text.strip().endswith('}'):
        text = text.strip() + '\n})();'

with open('dashboard/render.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully moved claim module inside IIFE in render.js!")
