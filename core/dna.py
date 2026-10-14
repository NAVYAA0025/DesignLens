from PIL import Image


def _pick(value, cuts, labels):
    return labels[sum(value >= c for c in cuts)]


def generate_dna(img: Image.Image, review) -> dict:
    cats = review.categories
    color = cats["color"].measurements
    layout = cats["layout"].measurements
    hier = cats["hierarchy"].measurements
    typo = cats["typography"].measurements

    gray = img.convert("L")
    gray.thumbnail((200, 200))
    brightness = sum(gray.getdata()) / (255 * gray.size[0] * gray.size[1])

    accent_share = sum(a["share"] for a in color["accents"])
    focal = hier["focal_points"]
    top_share = focal[0]["share"] if focal else 0.0
    ratio = typo["size_ratio"]

    if layout["whitespace_ratio"] < 0.20 or hier["busy_fraction"] >= 0.20:
        density = "dense"
    elif layout["whitespace_ratio"] > 0.55:
        density = "airy"
    else:
        density = "balanced"

    traits = {
        "tone": _pick(brightness, [0.30, 0.60], ["dark", "mid-tone", "light"]),
        "temperature": color["temperature"],
        "energy": _pick(accent_share, [0.01, 0.06], ["muted", "restrained", "vibrant"]),
        "density": density,
        "type": "n/a" if ratio is None else _pick(ratio, [3, 8], ["understated", "expressive", "dramatic"]),
        "focus": "single focal point" if top_share >= 0.25 else "distributed attention",
    }

    if traits["density"] == "dense":
        archetype = "Dense & Informational"
    elif traits["tone"] == "dark" and traits["type"] == "dramatic":
        archetype = "Dark & Dramatic"
    elif traits["density"] == "airy" and traits["energy"] == "muted":
        archetype = "Minimal & Quiet"
    elif traits["energy"] == "vibrant":
        archetype = "Bold & Energetic"
    else:
        archetype = "Balanced & Neutral"

    def article(word):
        return "an" if word[0] in "aeiou" else "a"

    parts = [f"{traits['energy']} color", f"{article(traits['density'])} {traits['density']} layout"]
    if traits["type"] != "n/a":
        parts.append(f"{traits['type']} typography")
    parts.append(traits["focus"])
    summary = (f"{article(traits['tone'])} {traits['tone']}, {traits['temperature']} interface with "
               + ", ".join(parts[:-1]) + f" and {parts[-1]}.").capitalize()
    
    return {"archetype": archetype, "traits": traits, "summary": summary,
            "raw": {"brightness": round(brightness, 2), "accent_share": round(accent_share, 3),
                    "top_focal_share": round(top_share, 3), "size_ratio": ratio}}