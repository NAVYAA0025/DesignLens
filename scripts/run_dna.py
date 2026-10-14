import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

from PIL import Image
from core.pipeline import run_review
from core.dna import generate_dna

img = Image.open(sys.argv[1]).convert("RGB")
dna = generate_dna(img, run_review(img))
print("ARCHETYPE:", dna["archetype"])
print(dna["summary"])
for k, v in dna["traits"].items():
    print(f"  {k:<12} {v}")
print("raw:", dna["raw"])