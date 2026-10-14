import cv2
import numpy as np
from PIL import Image
from core.models import Issue, AnalysisResult


def _where(cx, cy, W, H):
    h = "left" if cx < W / 3 else "right" if cx > 2 * W / 3 else "center"
    v = "top" if cy < H / 3 else "bottom" if cy > 2 * H / 3 else "middle"
    return "center" if (v, h) == ("middle", "center") else f"{v} {h}"


def _blobs(sal, thr=0.40, min_area_frac=0.005):
    mask = (sal > thr).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, labels, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    total = sal.sum() + 1e-9
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < min_area_frac * sal.size:
            continue
        out.append({"bbox": (int(x), int(y), int(w), int(h)),
                    "share": float(sal[labels == i].sum() / total),
                    "center": (float(cents[i][0]), float(cents[i][1]))})
    out.sort(key=lambda b: -b["share"])
    return out[:3]


def _overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def _describe(f):
    """Human label for a focal area: its largest text if it has any, else its position."""
    if f["texts"]:
        t = f["texts"][0]
        t = t if len(t) <= 30 else t[:27] + "..."
        return f'the "{t}" part'
    return f"the picture at the {f['where']}"


def analyze_hierarchy(img: Image.Image, text_boxes=None, text_items=None) -> AnalysisResult:
    if text_items is not None and text_boxes is None:
        text_boxes = [it["bbox"] for it in text_items]
    W, H = img.size
    small = img.convert("RGB")
    small.thumbnail((400, 400))
    sw, sh = small.size
    sx, sy = W / sw, H / sh
    rgb = np.asarray(small)

    def up(b):  # small-image box -> original-image box
        return (int(b[0] * sx), int(b[1] * sy), int(b[2] * sx), int(b[3] * sy))

    # --- saliency: how far each (slightly blurred) pixel is from the page's average color ---
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    blur = cv2.GaussianBlur(lab, (0, 0), 3)
    sal = np.linalg.norm(blur - lab.reshape(-1, 3).mean(axis=0), axis=2)
    sal = sal / (sal.max() + 1e-6)

    blobs = _blobs(sal)
    focal = []
    for b in blobs:
        box = up(b["bbox"])
        inside = sorted((it for it in (text_items or []) if _overlaps(box, tuple(it["bbox"]))),
                        key=lambda it: -it["bbox"][3])          # biggest text first
        focal.append({"bbox": box, "share": round(b["share"], 3),
                      "where": _where(b["center"][0] * sx, b["center"][1] * sy, W, H),
                      "has_text": any(_overlaps(box, tuple(t)) for t in (text_boxes or [])),
                      "texts": [it["text"] for it in inside[:3]]})

    # --- clutter: edge density on a grid ---
    gray = cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), (5, 5), 0)
    edges = cv2.Canny(gray, 30, 90) > 0
    for (tx, ty, tw, th) in (text_boxes or []):   # text isn't clutter: blank out OCR boxes
        bx0, by0 = max(0, int(tx / sx) - 2), max(0, int(ty / sy) - 2)
        bx1, by1 = min(sw, int((tx + tw) / sx) + 2), min(sh, int((ty + th) / sy) + 2)
        edges[by0:by1, bx0:bx1] = False
    cols, rows = 12, 8
    ys = np.linspace(0, sh, rows + 1).astype(int)
    xs = np.linspace(0, sw, cols + 1).astype(int)
    density = np.array([[edges[ys[r]:ys[r + 1], xs[c]:xs[c + 1]].mean()
                         for c in range(cols)] for r in range(rows)])
    busy = density > 0.10
    busy_fraction = float(busy.mean())

    issues = []
    competing = (len(focal) >= 2 and focal[1]["share"] >= 0.05
                 and focal[1]["share"] / focal[0]["share"] > 0.6)
    if competing:
        issues.append(Issue(
            "hierarchy", "medium", focal[1]["bbox"],
            f"{_describe(focal[1])[0].upper() + _describe(focal[1])[1:]} grabs almost as much attention "
            f"as {_describe(focal[0])}.",
            "Visitors don't know where to look first.",
            "Pick the one that matters most and keep it big and bold. Make the other smaller, duller, or move it away.",
            effort="moderate", title="Two things fight for attention"))
    unclear = len(focal) >= 1 and focal[0]["share"] < 0.12
    if unclear:
        issues.append(Issue(
            "hierarchy", "low", focal[0]["bbox"],
            "No part of the page clearly says 'look here first'.",
            "People take longer to find your main message, or miss it completely.",
            "Make your headline or main button bigger, bolder, or the only thing in your brightest colour.",
            effort="moderate", title="Nothing stands out"))
    cluttered = busy_fraction >= 0.20
    if cluttered:
        rr, cc = np.where(busy)
        box = up((xs[cc.min()], ys[rr.min()], xs[cc.max() + 1] - xs[cc.min()], ys[rr.max() + 1] - ys[rr.min()]))
        issues.append(Issue(
            "ux", "low", box,
            f"About {busy_fraction:.0%} of the page is packed with small details.",
            "With so much going on, it's tiring to find what matters.",
            "Remove extra decorations and borders, group small items together, and leave more space around each group.",
            effort="major", title="Busy, cluttered areas"))

    score = 100 - (20 if competing else 0) - (15 if unclear else 0) - (15 if cluttered else 0)
    return AnalysisResult(
        "hierarchy", float(max(0, min(100, score))),
        {"focal_points": focal, "busy_fraction": round(busy_fraction, 2),
         "density": density, "saliency": sal},
        issues)