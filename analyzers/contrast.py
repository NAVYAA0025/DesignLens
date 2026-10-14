import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
from core.models import Issue, AnalysisResult

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:          # load the OCR model once, reuse afterwards
        _ocr = RapidOCR()
    return _ocr


def _lin(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _luminance(rgb):
    r, g, b = _lin(rgb)
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def contrast_ratio(c1, c2):
    l1, l2 = _luminance(c1), _luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _estimate_colors(arr, x, y, w, h):
    """bg = median of a ring around the text box; fg = the pixels in the box
    that differ most from bg."""
    H, W = arr.shape[:2]
    pad = max(2, h // 3)
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
    outer = arr[y0:y1, x0:x1]
    mask = np.ones(outer.shape[:2], bool)
    mask[y - y0:y - y0 + h, x - x0:x - x0 + w] = False
    ring = outer[mask]
    inner = arr[y:y + h, x:x + w].reshape(-1, 3)
    bg = np.median(ring if len(ring) else inner, axis=0)

    dist = np.linalg.norm(inner.astype(np.float64) - bg, axis=1)
    k = max(5, len(inner) // 20)                  # top 5% most different pixels
    fg = np.median(inner[np.argsort(-dist)[:k]], axis=0)
    return fg, bg


def _hex(c):
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def suggest_color(fg, bg, required):
    """Smallest change to the text colour that reaches `required`: blend it towards
    white or black (whichever direction can get there) and keep its hue."""
    fg, bg = np.asarray(fg, dtype=np.float64), np.asarray(bg, dtype=np.float64)
    target_ratio = required + 0.1                  # small margin for estimation error
    options = []
    for end in (np.array([255.0, 255, 255]), np.array([0.0, 0, 0])):
        for t in np.linspace(0, 1, 101):
            c = fg + (end - fg) * t
            if contrast_ratio(c, bg) >= target_ratio:
                options.append((t, c))
                break
    if not options:
        return None, None
    t, c = min(options, key=lambda o: o[0])
    return _hex(c), round(contrast_ratio(c, bg), 1)


def _similar(a, b, tol=40):
    return np.linalg.norm(np.asarray(a, float) - np.asarray(b, float)) < tol


def _rgb(hexstr):
    return tuple(int(hexstr[i:i + 2], 16) for i in (1, 3, 5))


def _quote(texts, n=3):
    shown = [t if len(t) <= 24 else t[:21] + "..." for t in texts[:n]]
    more = f" and {len(texts) - n} more" if len(texts) > n else ""
    return ", ".join(f'"{t}"' for t in shown) + more


def analyze_contrast(img: Image.Image) -> AnalysisResult:
    arr = np.asarray(img.convert("RGB"))
    H, W = arr.shape[:2]
    result, _ = _get_ocr()(arr[:, :, ::-1])       # RapidOCR expects BGR

    items = []
    for box, text, conf in (result or []):
        if float(conf) < 0.5 or not text.strip():
            continue
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        x, y = max(0, int(min(xs))), max(0, int(min(ys)))
        w, h = min(W, int(max(xs))) - x, min(H, int(max(ys))) - y
        if w < 4 or h < 4:
            continue

        fg, bg = _estimate_colors(arr, x, y, w, h)
        ratio = contrast_ratio(fg, bg)
        required = 3.0 if h >= 30 else 4.5        # box height as a rough "large text" proxy
        if ratio >= required:
            status = "pass"
        elif ratio >= required * 0.8:
            status = "borderline"      # within 20%: estimation error could flip the verdict
        else:
            status = "fail"
        item = {"text": text, "bbox": (x, y, w, h), "ratio": round(ratio, 2),
                "required": required, "fg": _hex(fg), "bg": _hex(bg), "status": status,
                "suggested": None, "suggested_ratio": None}
        if status != "pass":
            item["suggested"], item["suggested_ratio"] = suggest_color(fg, bg, required)
        items.append(item)

    # one issue per "family" of problem text: same colours, same requirement, same verdict
    # (e.g. five grey nav links are one design decision, not five separate problems)
    groups = []
    for it in sorted((i for i in items if i["status"] != "pass"), key=lambda i: i["ratio"]):
        for g in groups:
            ref = g[0]
            if (ref["status"] == it["status"] and ref["required"] == it["required"]
                    and _similar(_rgb(ref["fg"]), _rgb(it["fg"])) and _similar(_rgb(ref["bg"]), _rgb(it["bg"]))):
                g.append(it)
                break
        else:
            groups.append([it])

    issues = []
    for g in groups:
        worst = g[0]
        ratio, required = worst["ratio"], worst["required"]
        texts = [i["text"] for i in g]
        many = len(g) > 1
        if worst["status"] == "fail":
            severity = "high" if ratio < 3.0 else "medium"
            title = "Text is hard to read"
            what = (f"{len(g)} bits of text ({_quote(texts)}) blend into their background." if many else
                    f"The text {_quote(texts)} blends into its background.")
        else:
            severity = "low"
            title = "Text is a little faint"
            what = (f"{len(g)} bits of text ({_quote(texts)}) are almost clear enough, but not quite." if many else
                    f"The text {_quote(texts)} is almost clear enough, but not quite.")
        why = (f"People with weaker eyesight, or anyone reading on a phone in sunlight, will struggle. "
               f"Readability: {ratio:.1f} out of the {required:g} needed.")
        if worst["suggested"]:
            way = "lighter" if _luminance(_rgb(worst["suggested"])) > _luminance(_rgb(worst["fg"])) else "darker"
            fix = (f"Change the text colour from {worst['fg']} to {worst['suggested']}. "
                   f"Same colour, just {way}, and easy to read.")
        else:
            fix = "Make the text much lighter or darker so it stands out from the background."
        if many:
            fix += " They share one style, so one change fixes them all."
        issues.append(Issue(
            "accessibility", severity, worst["bbox"], what, why, fix, effort="quick", title=title,
            regions=[i["bbox"] for i in g[1:]]))

    failing = sum(1 for it in items if it["status"] == "fail")
    borderline = sum(1 for it in items if it["status"] == "borderline")
    points = sum({"pass": 1, "borderline": 0.5, "fail": 0}[it["status"]] for it in items)
    score = 100.0 if not items else 100.0 * points / len(items)

    return AnalysisResult(
        category="accessibility", score=round(score, 1),
        measurements={"text_boxes": len(items), "failing": failing,
                      "min_ratio": min((it["ratio"] for it in items), default=None),
                      "items": items, "borderline": borderline},
        issues=issues)
