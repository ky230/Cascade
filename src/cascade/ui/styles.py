"""TCSS themes for Cascade Textual TUI.

Design reference:
- Gemini CLI theme-manager.ts (662 lines): ThemeManager singleton, 17 built-in themes
- Gemini CLI theme.ts (693 lines): ColorsTheme with semantic color tokens
- CMS Logo colors: blue #005EB8, gold #F5A623, red #D32F2F
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeColors:
    """Semantic color tokens for a Cascade theme."""
    name: str
    description: str
    bg_primary: str       # Main background
    bg_secondary: str     # Input area, footer, message boxes
    bg_tertiary: str      # Prompt container
    fg_primary: str       # Main text
    fg_secondary: str     # Placeholder, help text
    accent: str           # Brand color (banner, focus, scrollbar)
    border: str           # Borders, separators
    tool_color: str       # Tool call label
    error_color: str      # Error highlights
    msg_border: str       # Message area border


# ── Theme Definitions ──

THEME_DARK = ThemeColors(
    name="dark",
    description="Default dark (GitHub Dark)",
    bg_primary="#0d1117",
    bg_secondary="#161b22",
    bg_tertiary="#1c2128",
    fg_primary="#c9d1d9",
    fg_secondary="#484f58",
    accent="#5fd7ff",
    border="#30363d",
    tool_color="#ff8700",
    error_color="#ff5f5f",
    msg_border="#484f58",
)

THEME_LIGHT = ThemeColors(
    name="light",
    description="Clean light",
    bg_primary="#ffffff",
    bg_secondary="#f6f8fa",
    bg_tertiary="#eef1f5",
    fg_primary="#24292f",
    fg_secondary="#6e7781",
    accent="#0969da",
    border="#d0d7de",
    tool_color="#bf5700",
    error_color="#cf222e",
    msg_border="#afb8c1",
)

THEME_CMS = ThemeColors(
    name="cms",
    description="CMS experiment (blue & gold)",
    bg_primary="#0a1628",
    bg_secondary="#112240",
    bg_tertiary="#1a3358",
    fg_primary="#e2e8f0",
    fg_secondary="#7b8dad",
    accent="#005EB8",        # CMS blue
    border="#1e3a5f",
    tool_color="#F5A623",    # CMS gold
    error_color="#D32F2F",   # CMS red
    msg_border="#2a5082",
)


THEMES: dict[str, ThemeColors] = {
    "dark": THEME_DARK,
    "light": THEME_LIGHT,
    "cms": THEME_CMS,
}

DEFAULT_THEME = "dark"


def build_tcss(c: ThemeColors) -> str:
    """Generate Textual CSS string from a ThemeColors palette."""
    return f"""
Screen {{
    background: {c.bg_primary};
    layout: vertical;
}}

/* ── Banner (ASCII art) ── */

#banner {{
    background: {c.bg_primary};
    color: {c.accent};
    padding: 0 0;
    height: auto;
}}

/* ── Status bar (model + path) ── */

#status-bar {{
    height: auto;
    width: auto;
    background: {c.bg_primary};
    color: {c.fg_primary};
    padding: 0 1;
    margin: 1 1 0 1;
    border: round #555555;
}}

#help-text {{
    height: 1;
    background: {c.bg_primary};
    color: {c.fg_secondary};
    margin: 0 1 1 1;
}}

/* ── Prompt Container ── */

#input-section {{
    height: auto;
    padding-bottom: 0;
}}

#prompt-container {{
    height: auto;
    min-height: 1;
    width: 1fr;
    layout: horizontal;
    align: left middle;
    margin: 1 0 0 0;
    padding: 0 1;
    background: {c.bg_tertiary};
    border-top: inner {c.bg_tertiary};
    border-bottom: inner {c.bg_tertiary};
    border-left: none;
    border-right: none;
    layers: base surface overlay;
}}

#prompt-label {{
    height: 1;
    width: 2;
    background: transparent;
    layer: surface;
}}

#prompt-input {{
    layer: surface;
    width: 1fr;
    background: transparent;
}}

#prompt-input .text-area--cursor-line {{
    background: transparent;
}}

#prompt-placeholder {{
    content-align: left middle;
    height: 1;
    color: {c.fg_secondary};
    background: transparent;
    layer: overlay;
    position: absolute;
    offset: 2 0;
}}

/* ── Chat history scroll container ── */

#chat-history {{
    background: {c.bg_primary};
    height: 1fr;
    scrollbar-background: {c.bg_primary};
    scrollbar-color: {c.border};
    scrollbar-color-hover: {c.accent};
    scrollbar-color-active: {c.accent};
}}

