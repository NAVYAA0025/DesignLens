import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image, ImageDraw
from analyzers.contrast import analyze_contrast

img = Image.open(sys.argv[1]).convert("RGB")
res = analyze_contrast(img)
print("score:", res.score, "| text boxes:", res.measurements["text_boxes"],
      "| failing:", res.measurements["failing"])
for it in res.measurements["items"]:
    print(f'{it["status"].upper():<10} {it["ratio"]:>5}:1 (need {it["required"]})  {it["fg"]} on {it["bg"]}  "{it["text"]}"')

out = img.copy()
d = ImageDraw.Draw(out)
for i in res.issues:
    x, y, w, h = i.bbox
    d.rectangle([x - 3, y - 3, x + w + 3, y + h + 3],
                outline=(255, 200, 0) if i.severity == "low" else (255, 0, 60), width=3)
out.save(OUT / "contrast_out.png")
print("saved outputs/contrast_out.png")