def find_strengths(results) -> list:
    """Positive observations, read from the same measurements the issues come from,
    so the review says what to keep and not just what to fix."""
    out = []
    acc = results["accessibility"].measurements
    col = results["color"].measurements
    lay = results["layout"].measurements
    typ = results["typography"].measurements
    hie = results["hierarchy"].measurements

    n, failing = acc["text_boxes"], acc["failing"]
    if n >= 3 and failing == 0 and acc["borderline"] == 0:
        out.append(("accessibility", f"All {n} bits of text are easy to read."))
    elif n >= 5 and (failing + acc["borderline"]) / n <= 0.15:
        out.append(("accessibility", f"Almost all text is easy to read ({n - failing - acc['borderline']} of {n})."))

    names = col.get("accent_names", [])
    if 1 <= col["distinct_hues"] <= 2 and not col["vibrating_pairs"]:
        out.append(("color", f"Nice, simple colours: {' and '.join(names[:2]) or 'one colour'} "
                             f"{'pop' if len(names[:2]) > 1 else 'pops'} against calm backgrounds."))

    focal = hie["focal_points"]
    competing = len(focal) >= 2 and focal[1]["share"] / max(focal[0]["share"], 1e-9) > 0.6
    if focal and focal[0]["share"] >= 0.25 and not competing and hie["busy_fraction"] < 0.20:
        what = f'"{focal[0]["texts"][0]}"' if focal[0].get("texts") else "the main picture"
        out.append(("hierarchy", f"Clear starting point: the eye goes straight to {what}."))
    if hie["busy_fraction"] < 0.08:
        out.append(("ux", "Clean and calm, with no visual clutter."))

    ratio, levels = typ.get("size_ratio"), typ.get("size_levels", 0)
    if ratio and ratio >= 2 and 2 <= levels <= 6:
        out.append(("typography", f"Headings clearly stand out, using just {levels} text sizes."))

    ws = lay["whitespace_ratio"]
    if 0.25 <= ws <= 0.60:
        out.append(("layout", f"Good breathing room ({ws:.0%} open space)."))
    if lay["misaligned_groups"] == 0 and n >= 5:
        out.append(("layout", "Text lines up neatly."))
    return out
