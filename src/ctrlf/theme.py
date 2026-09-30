"""Visual themes, selectable at run time. The default is Evergreen.

Evergreen is the demo look: insurance-sector sober, statistical, environmentally
minded. Paper white on a faint graph-paper grid, deep ink text, forest-green
primary with navy as the second colour, tabular figures in KPI tiles, and a strip
of rising bars under the wordmark that shades from navy into green.

Black metal is the build-day look, kept as an option: monochrome and frostbitten,
blackletter logo, typewriter evidence quotes, a treeline and a pale moon behind
everything. Aesthetic only, with no occult or runic symbols: it is shown to a customer.

Streamlit reads its base theme (widget colours, fonts) from config, which is
process-wide. Switching sets those options and reruns, so the new theme reaches the
browser in the next run's session message. Two browsers on different themes would
each flip the process setting on their own reruns; fine for a single-presenter demo.
`.streamlit/config.toml` mirrors EVERGREEN so a cold start paints it straight away.

Fonts are bundled in assets/fonts and embedded as data URIs: a font CDN would be a
network call at run time, and Streamlit's static route answered font URLs with the
app's HTML page. Evergreen uses the system sans stack and needs no bundled font.
"""
from __future__ import annotations

import base64
import functools
import html
import random
from pathlib import Path
from urllib.parse import quote

import streamlit as st
from streamlit import config as st_config

GRAIN_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>"
    "<filter id='g'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' "
    "stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter>"
    "<rect width='240' height='240' filter='url(#g)' opacity='0.55'/></svg>"
)

BLACK_METAL_CSS = """
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


FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
FONT_FILES = {
    "UnifrakturMaguntia": "UnifrakturMaguntia-Book.ttf",
    "PirataOne": "PirataOne-Regular.ttf",
}

BLACK_METAL_EXTRA_CSS = """
code { color: #9fb4c7 !important; background: #0d0d0d !important; }
.ctrlf-strip, .ctrlf-kicker { display: none; }
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
def _black_metal_css() -> str:
    """Built once per process: the fonts and the generated SVG never change between reruns."""
    return (_font_faces()
            + BLACK_METAL_CSS.replace("__TREES__", _svg_uri(_treeline()))
            .replace("__GRAIN__", _svg_uri(GRAIN_SVG))
            + BLACK_METAL_EXTRA_CSS)


# --- Evergreen --------------------------------------------------------------

INK, FOREST, LEAF, NAVY = "#17312b", "#1d6b57", "#5a9e6f", "#24477a"

EVERGREEN_CSS = """
[data-testid="stApp"] {
  background-color: #f5f7f3;
  background-image:
    linear-gradient(rgba(29,107,87,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(29,107,87,0.05) 1px, transparent 1px),
    linear-gradient(rgba(29,107,87,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(29,107,87,0.025) 1px, transparent 1px);
  background-size: 120px 120px, 120px 120px, 24px 24px, 24px 24px;
  background-attachment: fixed;
}
[data-testid="stHeader"], [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: transparent !important;
}
[data-testid="stSidebar"] { border-right: 1px solid #d3ddd6; border-top: 6px solid __INK__; }

.ctrlf-hero { margin: 0 0 1.6rem; padding-bottom: 1.1rem; border-bottom: 1px solid #d3ddd6; }
.ctrlf-kicker {
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase;
  color: __FOREST__;
}
.ctrlf-logo {
  font-size: clamp(2.4rem, 4.6vw, 3.4rem); font-weight: 750; line-height: 1.05;
  letter-spacing: -0.02em; color: __INK__; margin-top: 0.15rem;
}
.ctrlf-logo::after { content: "."; color: __LEAF__; }
.ctrlf-tagline { margin-top: 0.35rem; font-size: 1.02rem; color: #4d6159; max-width: 46rem; }
.ctrlf-strip {
  height: 34px; margin-top: 1rem; max-width: 520px;
  background-image: __BARS__; background-repeat: no-repeat; background-size: 100% 100%;
}

h1, h2, h3, h4 { color: __INK__ !important; letter-spacing: -0.01em; }
h2, h3 { border-bottom: 2px solid __FOREST__; padding-bottom: 0.25rem; display: inline-block; }

div[role="radiogroup"] { gap: 0.45rem; }
div[role="radiogroup"] label {
  border: 1px solid #c9d6ce; border-radius: 999px; padding: 0.3rem 0.9rem;
  background: #ffffff; font-size: 0.86rem; transition: border-color .15s, background .15s;
}
div[role="radiogroup"] label:hover { border-color: __FOREST__; }
div[role="radiogroup"] label:has(input:checked) {
  background: #e3efe8; border-color: __FOREST__; color: __INK__; font-weight: 600;
}

[data-testid="stExpander"] details {
  border: 1px solid #d3ddd6 !important; border-left: 4px solid __FOREST__ !important;
  border-radius: 8px !important; background: #ffffff; box-shadow: 0 1px 2px rgba(23,49,43,0.06);
}
[data-testid="stExpander"] summary:hover { color: __FOREST__; }

[data-testid="stMarkdownContainer"] blockquote {
  background: #f1f6f2; border-left: 3px solid __LEAF__; color: #2a3d37;
  padding: 0.55rem 0.95rem; border-radius: 0 6px 6px 0; font-size: 0.93rem;
}

[data-testid="stMetric"] {
  background: #ffffff; border: 1px solid #d3ddd6; border-top: 3px solid __NAVY__;
  border-radius: 8px; padding: 0.7rem 0.9rem 0.6rem; margin-bottom: 0.55rem;
  box-shadow: 0 1px 2px rgba(23,49,43,0.05);
}
[data-testid="stMetricValue"] {
  font-size: 2rem; font-weight: 700; color: __INK__; font-variant-numeric: tabular-nums;
}
[data-testid="stMetricLabel"] p {
  text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.7rem; color: #5b6f67;
  font-weight: 600;
}

[data-testid="stAlertContainer"] { border-radius: 8px; border: 1px solid #d3ddd6; }

code { color: __NAVY__ !important; background: #e9eff5 !important; }
hr { border-color: #d3ddd6 !important; }
::selection { background: #cfe5d8; color: __INK__; }
[data-testid="stApp"] { font-variant-numeric: tabular-nums; }
"""

# Mirrored in .streamlit/config.toml, so a cold start paints Evergreen before any script runs.
EVERGREEN = {
    "theme.base": "light",
    "theme.primaryColor": FOREST,
    "theme.backgroundColor": "#f5f7f3",
    "theme.secondaryBackgroundColor": "#e8efea",
    "theme.textColor": INK,
    "theme.linkColor": NAVY,
    "theme.borderColor": "#c9d6ce",
    "theme.showWidgetBorder": True,
    "theme.baseRadius": "medium",
    "theme.font": "sans-serif",
    "theme.headingFont": "sans-serif",
    "theme.headingFontWeights": 700,
    "theme.codeFont": "monospace",
    "theme.sidebar.backgroundColor": "#eaf1ec",
    "theme.sidebar.secondaryBackgroundColor": "#ffffff",
}

BLACK_METAL = {
    "theme.base": "dark",
    "theme.primaryColor": "#e6e1d7",
    "theme.backgroundColor": "#050505",
    "theme.secondaryBackgroundColor": "#111111",
    "theme.textColor": "#d8d3c9",
    "theme.linkColor": "#9fb4c7",
    "theme.borderColor": "#262626",
    "theme.showWidgetBorder": True,
    "theme.baseRadius": "none",
    "theme.font": "sans-serif",
    # PirataOne is defined by an embedded @font-face above.
    "theme.headingFont": "PirataOne, serif",
    "theme.headingFontWeights": 400,
    "theme.codeFont": "'Courier New', monospace",
    "theme.sidebar.backgroundColor": "#000000",
    "theme.sidebar.secondaryBackgroundColor": "#0c0c0c",
}


def _bars(width: int = 520, height: int = 34, n: int = 52, seed: int = 11) -> str:
    """A rising histogram shading from navy into green: the statistics motif."""
    rnd = random.Random(seed)
    step = width / n
    rects = []
    for i in range(n):
        t = i / (n - 1)
        h = min(height, max(3.0, height * (0.18 + 0.72 * t ** 1.4 + rnd.uniform(-0.08, 0.1))))
        rgb = [int(a + (b - a) * t) for a, b in ((0x24, 0x5a), (0x47, 0x9e), (0x7a, 0x6f))]
        rects.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' rx='1' fill='#%02x%02x%02x'/>"
                     % (i * step, height - h, step * 0.62, h, *rgb))
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
            "viewBox='0 0 %d %d' preserveAspectRatio='none'>%s</svg>"
            % (width, height, width, height, "".join(rects)))


