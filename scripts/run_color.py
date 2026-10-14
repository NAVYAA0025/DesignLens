import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image
from analyzers.color import analyze_color

res = analyze_color(Image.open(sys.argv[1]).convert("RGB"))
print("score:", res.score)
print("temperature:", res.measurements["temperature"], "| distinct hues:", res.measurements["distinct_hues"])
for p in res.measurements["palette"]:
    print(" ", p["hex"], p["share"])
print("accents:", [(a["hex"], a["share"]) for a in res.measurements["accents"]])
for i in res.issues:
    print(f"[{i.severity}] {i.what}")
print("neon share:", res.measurements["neon_share"], "| vibrating pairs:", res.measurements["vibrating_pairs"])
print("saturated coverage:", res.measurements["saturated_coverage"])