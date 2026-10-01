"""Independent reading-path contracts; no ChainBench or NumPy imports."""

import base64
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.images = []
        self.card = None
        self.divs = []
        self.flow = None
        self.flow_depth = None
        self.flows = {}
        self.code = None
        self.meaning = None
        self.rows = {}
        self.cell = None
        self.language = None
        self.context = None
        self.contexts = []
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if tag == "a":
            self.links.append(a)
            self.card = a.get("href") if "tour-card" in a.get("class", "").split() else None
        if tag == "img" and self.card == "backtracking.html":
            self.images.append(a.get("src"))
        if tag == "div":
            self.divs.append(a)
            if "data-backtracking-flow" in a:
                self.flow = a["data-backtracking-flow"]
                self.flow_depth = len(self.divs)
                if self.flow in self.flows:
                    raise RuntimeError("duplicate backtracking flow")
                self.flows[self.flow] = []
        if tag == "code" and self.flow is not None:
            self.code = []
        if tag == "tr" and "data-backtracking-meaning" in a:
            self.meaning = a["data-backtracking-meaning"]
            if self.meaning in self.rows:
                raise RuntimeError("duplicate backtracking meaning")
            self.rows[self.meaning] = []
        if tag == "td" and self.meaning is not None:
            self.cell = {"ko": "", "en": ""}
        if tag == "span" and self.cell is not None:
            self.language = a.get("lang")
        if tag == "p" and "data-backtracking-preview-context" in a:
            self.context = []

    def handle_data(self, text):
        if self.code is not None:
            self.code.append(text)
        if self.cell is not None and self.language in ("ko", "en"):
            self.cell[self.language] += text
        if self.context is not None:
            self.context.append(text)

    def handle_endtag(self, tag):
        if tag == "a":
            self.card = None
        if tag == "code" and self.code is not None:
            self.flows[self.flow].append("".join(self.code))
            self.code = None
        if tag == "div":
            if self.flow_depth == len(self.divs):
                self.flow = None
                self.flow_depth = None
            if self.divs:
                self.divs.pop()
        if tag == "span":
            self.language = None
        if tag == "td" and self.cell is not None:
            self.rows[self.meaning].append(self.cell)
            self.cell = None
        if tag == "tr":
            self.meaning = None
        if tag == "p" and self.context is not None:
            self.contexts.append("".join(self.context))
            self.context = None


def require(condition, message):
    if not condition:
        raise RuntimeError("Backtracking tour: " + message)


def validate_backtracking_tour_metadata(artifact, record, language):
    expected = dict(
        layer="controlled backtracking illustrations; all declared trials retained",
        command=["geometry", "fista-backtracking", "--steps", "18", "--lang", language],
        source=record["source"],
        steps=18,
        dimension=2,
        cases=[c["id"] for c in record["cases"]],
        input_sha256={c["id"]: c["input_sha256"] for c in record["cases"]},
        metric="original-objective gap and signed candidate model difference",
        variant=dict(
            initial_L=[0.25, 1.0, 4.0],
            eta=2.0,
            carry="accepted L",
            acceptance_tolerance=0.0,
            stopping="fixed_budget",
        ),
        gate=record["gate"],
        preview=dict(
            case="lambda0.8-zero-L1",
            iteration=1,
            attempt=0,
            trial_L=1.0,
            accepted=False,
            view="model",
            height="F(u)-F* and Q_L(u,y)-F* on the first rejected candidate line",
        ),
    )
    require(all(artifact.get(k) == v for k, v in expected.items()), "metadata differs")
    require(
        record["parameters"]["steps"] == 18 and len(record["cases"]) == 36,
        "budget/case count differs",
    )


def validate_backtracking_tour_presentation(folder):
    index = (folder / "index.html").read_text(encoding="utf8")
    report = (folder / "backtracking.html").read_text(encoding="utf8")
    parsed = Elements(index)
    require(
        parsed.flows
        == {
            "fixed": ["L=9", "z=y_k−∇f(y_k)/9", "x_k=soft(z,λ/9)", "t_next, y_next"],
            "backtracking": [
                "L=L_{k−1}",
                "z=y_k−∇f(y_k)/L; q=soft(z,λ/L)",
                "F(q)≤Q_L(q,y_k)?",
                "x_k=q; L_k=L; t_next, y_next",
            ],
        },
        "symbolic flow differs",
    )
    expected = {
        "inputs": (
            "3 λ values × 3 starts = 9 FISTA runs",
            "3 λ values × 4 starts × 3 L₀ guesses = 36 runs",
        ),
        "curvature": ("L=9, step size 1/9", "L₀∈{0.25,1,4}; double L on rejection, step size 1/L"),
        "threshold": ("λ/9", "λ/L"),
        "test": (
            "9 bounds both curvatures 1 and 9; no candidate search",
            "First candidate q with F(q)≤Q_L(q,y)",
        ),
        "carry": ("Always 9", "Keep the accepted L; no reset or decrease"),
        "envelope": ("18R²/(k+1)², α=1", "36R²/(k+1)², α=η=2, all L₀≤9"),
        "work": (
            "One candidate per accepted update",
            "An accepted update may contain several rejected trials",
        ),
    }
    require(list(parsed.rows) == list(expected), "comparison row coverage differs")
    for name, values in expected.items():
        row = parsed.rows[name]
        require(
            len(row) == 3 and all(cell["ko"] and cell["en"] for cell in row),
            "bilingual comparison cell missing",
        )
        require(tuple(cell["en"] for cell in row[1:]) == values, "comparison meaning differs")
    require(
        len(parsed.contexts) == 1
        and all(
            parsed.contexts[0].count(value) == 2
            for value in ("λ=0.8, x₀=(0,0), L₀=1", "q=(0.6,−6.4)", "163.84>0")
        ),
        "preview input/value caption differs",
    )
    case = re.search(
        r'<section\b[^>]*data-bt-case="lambda0.8-zero-L1"[^>]*>(.*?)(?=<section\b[^>]*data-bt-case=|\Z)',
        report,
        flags=re.S,
    )
    models = (
        [
            s
            for s in re.findall(r"<svg\b.*?</svg>", case[1], flags=re.S)
            if 'data-bt-dynamic="model_gap"' in s
        ]
        if case
        else []
    )
    prefix = "data:image/svg+xml;base64,"
    require(
        len(parsed.images) == 1 and len(models) == 1 and parsed.images[0].startswith(prefix),
        "preview source differs",
    )
    try:
        raw = base64.b64decode(parsed.images[0][len(prefix) :], validate=True).decode("utf8")
        element = ET.fromstring(raw)
    except (ValueError, UnicodeError, ET.ParseError) as error:
        raise RuntimeError("Backtracking tour: invalid SVG preview") from error
    require(
        raw == models[0] and element.tag == "{http://www.w3.org/2000/svg}svg",
        "preview differs from actual first trial",
    )
    for name, target in (
        ("proximal.html", "backtracking.html"),
        ("backtracking.html", "proximal.html"),
        ("atlas.html", "backtracking.html"),
    ):
        links = Elements((folder / name).read_text(encoding="utf8")).links
        require(
            [a.get("href") for a in links if "data-tour-backtracking" in a] == [target]
            and [a.get("href") for a in links if "data-tour-backtracking-guide" in a]
            == ["index.html#step-selection"],
            "comparison navigation differs",
        )
