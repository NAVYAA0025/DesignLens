from datetime import date

EFFORT = {"quick": "quick fix", "moderate": "moderate", "major": "bigger change"}


def build_report(review, dna, name="screenshot", mentor_text=None) -> str:
    """Markdown version of the review, for sharing or handing in."""
    lines = [f"# DesignLens AI review: {name}", f"_Generated {date.today():%d %b %Y}_", "",
             f"**Overall score: {review.overall:.0f}/100**", ""]
    lines += ["| Category | Score |", "|---|---|"]
    lines += [f"| {k.capitalize()} | {r.score:.0f} |" for k, r in review.categories.items()]
    lines += ["", "## Design DNA", f"**{dna['archetype']}**: {dna['summary']}", "",
              ", ".join(f"{k}: {v}" for k, v in dna["traits"].items()), ""]
    if mentor_text:
        lines += ["## Mentor summary", mentor_text, ""]
    if review.strengths:
        lines += ["## What's working"] + [f"- {t}" for _, t in review.strengths] + [""]
    lines += ["## Recommendations"]
    if not review.issues:
        lines.append("No issues detected.")
    for i in review.issues:
        lines += [f"### {i.priority}. {i.title or i.category.capitalize()} ({EFFORT.get(i.effort, i.effort)})",
                  f"- **What:** {i.what}", f"- **Why it matters:** {i.why}", f"- **How to improve:** {i.fix}", ""]
    return "\n".join(lines)
