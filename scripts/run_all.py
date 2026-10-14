import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image, ImageDraw, ImageFont
from core.pipeline import run_review

img = Image.open(sys.argv[1]).convert("RGB")
review = run_review(img)

print("OVERALL:", review.overall)
for name, r in review.categories.items():
    print(f"  {name:<14} {r.score}")
print("timings (s):", review.timings)
print()
for i in review.issues:
    print(f"#{i.priority} [{i.severity}] {i.category}: {i.what}")

W, H = img.size
out = img.copy()
d = ImageDraw.Draw(out)
font = ImageFont.load_default(size=max(14, W // 60))
colors = {"high": (255, 0, 60), "medium": (255, 140, 0), "low": (255, 215, 0)}
for i in review.issues:
    x, y, w, h = i.bbox
    if w * h > 0.9 * W * H:      # skip whole-page issues; they have no specific region
        continue
    c = colors[i.severity]
    d.rectangle([x - 3, y - 3, x + w + 3, y + h + 3], outline=c, width=3)
    d.text((x, max(0, y - W // 50)), str(i.priority), fill=c, font=font)
out.save(OUT / "review_out.png")
print("\nsaved outputs/review_out.png")