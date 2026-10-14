from dataclasses import dataclass, field


@dataclass
class Issue:
    category: str   # color | accessibility | typography | layout | hierarchy | ux
    severity: str   # high | medium | low
    bbox: tuple     # (x, y, w, h) in ORIGINAL image pixels
    what: str       # what we noticed
    why: str        # why it matters
    fix: str        # how to improve it
    priority: int = 0
    title: str = ""                                 # short plain-language headline
    effort: str = "moderate"                       # quick | moderate | major
    regions: list = field(default_factory=list)    # extra boxes when one issue covers several elements


@dataclass
class AnalysisResult:
    category: str
    score: float                                   # 0-100
    measurements: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)     # list[Issue]

@dataclass
class Review:
    overall: float
    categories: dict    # name -> AnalysisResult
    issues: list        # all Issues, ranked (issue.priority = rank)
    timings: dict
    strengths: list = field(default_factory=list)  # list[(category, text)]
