import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image, ImageDraw
from analyzers.contrast import analyze_contrast
from analyzers.typography import analyze_typography

img = Image.open(sys.argv[1]).convert("RGB")
text_items = analyze_contrast(img).measurements["items"]
res = analyze_typography(img, text_items)
m = res.measurements
print("score:", res.score, "| size levels:", m["size_levels"], "| largest/smallest:", m["size_ratio"])
for it in sorted(m["items"], key=lambda it: -it["height"]):
    print(f'{it["height"]:>4}px  ink {it["ink"]:<6} "{it["text"]}"')
for i in res.issues:
    print(f"[{i.severity}] {i.what}")

out = img.copy()
d = ImageDraw.Draw(out)
for i in res.issues:
    x, y, w, h = i.bbox
    d.rectangle([x - 3, y - 3, x + w + 3, y + h + 3], outline=(200, 0, 255), width=3)
out.save(OUT / "typography_out.png")
print("saved outputs/typography_out.png")