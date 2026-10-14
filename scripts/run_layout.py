import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image, ImageDraw
from analyzers.contrast import analyze_contrast
from analyzers.layout import analyze_layout

img = Image.open(sys.argv[1]).convert("RGB")
text_boxes = [it["bbox"] for it in analyze_contrast(img).measurements["items"]]
res = analyze_layout(img, text_boxes)
m = res.measurements
print("score:", res.score, "| whitespace:", m["whitespace_ratio"],
      "| balance x/y:", m["balance_x"], m["balance_y"])
for row in m["occupied_map"]:
    print("  " + "".join("#" if v else "." for v in row))
for i in res.issues:
    print(f"[{i.severity}] {i.what}")

out = img.copy()
d = ImageDraw.Draw(out)
for i in res.issues:
    x, y, w, h = i.bbox
    d.rectangle([x, y, x + w, y + h], outline=(0, 160, 255), width=3)
out.save(OUT / "layout_out.png")
print("saved outputs/layout_out.png")