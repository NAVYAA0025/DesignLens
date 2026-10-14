import colorsys
import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
from core.models import Issue, AnalysisResult
from itertools import combinations
from analyzers.contrast import contrast_ratio


def _hsv(rgb):
    r, g, b = (v / 255 for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s, v


def hue_name(h):
    for limit, name in ((15, "red"), (45, "orange"), (70, "yellow"), (160, "green"),
                        (200, "teal"), (250, "blue"), (290, "purple"), (345, "pink")):
        if h < limit:
            return name
    return "red"


def analyze_color(img: Image.Image, k: int = 6) -> AnalysisResult:
    w, h = img.size
    small = img.copy()
    small.thumbnail((200, 200))  # speed: cluster on a tiny copy
    pixels = np.asarray(small, dtype=np.float32).reshape(-1, 3)

    km = KMeans(n_clusters=k, n_init=3, random_state=0).fit(pixels)
    shares = np.bincount(km.labels_, minlength=k) / len(pixels)

    palette = []
    for i in np.argsort(-shares):
        rgb = tuple(int(round(c)) for c in km.cluster_centers_[i])
        hue, sat, val = _hsv(rgb)
        palette.append({"hex": "#%02x%02x%02x" % rgb, "share": round(float(shares[i]), 3),
                        "hue": hue, "sat": sat, "val": val})

        # --- accent detection: isolate colorful pixels, then cluster only those ---
    mid = img.copy()
    mid.thumbnail((400, 400))  # bigger than before so thin colored text survives
    arr = np.asarray(mid, dtype=np.uint8)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV).reshape(-1, 3)  # H 0-179, S/V 0-255
    pix = arr.reshape(-1, 3).astype(np.float32)

    colorful = (hsv[:, 1] > 90) & (hsv[:, 2] > 60)  # saturation > ~35%, not near-black
    colorful_share = float(colorful.mean())
    cp = pix[colorful]

    chromatic = []
    if len(cp) >= 30:
        if len(cp) > 20000:  # subsample for speed
            cp = cp[np.random.default_rng(0).choice(len(cp), 20000, replace=False)]
        n = min(4, len(cp))
        km2 = KMeans(n_clusters=n, n_init=3, random_state=0).fit(cp)
        frac = np.bincount(km2.labels_, minlength=n) / len(cp)
        for i in np.argsort(-frac):
            rgb = tuple(int(round(c)) for c in km2.cluster_centers_[i])
            hue, sat, val = _hsv(rgb)
            share = float(frac[i]) * colorful_share
            if share >= 0.005:  # 0.5% of the image is enough for an accent
                chromatic.append({"hex": "#%02x%02x%02x" % rgb, "share": round(share, 3),
                                  "hue": hue, "sat": sat, "val": val})

    # hue families: neighbouring hues (orange + yellow) count as ONE family
    hues = sorted(p["hue"] for p in chromatic)
    # --- harshness checks ---
    neon_share = float(((hsv[:, 1] > 204) & (hsv[:, 2] > 204)).mean())
    saturated_cov = float(((hsv[:, 1] > 153) & (hsv[:, 2] > 102)).mean())  # saturation > 0.6, not dark

    def _rgb(hexstr):
        return tuple(int(hexstr[i:i + 2], 16) for i in (1, 3, 5))

    vibrating = []
    strong = [p for p in chromatic if p["share"] >= 0.02 and p["sat"] > 0.6 and p["val"] > 0.4]
    for a, b in combinations(strong, 2):
        diff = abs(a["hue"] - b["hue"])
        diff = min(diff, 360 - diff)
        if diff >= 150 and contrast_ratio(_rgb(a["hex"]), _rgb(b["hex"])) < 1.5:
            vibrating.append((a["hex"], b["hex"]))
    distinct_hues = (1 + sum(1 for a, b in zip(hues, hues[1:]) if b - a > 30)) if hues else 0

    warm = sum(p["share"] for p in chromatic if p["hue"] < 70 or p["hue"] >= 330)
    cool = sum(p["share"] for p in chromatic if 150 <= p["hue"] <= 270)
    if not chromatic:
        temperature = "neutral"
    elif warm > 1.5 * cool:
        temperature = "warm"
    elif cool > 1.5 * warm:
        temperature = "cool"
    else:
        temperature = "balanced"

    mean_sat = sum(p["share"] * p["sat"] for p in palette)

    issues = []
    full = (0, 0, w, h)
    names = []
    for p in chromatic:
        n = hue_name(p["hue"])
        if n not in names:
            names.append(n)
    if distinct_hues >= 4:
        primary = chromatic[0]
        issues.append(Issue(
            "color", "medium", full,
            f"Your page uses {distinct_hues} different colours ({', '.join(names)}).",
            "With this many colours, nothing feels important and the page looks a bit messy.",
            f"Keep {hue_name(primary['hue'])} ({primary['hex']}) as your main colour, since you use it most. "
            "Add at most one helper colour and make the rest grey or softer shades.",
            effort="moderate", title="Too many colours"))
    if not chromatic:
        issues.append(Issue(
            "color", "low", full,
            "The page is almost all greys, black and white.",
            "Without one bright colour, buttons and links don't catch the eye.",
            "Add one bright colour (a blue or orange works well) and use it only for buttons and links.",
            effort="moderate", title="No colour that pops"))
    if vibrating:
        issues.append(Issue(
            "color", "medium", full,
            f"{vibrating[0][0]} and {vibrating[0][1]} are bright, opposite colours at the same brightness.",
            "Side by side they seem to flicker and tire the eyes, and colour-blind people may not tell them apart.",
            "Make one of them much darker or lighter, or swap one for a grey.",
            effort="quick", title="Two colours clash"))
    if saturated_cov >= 0.60:
        issues.append(Issue(
            "color", "low", full,
            f"About {saturated_cov:.0%} of the page is loud, bright colour.",
            "When everything is loud, nothing stands out, and the eyes get tired fast.",
            "Put your content on a calmer, softer background and save the bright colour for the few things "
            "you want people to notice.",
            effort="moderate", title="Too much bright colour"))

    score: int = (100 - 15 * max(0, distinct_hues - 3) - (20 if not chromatic else 0) - (15 if vibrating else 0) - (10 if neon_share >= 0.15 else 0))

    return AnalysisResult(
        category="color",
        score=float(max(0, min(100, score))),
                        measurements={"palette": palette, "distinct_hues": distinct_hues,
                      "temperature": temperature, "mean_saturation": round(mean_sat, 2),
                      "accents": chromatic, "accent_names": names, "saturated_coverage": round(saturated_cov, 3),
                      "neon_share": round(neon_share, 3), "vibrating_pairs": vibrating},
        issues=issues,
    )
