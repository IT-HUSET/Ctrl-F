"""Visual theme: Norwegian black metal, kept legible.

Monochrome and frostbitten. Blackletter for the logo, a readable sans for data,
typewriter for evidence quotes like a photocopied zine, a treeline and a pale
moon behind everything. Fonts are bundled in assets/fonts and embedded in the
stylesheet as data URIs: a Google Fonts link would be a network call at run time,
and Streamlit's static file route answered the font URL with the app's HTML page.

Aesthetic only, with no occult or runic symbols: this is shown to a customer.
"""
from __future__ import annotations

import base64
import functools
import html
import random
from pathlib import Path
from urllib.parse import quote

import streamlit as st

GRAIN_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>"
    "<filter id='g'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' "
    "stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter>"
    "<rect width='240' height='240' filter='url(#g)' opacity='0.55'/></svg>"
)

CSS = """
[data-testid="stApp"] {
  background-color: #050505;
  background-image: __TREES__,
    radial-gradient(circle at 88% 9%, rgba(230,225,215,0.13) 0, rgba(230,225,215,0.05) 46px, rgba(0,0,0,0) 110px),
    linear-gradient(to bottom, #050505 0%, #050505 55%, #0d1216 88%, #121a22 100%);
  background-repeat: repeat-x, no-repeat, no-repeat;
  background-position: left bottom, 0 0, 0 0;
  background-size: auto 140px, 100% 100%, 100% 100%;
  background-attachment: fixed, fixed, fixed;
}
[data-testid="stApp"]::after {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 999990;
  background-image: __GRAIN__; opacity: 0.07; mix-blend-mode: screen;
}
[data-testid="stHeader"], [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: transparent !important;
}
[data-testid="stMainBlockContainer"], .block-container { padding-bottom: 170px; }
[data-testid="stSidebar"] { background: #000 !important; border-right: 1px solid #1b1b1b; }

.ctrlf-hero { text-align: center; margin: 0.2rem 0 1.4rem; }
.ctrlf-logo {
  font-family: 'UnifrakturMaguntia', serif; font-size: clamp(3.2rem, 7vw, 6rem);
  line-height: 1; color: #e6e1d7; letter-spacing: 0.04em;
  text-shadow: 0 0 22px rgba(159,180,199,0.25), 0 2px 0 #000;
}
.ctrlf-logo::before, .ctrlf-logo::after {
  content: ""; display: inline-block; width: 12vw; height: 1px;
  vertical-align: middle; margin: 0 1.4rem;
}
.ctrlf-logo::before { background: linear-gradient(to left, #e6e1d7, rgba(230,225,215,0)); }
.ctrlf-logo::after { background: linear-gradient(to right, #e6e1d7, rgba(230,225,215,0)); }
.ctrlf-tagline {
  margin-top: 0.7rem; font-size: 0.72rem; letter-spacing: 0.32em;
  text-transform: uppercase; color: #8a8680;
}

h1, h2, h3, h4 { letter-spacing: 0.03em; color: #e6e1d7 !important; }
h2, h3 { border-bottom: 1px solid #1f1f1f; padding-bottom: 0.2rem; }

div[role="radiogroup"] { gap: 0.4rem; }
div[role="radiogroup"] label {
  border: 1px solid #2b2b2b; padding: 0.35rem 0.85rem; background: #080808;
  text-transform: uppercase; letter-spacing: 0.09em; font-size: 0.78rem;
}
div[role="radiogroup"] label:has(input:checked) {
  border-color: #e6e1d7; box-shadow: 0 0 14px rgba(159,180,199,0.2);
}

[data-testid="stExpander"] details { border: 1px solid #222 !important; background: rgba(8,8,8,0.92); }
[data-testid="stExpander"] summary:hover { color: #9fb4c7; }

[data-testid="stMarkdownContainer"] blockquote {
  font-family: 'Courier New', Courier, monospace; background: #0a0a0a;
  border-left: 3px solid #8b0000; color: #d6d0c4; padding: 0.55rem 0.9rem;
}

[data-testid="stMetricValue"] { font-family: 'PirataOne', serif; font-size: 2.6rem; color: #e6e1d7; }
[data-testid="stMetricLabel"] p {
  text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.72rem; color: #8a8680;
}

[data-testid="stAlertContainer"] {
  background: rgba(10,10,10,0.94) !important; border: 1px solid #242424;
  border-left: 3px solid #9fb4c7; color: #e6e1d7;
}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]),
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { border-left-color: #8b0000; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { border-left-color: #e6e1d7; }

button { text-transform: uppercase; letter-spacing: 0.08em; }
hr { border-color: #1f1f1f !important; }
::selection { background: #8b0000; color: #fff; }
::-webkit-scrollbar { width: 9px; }
::-webkit-scrollbar-track { background: #000; }
::-webkit-scrollbar-thumb { background: #262626; }
"""


