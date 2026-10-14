import hashlib
import html
import io
import re
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from core import mentor
from core.dna import generate_dna
from core.pipeline import run_review
from core.report import build_report

st.set_page_config(page_title="DesignLens AI", page_icon="🔍", layout="wide", initial_sidebar_state="collapsed")

HERE = Path(__file__).parent
SAMPLE_DIR = HERE / "samples"
SAMPLES = {"Dark landing page": "dark_landing.png", "Neon poster": "neon_poster.png",
           "Dark poster": "dark_poster.png", "Busy page": "busy_page.png"}
SAMPLES = {k: v for k, v in SAMPLES.items() if (SAMPLE_DIR / v).exists()}

SEV = {"high": ("Big", "#be123c", (225, 29, 72)),        # (label, readable text/badge colour, box colour)
       "medium": ("Medium", "#c2410c", (249, 115, 22)),
       "low": ("Small", "#a16207", (234, 179, 8))}
CAT = {"accessibility": ("👀", "Readability"), "color": ("🎨", "Colour"), "typography": ("🔤", "Text"),
       "layout": ("📐", "Layout"), "hierarchy": ("🎯", "Focus"), "ux": ("🧭", "Clutter")}
EFFORT = {"quick": ("⚡ quick fix", "#0f766e", "#ccfbf1"),
          "moderate": ("🛠 some work", "#4338ca", "#e0e7ff"),
          "major": ("🏗 bigger change", "#9f1239", "#ffe4e6")}
ARCH_EMOJI = {"Dense & Informational": "📚", "Dark & Dramatic": "🌙", "Minimal & Quiet": "🍃",
              "Bold & Energetic": "⚡", "Balanced & Neutral": "⚖️"}
TRAIT_ICON = {"tone": "🌗", "temperature": "🌡️", "energy": "✨", "density": "🧱", "type": "🔤", "focus": "🎯"}