@functools.lru_cache(maxsize=1)
def _evergreen_css() -> str:
    css = EVERGREEN_CSS.replace("__BARS__", _svg_uri(_bars()))
    for token, value in (("__INK__", INK), ("__FOREST__", FOREST),
                         ("__LEAF__", LEAF), ("__NAVY__", NAVY)):
        css = css.replace(token, value)
    return css


# --- Selection --------------------------------------------------------------

THEMES = {
    "evergreen": ("Evergreen", EVERGREEN, _evergreen_css),
    "blackmetal": ("Black metal", BLACK_METAL, _black_metal_css),
}
DEFAULT = "evergreen"


def current() -> str:
    """The chosen theme, carried in the URL so a reload or a shared link keeps it."""
    name = st.query_params.get("theme", DEFAULT)
    return name if name in THEMES else DEFAULT


def apply() -> None:
    """Call once, straight after st.set_page_config.

    If the process-wide base theme is not the chosen one, set it and rerun: the
    browser only picks up base theme options at the start of a run.
    """
    _, options, css = THEMES[current()]
    stale = {k: v for k, v in options.items() if st_config.get_option(k) != v}
    if stale:
        for k, v in stale.items():
            st_config.set_option(k, v)
        st.rerun()
    st.html("<style>" + css() + "</style>")


def picker() -> None:
    """Theme selector for the sidebar. Changing it rewrites the URL and reruns."""
    names = list(THEMES)
    chosen = st.selectbox("Appearance", names, index=names.index(current()),
                          format_func=lambda n: THEMES[n][0])
    if chosen != current():
        st.query_params["theme"] = chosen
        st.rerun()


def hero(title: str, tagline: str, kicker: str = "") -> None:
    """Wordmark and tagline. Each theme styles or hides the kicker and the bar strip."""
    st.markdown(
        '<div class="ctrlf-hero"><div class="ctrlf-kicker">%s</div>'
        '<div class="ctrlf-logo">%s</div><div class="ctrlf-tagline">%s</div>'
        '<div class="ctrlf-strip"></div></div>'
        % (html.escape(kicker), html.escape(title), html.escape(tagline)),
        unsafe_allow_html=True,
    )