def _svg_uri(svg: str) -> str:
    return 'url("data:image/svg+xml,' + quote(svg, safe="") + '")'


def _treeline(width: int = 900, height: int = 140, seed: int = 7) -> str:
    """A jagged spruce skyline, generated rather than drawn, so it tiles cheaply."""
    rnd = random.Random(seed)
    polys, x = [], -20
    while x < width + 20:
        h = rnd.randint(55, 130)
        w = h * rnd.uniform(0.22, 0.3)
        b = height
        pts = [
            (x, b - h),
            (x + w * 0.45, b - h * 0.62), (x + w * 0.18, b - h * 0.62),
            (x + w * 0.75, b - h * 0.3), (x + w * 0.32, b - h * 0.3),
            (x + w, b), (x - w, b),
            (x - w * 0.32, b - h * 0.3), (x - w * 0.75, b - h * 0.3),
            (x - w * 0.18, b - h * 0.62), (x - w * 0.45, b - h * 0.62),
        ]
        polys.append("<polygon points='%s'/>" % " ".join("%.1f,%.1f" % p for p in pts))
        x += rnd.randint(18, 46)
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' fill='#020202'>%s</svg>"
            % (width, height, "".join(polys)))


def apply() -> None:
    """Inject the stylesheet. Call once, straight after st.set_page_config."""
    css = _cached_css()
    st.html("<style>" + css + "</style>")


def hero(title: str, tagline: str) -> None:
    """Centred blackletter logo with symmetrical rules either side."""
    st.markdown(
        '<div class="ctrlf-hero"><div class="ctrlf-logo">%s</div>'
        '<div class="ctrlf-tagline">%s</div></div>' % (html.escape(title), html.escape(tagline)),
        unsafe_allow_html=True,
    )


FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
FONT_FILES = {
    "UnifrakturMaguntia": "UnifrakturMaguntia-Book.ttf",
    "PirataOne": "PirataOne-Regular.ttf",
}

EXTRA_CSS = """
code { color: #9fb4c7 !important; background: #0d0d0d !important; }
"""


def _font_faces() -> str:
    """Embed the bundled fonts so the stylesheet needs no route and no request."""
    rules = []
    for family, filename in FONT_FILES.items():
        path = FONT_DIR / filename
        if not path.exists():
            continue  # a missing font falls back to serif instead of breaking the app
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            "@font-face { font-family: '" + family + "'; font-style: normal; font-weight: 400; "
            "font-display: block; src: url(data:font/ttf;base64," + data + ") format('truetype'); }"
        )
    return "".join(rules)


@functools.lru_cache(maxsize=1)
def _cached_css() -> str:
    """Built once per process: the fonts and the generated SVG never change between reruns."""
    return (_font_faces()
            + CSS.replace("__TREES__", _svg_uri(_treeline())).replace("__GRAIN__", _svg_uri(GRAIN_SVG))
            + EXTRA_CSS)