CSS = """
<style>
header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
footer, #MainMenu {display:none !important;}
.block-container {padding:.9rem 1.4rem .4rem !important; max-width:100% !important;}
[data-testid="stVerticalBlock"] {gap:.55rem;}
[class*="st-key-"] > div {flex-shrink:0;}
[data-testid="stMarkdownContainer"] {margin-bottom:0 !important;}   /* Streamlit pulls the next element up by 1rem */
h1,h2,h3,h4 {letter-spacing:-.01em; margin:0 !important; padding:0 !important;}

/* cards = keyed containers */
.st-key-shot, .st-key-facts, .st-key-scorecard, .st-key-fixcard, .st-key-dna, .st-key-good, .st-key-hero {
  background:#fff; border:1px solid #e6e4f3; border-radius:20px; padding:14px 16px;
  box-shadow:0 2px 10px rgba(60,50,140,.05);}
.st-key-dna {background:linear-gradient(160deg,#ffffff 0%,#f5f2ff 100%);}
.st-key-hero {margin-top:9vh; padding:26px 28px;}
.st-key-shot [data-testid="stImage"], .st-key-shot [data-testid="stImageContainer"] {display:flex; justify-content:center; width:100%;}
.st-key-shot img {max-height:calc(100vh - 372px); min-height:200px; width:auto !important; max-width:100%;
  object-fit:contain; display:block; margin:0 auto; border-radius:12px;}
.st-key-fixlist {max-height:calc(100vh - 362px); overflow-y:auto; padding-right:6px; gap:.45rem;}
.st-key-goodlist {max-height:calc(100vh - 560px); min-height:70px; overflow-y:auto;}
[class*="st-key-samples"] img {height:120px; object-fit:cover; border-radius:12px; border:1px solid #e6e4f3;}

.dl-brand {display:flex; align-items:center; gap:12px;}
.dl-logo {width:40px; height:40px; border-radius:12px; display:grid; place-items:center; font-size:20px;
          background:linear-gradient(135deg,#5b4be1,#a855f7); box-shadow:0 6px 16px rgba(91,75,225,.3);}
.dl-title {font-size:1.3rem; font-weight:800; line-height:1.05;
           background:linear-gradient(90deg,#3b2fc9,#a23be0); -webkit-background-clip:text; color:transparent;}
.dl-sub {color:#5f5b85; font-size:.82rem;}
.dl-h {font-weight:800; font-size:1rem; color:#1e1b3a; display:flex; align-items:center; gap:8px;}
.dl-muted {color:#5f5b85; font-size:.8rem;}

.dl-score {display:flex; gap:14px; align-items:center;}
.dl-ring {width:96px; height:96px; border-radius:50%; display:grid; place-items:center; flex-shrink:0;}
.dl-ring > div {width:76px; height:76px; border-radius:50%; background:#fff; display:flex; flex-direction:column;
                align-items:center; justify-content:center;}
.dl-ring b {font-size:1.7rem; line-height:1;} .dl-ring small {color:#4f4b75; font-size:.78rem;}
.dl-grade {display:inline-block; font-weight:800; font-size:.78rem; padding:2px 10px; border-radius:99px; color:#fff;}
.dl-tiles {display:flex; gap:6px; margin-top:10px;}
.dl-tile {flex:1; background:#f7f6fd; border-radius:12px; padding:6px 4px; text-align:center;}
.dl-tile .i {font-size:1rem;} .dl-tile b {display:block; font-size:1rem;} .dl-tile small {color:#5f5b85; font-size:.74rem;}

.dl-issue {border:1px solid #eeedf8; border-left:4px solid var(--c); border-radius:12px; padding:9px 11px; background:#fff;}
.dl-issue.on {background:#faf9ff; box-shadow:0 0 0 2px #5b4be1 inset;}
.dl-it {display:flex; align-items:center; gap:7px; font-weight:700; font-size:.92rem;}
.dl-num {display:inline-grid; place-items:center; min-width:22px; height:22px; border-radius:7px; color:#fff;
         font-weight:800; font-size:.74rem; background:var(--c);}
.dl-pill {display:inline-block; padding:1px 8px; border-radius:99px; font-size:.74rem; font-weight:700; white-space:nowrap;}
.dl-what {color:#5d5a80; font-size:.82rem; margin:3px 0 4px;}
.dl-fix {font-size:.85rem; background:#f2fbf6; border-radius:8px; padding:6px 9px;}
.dl-issue details {font-size:.78rem; color:#5f5b85; margin-top:4px;}
.dl-issue summary {cursor:pointer; font-weight:600;}
.dl-sw {display:inline-block; width:11px; height:11px; border-radius:3px; border:1px solid rgba(0,0,0,.2);
        vertical-align:-1px; margin-right:3px;}
.dl-issue code, .dl-table code {font-size:.76rem; padding:0 3px;}

.dl-arch {display:flex; align-items:center; gap:10px;}
.dl-arch .e {font-size:2rem; width:52px; height:52px; display:grid; place-items:center; border-radius:16px; background:#eeebff;}
.dl-arch b {font-size:1.25rem; font-weight:800; color:#1e1b3a;}
.dl-traits {display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin:10px 0;}
.dl-trait {background:#fff; border:1px solid #ebe8fb; border-radius:12px; padding:6px 8px;}
.dl-trait small {display:block; color:#5f5b85; font-size:.74rem; text-transform:uppercase; letter-spacing:.06em;}
.dl-trait span {font-weight:700; color:#3b2fc9; font-size:.86rem;}
.dl-palette {display:flex; height:34px; border-radius:10px; overflow:hidden; border:1px solid #e6e4f3;}
.dl-palette div {display:flex; align-items:flex-end; padding:2px 5px; font-size:.68rem; font-family:monospace;
  min-width:0; overflow:hidden; white-space:nowrap;}
[data-testid="stColumn"], .dl-trait, .dl-tile {min-width:0;}
.dl-trait span {display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.dl-facts {display:grid; grid-template-columns:1.1fr 1fr; gap:18px;}
.dl-eye {display:flex; align-items:center; gap:8px; font-size:.8rem; margin:5px 0;}
.dl-eye .bar {flex:1; height:7px; border-radius:99px; background:#eeedf8; overflow:hidden;}
.dl-eye .bar span {display:block; height:100%; background:linear-gradient(90deg,#5b4be1,#a855f7); border-radius:99px;}
.dl-eye .w {width:92px; color:#4f4b75; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.dl-fact {display:flex; justify-content:space-between; font-size:.8rem; padding:3px 0; border-bottom:1px dashed #eeedf8;}
.dl-fact b {color:#3b2fc9;}
.dl-good {display:flex; gap:8px; margin:5px 0; font-size:.85rem;}
.dl-good span:first-child {color:#15803d;}

table.dl-table {width:100%; border-collapse:collapse; font-size:.84rem;}
table.dl-table th {text-align:left; color:#5f5b85; font-size:.74rem; text-transform:uppercase; padding:5px 6px;
                   border-bottom:1px solid #e6e4f3;}
table.dl-table td {padding:5px 6px; border-bottom:1px solid #f0eff7;}
.dl-prev {display:inline-block; padding:2px 9px; border-radius:6px; font-weight:600;}
button[kind="tertiary"] {padding:0 !important; min-height:0 !important; font-size:.86rem !important; color:#4c3fd1 !important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
ss = st.session_state


# ---------- helpers ----------
@st.cache_data(show_spinner=False)
def get_review(data: bytes):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    review = run_review(img)
    return img, review, generate_dna(img, review)


def score_color(s):
    return "#15803d" if s >= 85 else "#b45309" if s >= 70 else "#be123c"    # all pass 4.5:1 on the light cards


def grade(s):
    return next(g for cut, g in ((90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "E")) if s >= cut)


def verdict(s):
    if s >= 90:
        return "Looking great! Just a few tiny touches left. ✨"
    if s >= 80:
        return "Nice work! A few quick fixes will make it shine."
    if s >= 70:
        return "Good start. Some things are holding it back."
    return "Needs some love. Start with the top fixes."


def esc(text):
    """HTML-escape, then show any hex colour with a swatch next to it."""
    return re.sub(r"#[0-9a-fA-F]{6}\b",
                  lambda m: f"<span class='dl-sw' style='background:{m.group(0)}'></span><code>{m.group(0)}</code>",
                  html.escape(text))


def boxes_of(issue):
    return [issue.bbox] + list(issue.regions)


def is_page_level(issue, W, H):
    x, y, w, h = issue.bbox
    return not issue.regions and w * h > 0.5 * W * H      # no specific region to point at


def annotate(img, issues, focus=None):
    W, H = img.size
    if focus is not None:      # dim everything except the focused issue's regions
        out = ImageEnhance.Brightness(img).enhance(0.35)
        for (x, y, w, h) in boxes_of(focus):
            box = (max(0, x - 6), max(0, y - 6), min(W, x + w + 6), min(H, y + h + 6))
            out.paste(img.crop(box), box[:2])
        issues = [focus]
    else:
        out = img.copy()
    d = ImageDraw.Draw(out)
    font = ImageFont.load_default(size=max(16, W // 50))
    lw = max(2, W // 350)
    for i in issues:
        c = SEV[i.severity][2]
        for n, (x, y, w, h) in enumerate(boxes_of(i)):
            d.rounded_rectangle([x - 4, y - 4, x + w + 4, y + h + 4], radius=6, outline=c, width=lw)
            if n:          # number badge only on the main region
                continue
            label = str(i.priority)
            tb = d.textbbox((0, 0), label, font=font)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
            ly = y - th - 16 if y - th - 16 >= 0 else y + h + 6
            d.rounded_rectangle([x - 4, ly, x + tw + 12, ly + th + 12], radius=6, fill=c)
            d.text((x + 4, ly + 4 - tb[1]), label, fill=(255, 255, 255), font=font)
    return out


def html_block(s):
    st.markdown(s, unsafe_allow_html=True)


def set_image(data, name):
    ss.data, ss.name, ss.focus = data, name, None


def on_upload(key):
    f = ss.get(key)
    if f is not None:
        set_image(f.getvalue(), f.name)


def use_sample(file):
    set_image((SAMPLE_DIR / file).read_bytes(), file)


def set_focus(p):
    ss.focus = None if ss.get("focus") == p else p


def sample_picker(prefix):
    with st.container(key=f"samples_{prefix}"):
        for col, (label, file) in zip(st.columns(len(SAMPLES)), SAMPLES.items()):
            with col:
                st.image(str(SAMPLE_DIR / file), width="stretch")
                st.button(label, key=f"{prefix}_{file}", on_click=use_sample, args=(file,), width="stretch")


def brand():
    html_block("<div class='dl-brand'><div class='dl-logo'>🔍</div><div>"
               "<div class='dl-title'>DesignLens AI</div>"
               "<div class='dl-sub'>Your friendly design mentor · upload a screenshot, get simple fixes</div></div></div>")


# ---------- landing ----------
if "data" not in ss and st.query_params.get("sample") in SAMPLES.values():   # e.g. ?sample=neon_poster.png for demos
    use_sample(st.query_params["sample"])
if "data" not in ss:
    _, mid, _ = st.columns([1, 2.2, 1])
    with mid:
        st.write("")
        with st.container(key="hero"):
            brand()
            st.write("")
            html_block("<div style='font-size:1.6rem;font-weight:800;line-height:1.2'>How good is your design? 👀</div>"
                       "<div class='dl-muted' style='font-size:.95rem;margin:4px 0 6px'>Drop in a screenshot of a website, "
                       "app or poster. In a few seconds you'll see what works, what to fix, and your design's personality.</div>")
            st.file_uploader("Upload a screenshot", type=["png", "jpg", "jpeg", "webp"], key="up_land",
                             on_change=on_upload, args=("up_land",), label_visibility="collapsed")
            if SAMPLES:
                html_block("<div class='dl-h' style='margin-top:4px'>…or try a sample</div>")
                sample_picker("land")
    st.stop()

# ---------- analysis ----------
data, name = ss.data, ss.name
with st.spinner("Looking at your design… 🔍"):
    img, review, dna = get_review(data)
digest = hashlib.md5(data).hexdigest()
W, H = img.size
cats = review.categories
region = [i for i in review.issues if not is_page_level(i, W, H)]
focus = next((i for i in review.issues if i.priority == ss.get("focus")), None)


@st.dialog("🤖 AI design mentor", width="large")
def mentor_dialog():
    st.caption("A local AI model looks at your screenshot and the findings, then explains them like a mentor would.")
    models = mentor.list_models()
    if not models:
        st.info("Ollama isn't running. Start it and run `ollama pull qwen2.5vl:3b`, then try again.")
        return
    default = models.index(mentor.DEFAULT_MODEL) if mentor.DEFAULT_MODEL in models else 0
    model = st.selectbox("Model", models, index=default)
    key = f"mentor_{digest}_{model}"
    if key not in ss and st.button("✨ Ask the mentor", type="primary"):
        with st.spinner("Thinking… the first time can take a couple of minutes."):
            try:
                ss[key] = mentor.mentor_review(img, review, dna, model)
            except Exception as e:      # model missing, out of memory, server stopped…
                st.error(f"The mentor couldn't answer: {e}")
    if key in ss:
        st.markdown(ss[key])


@st.dialog("👀 Text readability check", width="large")
def contrast_dialog():
    m = cats["accessibility"].measurements
    items = sorted(m["items"], key=lambda it: it["ratio"])
    st.caption(f"Read {m['text_boxes']} bits of text · {m['failing']} hard to read · {m['borderline']} a little faint. "
               "Readability needs 4.5 for normal text and 3 for big text.")
    if not items:
        st.info("No readable text was found in this screenshot.")
        return
    lab = {"pass": ("Easy to read", "#15803d"), "borderline": ("A bit faint", "#b45309"), "fail": ("Hard to read", "#be123c")}
    rows = []
    for it in items:
        t = html.escape(it["text"] if len(it["text"]) <= 26 else it["text"][:23] + "…")
        l, c = lab[it["status"]]
        sug = (f"<span class='dl-prev' style='color:{it['suggested']};background:{it['bg']}'>{t}</span> "
               f"<code>{it['suggested']}</code>") if it.get("suggested") else "—"
        rows.append(f"<tr><td><span class='dl-prev' style='color:{it['fg']};background:{it['bg']}'>{t}</span></td>"
                    f"<td><b>{it['ratio']:.1f}</b> / {it['required']:g}</td>"
                    f"<td><span class='dl-pill' style='background:{c}1f;color:{c}'>{l}</span></td><td>{sug}</td></tr>")
    html_block("<table class='dl-table'><tr><th>How it looks now</th><th>Readability</th><th>Result</th>"
               "<th>Try this colour</th></tr>" + "".join(rows) + "</table>")


# ---------- top bar ----------
t1, t2, t3 = st.columns([5, 1.1, 1.1], vertical_alignment="center")
with t1:
    brand()
with t2:
    with st.popover("📤 New design", width="stretch"):
        st.file_uploader("Upload a screenshot", type=["png", "jpg", "jpeg", "webp"], key="up_pop",
                         on_change=on_upload, args=("up_pop",))
        if SAMPLES:
            st.caption("…or try a sample")
            sample_picker("pop")
with t3:
    with st.popover("⬇️ Export", width="stretch"):
        st.download_button("📝 Review as text (Markdown)", build_report(review, dna, name),
                           file_name=f"designlens_{Path(name).stem}.md", mime="text/markdown", width="stretch")
        buf = io.BytesIO()
        annotate(img, region).save(buf, format="PNG")
        st.download_button("🖼️ Marked-up screenshot", buf.getvalue(),
                           file_name=f"designlens_{Path(name).stem}_marked.png", mime="image/png", width="stretch")

# ---------- dashboard ----------
c_img, c_mid, c_dna = st.columns([1.35, 1, 1], gap="medium")

with c_img:
    with st.container(key="shot"):
        h1, h2 = st.columns([3, 1], vertical_alignment="center")
        h1.markdown("<div class='dl-h'>🖼️ Your design</div>", unsafe_allow_html=True)
        if focus is not None:
            h2.button("✕ Show all", key="clear_focus", on_click=set_focus, args=(focus.priority,), type="tertiary")
        st.image(annotate(img, region, focus), width="stretch")
        html_block("<div class='dl-muted' style='text-align:center'>Numbers match the fix list · "
                   + " ".join(f"<span class='dl-pill' style='background:{c}1f;color:{c}'>{l}</span>" for l, c, _ in SEV.values())
                   + " · tap “Show me” to spotlight one</div>")

    with st.container(key="facts"):
        hie_m, lay_m, typ_m, col_m = (cats[k].measurements for k in ("hierarchy", "layout", "typography", "color"))
        fp = hie_m["focal_points"]
        top = max((f["share"] for f in fp), default=1) or 1
        eye = "".join(
            f"<div class='dl-eye'><span class='w'>{n}. {html.escape(chr(34) + f['texts'][0] + chr(34) if f.get('texts') else f['where'])}</span>"
            f"<div class='bar'><span style='width:{f['share'] * 100 / top:.0f}%'></span></div></div>"
            for n, f in enumerate(fp, 1)) or "<div class='dl-muted'>No clear focus areas found.</div>"
        scale = typ_m.get("suggested_scale")
        facts = [("Empty space", f"{lay_m['whitespace_ratio']:.0%}"), ("Colour mood", col_m["temperature"]),
                 ("Text sizes used", str(typ_m.get("size_levels", 0))),
                 ("Try these sizes", " · ".join(str(v) for v in scale[:4]) + "px" if scale else "—")]
        html_block("<div class='dl-facts'><div><div class='dl-h' style='margin-bottom:4px'>🎯 Where the eye goes</div>"
                   f"{eye}</div><div><div class='dl-h' style='margin-bottom:4px'>📏 Quick facts</div>"
                   + "".join(f"<div class='dl-fact'><span>{k}</span><b>{html.escape(v)}</b></div>" for k, v in facts)
                   + "</div></div>")

with c_mid:
    with st.container(key="scorecard"):
        s = review.overall
        col = score_color(s)
        tiles = "".join(
            f"<div class='dl-tile'><div class='i'>{CAT[k][0]}</div><b style='color:{score_color(r.score)}'>{r.score:.0f}</b>"
            f"<small>{CAT[k][1]}</small></div>" for k, r in cats.items())
        html_block("<div class='dl-score'>"
                   f"<div class='dl-ring' style='background:conic-gradient({col} {s}%, #eeedf8 0)'><div><b>{s:.0f}</b><small>/ 100</small></div></div>"
                   f"<div><span class='dl-grade' style='background:{col}'>Grade {grade(s)}</span>"
                   f"<div style='margin-top:6px;font-weight:700;font-size:.98rem'>{verdict(s)}</div></div></div>"
                   f"<div class='dl-tiles'>{tiles}</div>")

    with st.container(key="fixcard"):
        quick = sum(1 for i in review.issues if i.effort == "quick")
        html_block(f"<div class='dl-h'>🛠️ Things to fix <span class='dl-pill' style='background:#eeedf8;color:#3b2fc9'>"
                   f"{len(review.issues)}</span><span class='dl-pill' style='background:#ccfbf1;color:#0f766e'>"
                   f"⚡ {quick} quick</span></div>")
        with st.container(key="fixlist"):
            if not review.issues:
                st.success("Nothing to fix. Lovely! 🎉")
            for i in review.issues:
                c = SEV[i.severity][1]
                eff, efg, ebg = EFFORT.get(i.effort, EFFORT["moderate"])
                on = " on" if focus is not None and focus.priority == i.priority else ""
                html_block(f"<div class='dl-issue{on}' style='--c:{c}'>"
                           f"<div class='dl-it'><span class='dl-num'>{i.priority}</span>"
                           f"<span style='flex:1'>{html.escape(i.title or i.category.capitalize())}</span>"
                           f"<span class='dl-pill' style='background:{ebg};color:{efg}'>{eff}</span></div>"
                           f"<div class='dl-what'>{esc(i.what)}</div>"
                           f"<div class='dl-fix'>💡 {esc(i.fix)}</div>"
                           f"<details><summary>Why does this matter?</summary>{esc(i.why)}</details></div>")
                if not is_page_level(i, W, H):
                    st.button("👁 Hide spotlight" if on else "👁 Show me", key=f"f_{digest}_{i.priority}",
                              on_click=set_focus, args=(i.priority,), type="tertiary")

with c_dna:
    with st.container(key="dna"):
        traits = "".join(f"<div class='dl-trait'><small>{TRAIT_ICON.get(k, '')} {k}</small><span>{html.escape(str(v))}</span></div>"
                         for k, v in dna["traits"].items())
        pal = cats["color"].measurements["palette"]
        strip = "".join(f"<div style='flex:{max(p['share'], 0.05)};background:{p['hex']};"
                        f"color:{'#fff' if p['val'] < 0.6 else '#000'}'>{p['hex'] if p['share'] >= 0.12 else ''}</div>" for p in pal)
        html_block("<div class='dl-h' style='margin-bottom:8px'>🧬 Design DNA</div>"
                   f"<div class='dl-arch'><div class='e'>{ARCH_EMOJI.get(dna['archetype'], '🎨')}</div>"
                   f"<div><b>{html.escape(dna['archetype'])}</b><div class='dl-muted'>{html.escape(dna['summary'])}</div></div></div>"
                   f"<div class='dl-traits'>{traits}</div><div class='dl-palette'>{strip}</div>")

    with st.container(key="good"):
        html_block("<div class='dl-h'>💚 What's working</div>")
        with st.container(key="goodlist"):
            if review.strengths:
                html_block("".join(f"<div class='dl-good'><span>✔</span><span>{html.escape(t)}</span></div>"
                                   for _, t in review.strengths))
            else:
                html_block("<div class='dl-muted'>Fix a few things on the left and the good stuff will show up here.</div>")

    b1, b2 = st.columns(2)
    if b1.button("🤖 Ask AI mentor", type="primary", width="stretch"):
        mentor_dialog()
    if b2.button("👀 Readability check", width="stretch"):
        contrast_dialog()
