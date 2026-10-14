import time
from PIL import Image
from analyzers.color import analyze_color
from analyzers.contrast import analyze_contrast
from analyzers.layout import analyze_layout
from analyzers.typography import analyze_typography
from analyzers.hierarchy import analyze_hierarchy
from core.models import Review
from core.strengths import find_strengths

WEIGHTS = {"accessibility": 0.25, "hierarchy": 0.20, "typography": 0.20,
           "layout": 0.20, "color": 0.15}
SEVERITY = {"high": 3, "medium": 2, "low": 1}
EFFORT = {"quick": 0, "moderate": 1, "major": 2}


def run_review(img: Image.Image) -> Review:
    img = img.convert("RGB")
    timings = {}

    def timed(name, fn, *args):
        start = time.time()
        result = fn(*args)
        timings[name] = round(time.time() - start, 2)
        return result

    contrast = timed("contrast+ocr", analyze_contrast, img)
    items = contrast.measurements["items"]
    boxes = [it["bbox"] for it in items]

    results = {
        "accessibility": contrast,
        "color": timed("color", analyze_color, img),
        "layout": timed("layout", analyze_layout, img, boxes),
        "typography": timed("typography", analyze_typography, img, items),
        "hierarchy": timed("hierarchy", analyze_hierarchy, img, boxes, items),
    }

    overall = sum(results[name].score * w for name, w in WEIGHTS.items())

    issues = [i for r in results.values() for i in r.issues]
    # most severe first; among equals, cheaper fixes first (quick wins), then category weight
    issues.sort(key=lambda i: (-SEVERITY[i.severity], EFFORT.get(i.effort, 1), -WEIGHTS.get(i.category, 0.15)))
    for rank, issue in enumerate(issues, 1):
        issue.priority = rank

    return Review(round(overall, 1), results, issues, timings, find_strengths(results))