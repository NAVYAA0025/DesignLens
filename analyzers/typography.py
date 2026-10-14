import numpy as np
from PIL import Image
from core.models import Issue, AnalysisResult
from analyzers.contrast import _estimate_colors


def _group_sizes(heights, step=1.35):
    """A new size level starts when a height is >35% bigger than the first
    height of the current level."""
    hs = sorted(heights)
    levels = [[hs[0]]]
    for h in hs[1:]:
        if h > levels[-1][0] * step:
            levels.append([h])
        else:
            levels[-1].append(h)
    return levels


def _short(t):
    return t if len(t) <= 24 else t[:21] + "..."


def analyze_typography(img: Image.Image, text_items) -> AnalysisResult:
    W, H = img.size
    arr = np.asarray(img.convert("RGB"))
    items = [dict(it) for it in text_items if it["bbox"][3] >= 6 and it["bbox"][2] >= 4]
    if len(items) < 3:   # too little text to judge
        return AnalysisResult("typography", 100.0,
                              {"size_levels": 0, "size_ratio": None, "items": []}, [])

    for it in items:
        x, y, w, h = it["bbox"]
        fg, bg = _estimate_colors(arr, x, y, w, h)
        span = np.linalg.norm(fg - bg)
        crop = arr[y:y + h, x:x + w].astype(np.float64)
        dist = np.linalg.norm(crop - bg, axis=2)
        it["height"] = h
        it["ink"] = round(float((dist > span * 0.5).mean()), 3) if span > 1 else 0.0

    heights = [it["height"] for it in items]
    levels = _group_sizes(heights)
    size_ratio = round(max(heights) / min(heights), 1)

    x0 = min(it["bbox"][0] for it in items)
    y0 = min(it["bbox"][1] for it in items)
    x1 = max(it["bbox"][0] + it["bbox"][2] for it in items)
    y1 = max(it["bbox"][1] + it["bbox"][3] for it in items)
    text_area = (x0, y0, x1 - x0, y1 - y0)

    # body size = the size level holding the most text blocks; suggest a 1.25x scale from it
    body_level = max(levels, key=len)
    body = int(round(float(np.median(body_level))))
    scale = [body] + [int(round(body * 1.25 ** k)) for k in (1, 2, 3, 4)]
    scale_txt = " / ".join(f"{s}px" for s in scale)

    issues = []
    too_many = len(levels) >= 7
    weak = len(items) >= 4 and size_ratio < 1.5
    if too_many:
        issues.append(Issue(
            "typography", "medium", text_area,
            f"There are about {len(levels)} different text sizes.",
            "People can't tell what's a heading and what's normal text.",
            f"Stick to about 5 sizes. Based on your normal text, try {scale_txt}.",
            effort="moderate", title="Too many text sizes"))
    if weak:
        issues.append(Issue(
            "typography", "medium", text_area,
            f"Your biggest text is only {size_ratio}x bigger than the smallest.",
            "Everything looks equally important, so it's hard to skim.",
            f"Make headings about {int(body * 2)}-{int(body * 2.5)}px and sub-headings about {int(body * 1.5)}px "
            f"(your normal text is {body}px). Making them bold helps too.",
            effort="moderate", title="Headings don't stand out"))

    tiny_cut = 0.007 * W
    tiny = sorted((it for it in items if it["height"] < tiny_cut),
                  key=lambda it: it["height"])[:6]
    target = max(int(round(tiny_cut)), int(round(0.85 * body)))
    if tiny:
        texts = ", ".join(f'"{_short(it["text"])}"' for it in tiny[:3]) + (f" and {len(tiny) - 3} more" if len(tiny) > 3 else "")
        smallest = tiny[0]["height"]
        issues.append(Issue(
            "typography", "medium" if smallest < 0.005 * W else "low", tiny[0]["bbox"],
            (f"The text {texts} is tiny ({smallest}px)." if len(tiny) == 1 else
             f"{len(tiny)} bits of text ({texts}) are tiny, some only {smallest}px tall."),
            "Small text is easy to miss and hard to read on a phone.",
            f"Make {'it' if len(tiny) == 1 else 'them'} at least {target}px (about 14-16px on a real screen), "
            "or remove anything that isn't needed.",
            effort="quick", title="Some text is too small", regions=[it["bbox"] for it in tiny[1:]]))
    thin = [it for it in items if it["height"] >= 30 and it["ink"] < 0.10]
    if thin:
        texts = ", ".join(f'"{_short(it["text"])}"' for it in thin[:3]) + (f" and {len(thin) - 3} more" if len(thin) > 3 else "")
        issues.append(Issue(
            "typography", "low", thin[0]["bbox"],
            f"The big text {texts} uses a super-thin font.",
            "Thin letters fade away on small screens and busy backgrounds.",
            "Fine for a big decorative heading. For anything people need to read, use a normal or medium weight.",
            effort="quick", title="Very thin font", regions=[it["bbox"] for it in thin[1:]]))
    score = 100 - (15 if too_many else 0) - (20 if weak else 0) - min(20, 5 * len(tiny)) - min(10, 5 * len(thin))    
    return AnalysisResult(
        "typography", float(max(0, min(100, score))),
        {"size_levels": len(levels), "size_ratio": size_ratio,
         "levels": [(min(l), max(l), len(l)) for l in levels],
         "tiny_cut_px": round(tiny_cut, 1), "body_px": body, "suggested_scale": scale, "items": items},
        issues)