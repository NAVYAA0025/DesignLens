import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image, ImageDraw
from analyzers.hierarchy import analyze_hierarchy


def run(name, img):
    res = analyze_hierarchy(img, [])
    print(name, "| score:", res.score)
    for f in res.measurements["focal_points"]:
        print("  focal", f["where"], f["share"])
    for i in res.issues:
        print("  [%s] %s" % (i.severity, i.what))


RED = (220, 30, 30)

a = Image.new("RGB", (800, 600), "white")      # two equal squares
d = ImageDraw.Draw(a)
d.rectangle([100, 200, 300, 400], fill=RED)
d.rectangle([500, 200, 700, 400], fill=RED)
run("two equal squares", a)

b = Image.new("RGB", (800, 600), "white")      # 12 small squares
d = ImageDraw.Draw(b)
for r in range(3):
    for c in range(4):
        x, y = 100 + c * 160, 100 + r * 160
        d.rectangle([x, y, x + 60, y + 60], fill=RED)
run("grid of small squares", b)

c = Image.new("RGB", (800, 600), "white")      # control
ImageDraw.Draw(c).rectangle([250, 150, 550, 450], fill=RED)
run("single square (control)", c)