# -*- coding: utf-8 -*-
import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
url = 'https://docs.google.com/spreadsheets/d/1l-eDWHv_RJsE1Y36ggyrd3lurbbqaEUSDiEnbCSfV1o/edit'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
    matches = re.findall(r'(\d+),0,\["([^"]+)"', html)
    print('Matches:', len(matches))
    # Also search for sheet names
    sheet_meta = re.findall(r'\[(\d+),"([^"]+)",\d+,\d+\]', html)
    print('Sheet meta:', sheet_meta)
    for m in re.finditer(r'gid=(\d+)', html):
        print('gid:', m.group(1))
except Exception as e:
    print('Error:', e)
