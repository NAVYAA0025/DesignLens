# DesignLens AI

**An AI-powered design mentor for website design.**

DesignLens AI analyzes website screenshots and gives you clear, actionable feedback on what works, what doesn't, and how to improve it.

It combines visual analysis with an optional local AI mentor to help you make better design decisions.

## Features

* **Design Score** — An overall score out of 100, with individual ratings for readability, colour, layout, typography, and visual focus.
* **Things to Fix** — Issues highlighted directly on your screenshot, explaining what's wrong, why it matters, and exactly how to fix it.
* **What's Working** — Highlights the design choices worth keeping.
* **Design DNA** — Breaks down your design's personality, tone, energy, density, and colour palette.
* **AI Mentor** — Optional design feedback from a local vision model powered by Ollama.

## Getting Started

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

For macOS/Linux, use `source .venv/bin/activate` instead.

Start the app:

```bash
streamlit run app.py
```

Open `http://localhost:8501` and upload a screenshot or choose a sample.

To open a sample directly:

```text
http://localhost:8501/?sample=neon_poster.png
```

### Optional AI Mentor

Install [Ollama](https://ollama.com) and pull the vision model:

```bash
ollama pull qwen2.5vl:3b
```

Once Ollama is running, click **Ask AI Mentor** in the dashboard.

## How It Works

1. **Text Detection** — RapidOCR identifies text and its position in the screenshot.
2. **Visual Analysis** — Individual analyzers evaluate contrast, colour, typography, layout, and visual hierarchy.
3. **Scoring** — Results are combined into an overall score, with issues ranked by importance.
4. **Feedback** — Problems are highlighted on the screenshot with specific suggestions for improvement.

## Project Structure

```text
DesignLens1/
├── app.py              # Streamlit dashboard
├── core/               # Pipeline, scoring, Design DNA, AI mentor
├── analyzers/          # Contrast, colour, typography, layout, hierarchy
├── samples/            # Example screenshots
├── scripts/            # Command-line analysis tools
├── tests/              # Analyzer tests
├── outputs/            # Generated results
└── requirements.txt
```

## Command-Line Usage

Run a full analysis:

```bash
python scripts/run_all.py samples/dark_landing.png
```

Run an individual analyzer:

```bash
python scripts/run_contrast.py samples/neon_poster.png
```

Other scripts include `run_color`, `run_layout`, `run_typography`, `run_hierarchy`, and `run_dna`.

---

**Note:** DesignLens scores are based on measurable visual properties. They're meant to guide improvements, not replace human design judgement.
