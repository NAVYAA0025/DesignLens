import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]      # project root, so `core` / `analyzers` import
sys.path.insert(0, str(ROOT))
OUT = ROOT / "outputs"              # generated images go here
OUT.mkdir(exist_ok=True)

import time
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
import ollama

path = sys.argv[1]
img = Image.open(path).convert("RGB")
img.thumbnail((768, 768))
small = OUT / "_small.png"
img.save(small)

t = time.time()
ocr = RapidOCR()
result, _ = ocr(str(small))
print(f"OCR: {time.time() - t:.1f}s, {len(result or [])} text boxes")
for box, text, conf in (result or [])[:5]:
    print("  ", text, round(float(conf), 2))

t = time.time()
r = ollama.chat(
    model="qwen2.5vl:3b",
    messages=[{
        "role": "user",
        "content": "In two sentences, describe this website's visual design.",
        "images": [str(small)],
    }],
    keep_alive="10m",
)
print(f"VLM: {time.time() - t:.1f}s")
print(r["message"]["content"])