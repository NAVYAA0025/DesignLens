import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image, ImageDraw
from analyzers.color import analyze_color


def run(name, img):
    res = analyze_color(img)
    m = res.measurements
    print(f"{name} | score: {res.score} | neon: {m['neon_share']} | vibrating: {m['vibrating_pairs']}")


def split(left, right):
    img = Image.new("RGB", (800, 600), left)
    ImageDraw.Draw(img).rectangle([400, 0, 800, 600], fill=right)
    return img


run("red + teal (similar brightness)", split((230, 30, 30), (0, 150, 120)))
run("yellow + blue (opposites, different brightness)", split((250, 230, 20), (30, 30, 200)))

neon = Image.new("RGB", (800, 600), "white")
ImageDraw.Draw(neon).rectangle([0, 0, 800, 480], fill=(57, 255, 20))
run("mostly neon green", neon)