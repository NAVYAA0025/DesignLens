from itertools import combinations
import cv2
import numpy as np
from PIL import Image
from core.models import Issue, AnalysisResult


def analyze_layout(img: Image.Image, text_boxes=None, grid=(12, 8)) -> AnalysisResult:
    W, H = img.size
    small = img.copy()
    small.thumbnail((800, 800))
    gray = cv2.cvtColor(np.asarray(small.convert("RGB")), cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 30, 90) > 0

    # --- density grid: which cells contain content? ---
    cols, rows = grid
    ys = np.linspace(0, edges.shape[0], rows + 1).astype(int)
    xs = np.linspace(0, edges.shape[1], cols + 1).astype(int)
    density = np.zeros((rows, cols))
    for r in range(rows):
        for c in range(cols):
            density[r, c] = edges[ys[r]:ys[r + 1], xs[c]:xs[c + 1]].mean()
    occupied = density > 0.01
    whitespace_ratio = float(1 - occupied.mean())

    total = density.sum()
    if total > 0:
        balance_x = float((density.sum(axis=0) * (np.arange(cols) + 0.5)).sum() / total / cols)
        balance_y = float((density.sum(axis=1) * (np.arange(rows) + 0.5)).sum() / total / rows)
    else:
        balance_x = balance_y = 0.5

    issues = []
    full = (0, 0, W, H)
    crowded = whitespace_ratio < 0.10
    sparse = whitespace_ratio > 0.90
    if crowded:
        issues.append(Issue(
            "layout", "medium", full,
            f"Only about {whitespace_ratio:.0%} of the page is empty space.",
            "Without room to breathe, it's hard to tell which things belong together.",
            "Add more space between sections (about double the gap inside a section) and move less important "
            "things further down.",
            effort="major", title="Feels crowded"))
    if sparse:
        issues.append(Issue(
            "layout", "low", full,
            f"About {whitespace_ratio:.0%} of the page is empty.",
            "Things feel far apart and the page can look unfinished.",
            "Move related things closer together, or use the space for one big eye-catching element.",
            effort="moderate", title="Feels a bit empty"))

    # --- alignment: left edges that almost match, but not quite ---
    boxes = [tuple(b) for b in (text_boxes or []) if b[3] >= 8]
    # keep only the first block of each text row; later blocks in a row (nav items,
    # inline labels) are spaced horizontally by design, not aligned to a column
    boxes.sort(key=lambda b: (b[1], b[0]))
    row_starts = []
    for b in boxes:
        cy = b[1] + b[3] / 2
        same_row = [r for r in row_starts if abs(r[1] + r[3] / 2 - cy) < 0.5 * max(r[3], b[3])]
        if not same_row:
            row_starts.append(b)
        elif b[0] < same_row[0][0]:
            row_starts[row_starts.index(same_row[0])] = b
    boxes = row_starts
    tol = max(4, round(W * 0.004))      # below this: treated as aligned (glyph shapes cause small offsets)
    near = max(12, round(W * 0.012))    # tol..near apart: looks like an attempted alignment that missed
    boxes.sort(key=lambda b: b[0])
    groups, cur = [], []
    for b in boxes:
        if cur and b[0] - cur[-1][0] > near:
            groups.append(cur)
            cur = []
        cur.append(b)
    if cur:
        groups.append(cur)

    misaligned = 0
    for g in groups:
        left = [b[0] for b in g]
        span = max(left) - min(left)
        stacked = any(a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1] for a, b in combinations(g, 2))
        if len(g) < 2 or span <= tol or not stacked:
            continue
        # the most common left edge is the "intended" one; blocks off it are the problem
        mode = max(left, key=lambda v: sum(abs(v - u) <= tol for u in left))
        off = [b for b in g if abs(b[0] - mode) > tol]
        if not off:
            continue
        misaligned += 1
        x0 = min(b[0] for b in off)
        y0 = min(b[1] for b in off)
        x1 = max(b[0] + b[2] for b in off)
        y1 = max(b[1] + b[3] for b in off)
        shift = round(sum(b[0] - mode for b in off) / len(off))
        side = "right" if shift > 0 else "left"
        issues.append(Issue(
            "layout", "low", (x0, y0, x1 - x0, y1 - y0),
            f"{len(off)} bit{'s' if len(off) > 1 else ''} of text {'are' if len(off) > 1 else 'is'} "
            f"{abs(shift)}px out of line with the text around {'them' if len(off) > 1 else 'it'}.",
            "Almost-lined-up looks like a mistake, and makes the page feel less tidy.",
            f"Nudge {'them' if len(off) > 1 else 'it'} {abs(shift)}px to the {'left' if side == 'right' else 'right'} "
            "so the left edges match.",
            effort="quick", title="Text slightly out of line"))

    score = 100 - 10 * misaligned - (25 if crowded else 0) - (10 if sparse else 0)

    return AnalysisResult(
        category="layout", score=float(max(0, min(100, score))),
        measurements={"whitespace_ratio": round(whitespace_ratio, 2),
                      "balance_x": round(balance_x, 2), "balance_y": round(balance_y, 2),
                      "occupied_map": occupied.tolist(), "misaligned_groups": misaligned},
        issues=issues)