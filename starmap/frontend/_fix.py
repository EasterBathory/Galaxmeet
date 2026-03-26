#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove remaining star map CSS and HTML remnants"""
import re

with open("index.html","r",encoding="utf-8") as f:
    html = f.read()

# Remove star map CSS lines
css_lines = [
    "#starMapWrap{position:relative;border-radius:var(--r);overflow:hidden;border:1px solid var(--border);background:#020408;cursor:grab;margin-bottom:8px}\n",
    "#starMapWrap:active{cursor:grabbing}\n",
    "#starCanvas{display:block;width:100%}\n",
    ".star-info-pop{position:absolute;background:rgba(28,28,30,.95);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);border:1px solid var(--border2);border-radius:var(--r-sm);padding:10px 12px;font-size:11px;z-index:10;pointer-events:none;max-width:180px;box-shadow:0 12px 32px rgba(0,0,0,.6);display:none}\n",
]
for line in css_lines:
    html = html.replace(line, "")

# Remove drawStarMap call in fetchPointData (if still present)
html = re.sub(
    r"\s*if\(document\.querySelector\('\.ptab\[data-tab=\"starmap\"\]'\)\?\.classList\.contains\(\"active\"\)\)drawStarMap\([^)]*\);",
    "",
    html
)

# Remove the starmap tab HTML block in the other renderCard version (lines with starMapWrap canvas)
html = re.sub(
    r"\s*<div style=\"padding:10px\">\s*<div[^>]*>拖拽旋转[^<]*</div>\s*<div id=\"starMapWrap\"><canvas id=\"starCanvas\"></canvas><div[^>]*></div></div>\s*</div>`;\s*\n\s*const lastPt=points\[points\.length-1\];\s*\n\s*drawStarMap\([^)]*\);",
    "",
    html
)

with open("index.html","w",encoding="utf-8") as f:
    f.write(html)
print("Done.")
