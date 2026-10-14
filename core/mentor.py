import io
import ollama
from PIL import Image

DEFAULT_MODEL = "qwen2.5vl:3b"

PROMPT = """You are a friendly senior UI/UX design mentor reviewing a website screenshot for a student.
Automated analyzers already measured the design. Their findings are below and are reliable;
do NOT invent new problems or numbers that are not in them.

Design DNA: {dna}
Overall score: {overall}/100

What already works:
{strengths}

Detected issues (ranked, most important first):
{issues}

Write the review in Markdown with exactly these three sections:
### First impression
Two sentences on the overall look and feel, in plain language.
### Fix these first
A numbered list of the 3 most valuable changes. Each item is one sentence, refers to a detected issue,
and says concretely what to change.
### Keep doing
One sentence about the strongest thing in the design.
Keep it under 150 words. Use simple, everyday words a beginner understands (no jargon).
Be encouraging but specific."""


def list_models():
    try:
        return [m.model for m in ollama.list().models]
    except Exception:
        return []


def mentor_review(img: Image.Image, review, dna, model: str = DEFAULT_MODEL) -> str:
    small = img.copy()
    small.thumbnail((768, 768))
    buf = io.BytesIO()
    small.save(buf, format="PNG")

    issues = "\n".join(f"{i.priority}. [{i.severity}] {i.title}: {i.what} Fix: {i.fix}"
                       for i in review.issues[:8]) or "None detected."
    strengths = "\n".join(f"- {t}" for _, t in review.strengths) or "- (none detected)"
    prompt = PROMPT.format(dna=f"{dna['archetype']}: {dna['summary']}", overall=review.overall,
                           strengths=strengths, issues=issues)

    msg = {"role": "user", "content": prompt}
    if any(tag in model for tag in ("vl", "llava", "vision", "gemma3", "moondream")):
        msg["images"] = [buf.getvalue()]      # text-only models get the findings without the screenshot
    r = ollama.chat(model=model, keep_alive="10m", options={"temperature": 0.3}, messages=[msg])
    return r["message"]["content"].strip()
