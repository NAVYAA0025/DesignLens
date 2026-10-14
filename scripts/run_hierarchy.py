import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

import cv2
import numpy as np
from PIL import Image
from analyzers.contrast import analyze_contrast
from analyzers.hierarchy  import analyze_hierarchy

img = Image.open(sys.argv[1]).convert("RGB")
boxes = [it["bbox"] for it in analyze_contrast(img).measurements["items"]]
res = analyze_hierarchy(img, boxes)
m = res.measurements
print("score:", res.score, "| busy fraction:", m["busy_fraction"])
for n, f in enumerate(m["focal_points"], 1):
    print(f'focal {n}: {f["where"]:<13} share {f["share"]:<6} on text: {f["has_text"]}  box {f["bbox"]}')
print("density map (0-9):")
for row in m["density"]:
    print("  " + "".join(str(min(9, int(v * 30))) for v in row))
for i in res.issues:
    print(f"[{i.severity}] {i.category}: {i.what}")

W, H = img.size
base = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
heat = cv2.applyColorMap(cv2.resize((m["saliency"] * 255).astype(np.uint8), (W, H)), cv2.COLORMAP_JET)
out = cv2.addWeighted(base, 0.6, heat, 0.4, 0)
for n, f in enumerate(m["focal_points"], 1):
    x, y, w, h = f["bbox"]
    cv2.rectangle(out, (x, y), (x + w, y + h), (255, 255, 255), 3)
    cv2.putText(out, str(n), (x + 8, y + 40), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
cv2.imwrite(str(OUT / "hierarchy_out.png"), out)
print("saved outputs/hierarchy_out.png")