/* ── Message labels ── */

.ai-label {{
    height: 1;
    background: {c.bg_primary};
    color: {c.accent};
    padding: 0 1;
    margin-top: 1;
    text-style: bold;
}}

.tool-label {{
    height: 1;
    background: {c.bg_primary};
    color: {c.tool_color};
    padding: 0 1;
    margin-top: 1;
}}

/* ── Message TextAreas ── */

.message-area {{
    background: {c.bg_secondary};
    color: {c.fg_primary};
    border: round {c.border};
    margin: 0 1;
    padding: 0 1;
    min-height: 3;
    height: auto;
    overflow: hidden hidden;
    scrollbar-size: 0 0;
}}

.message-area:focus {{
    border: round {c.accent};
}}

.user-msg-box {{
    width: auto;
    min-width: 10;
    max-width: 100%;
    height: auto;
    background: {c.bg_primary};
    color: {c.fg_primary};
    border: round {c.accent};
    border-title-color: {c.accent};
    padding: 0 1;
    margin: 0 1;
}}

.ai-msg {{
    border: round {c.msg_border};
    background: {c.bg_primary};
    margin: 0 1;
    padding: 0 1;
}}

.tool-msg {{
    border: round {c.tool_color};
}}

.tool-msg-error {{
    border: round {c.error_color};
}}

.system-msg {{
    background: {c.bg_primary};
    color: {c.fg_secondary};
    border: none;
    margin: 0 1;
    min-height: 1;
    height: auto;
}}

/* ── Spinner ── */

.spinner {{
    height: 1;
    background: {c.bg_primary};
    padding: 0 1;
    margin: 0 1;
}}

/* ── Input ── */

#prompt-input {{
    height: auto;
    max-height: 15;
    width: 1fr;
    background: transparent;
    padding: 0 0;
    margin: 0 0;
    border: none;
}}

#prompt-input:focus {{
    border: none;
}}

PromptInput > .text-area--cursor-line {{
    background: transparent;
}}

Input {{
    background: {c.bg_primary};
    color: {c.fg_primary};
    border: none;
    padding: 0 0;
    height: 1;
}}

Input:focus {{
    border: none;
}}

/* ── Footer bar (model) ── */

#footer-bar {{
    height: 1;
    dock: bottom;
    background: {c.bg_secondary};
    color: {c.fg_secondary};
    padding: 0 1;
}}

/* ── Rich markup messages ── */

.rich-msg {{
    background: {c.bg_primary};
    color: {c.fg_primary};
    padding: 0 1;
    margin: 0 1;
    height: auto;
}}

/* ── Command palette items ── */

.palette-item {{
    height: 1;
    background: transparent;
    padding: 0 1;
    margin: 0;
    width: 100%;
}}

.palette-item.active {{
    background: {c.accent};
}}

/* ── Notifications / Toast ── */
Toast {{
    width: auto;
    min-width: 20;
    max-width: 50;
    padding: 0 1;
    margin: 0 1 1 0;
    background: {c.bg_secondary};
    color: {c.fg_primary};
    border-left: tall {c.accent};
}}

Toast.-information {{
    border-left: tall {c.accent};
}}

Toast > .toast--title {{
    color: {c.accent};
    text-style: bold;
}}
Toast.-information > .toast--title {{
    color: {c.accent};
}}
"""


def get_tcss(theme_name: str | None = None) -> str:
    """Return TCSS string for the given theme name (default: dark)."""
    name = theme_name or DEFAULT_THEME
    colors = THEMES.get(name, THEMES[DEFAULT_THEME])
    return build_tcss(colors)


# Backward compat: existing code imports CASCADE_TCSS
CASCADE_TCSS = get_tcss("dark")


def hot_swap_css(app, new_css: str) -> None:
    """Replace Cascade's CSS at runtime without destroying framework defaults.

    Textual 8.x reads the App.CSS class variable only once at _start().
    After that, styling lives in app.stylesheet.source — a dict keyed by
    (file_path, class_var_name) tuples. Mutating type(app).CSS has no
    effect because reparse() reads from the source dict, not the class var.

    This function identifies the Cascade CSS entry in the source dict and
    replaces its CssSource tuple in-place, then reparses + refreshes.
    """
    import inspect

    read_from = (inspect.getfile(type(app)), f"{type(app).__name__}.CSS")
    old_val = app.stylesheet.source[read_from]
    CssSource = type(old_val)
    app.stylesheet.source[read_from] = CssSource(
        new_css, old_val.is_defaults, old_val.tie_breaker, old_val.scope
    )
    app.stylesheet.reparse()
    app.refresh_css()

