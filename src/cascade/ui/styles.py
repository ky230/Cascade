"""TCSS stylesheet for Cascade Textual TUI."""

CASCADE_TCSS = """
Screen {
    background: #0d1117;
    layout: vertical;
}

/* ── Banner (ASCII art) ── */

#banner {
    background: #0d1117;
    color: #5fd7ff;
    padding: 0 0;
    height: auto;
}

/* ── Status bar (model + path) ── */

#status-bar {
    height: auto;
    width: auto;
    background: #0d1117;
    color: #c9d1d9;
    padding: 0 1;
    margin: 1 1 0 1;
    border: round #555555;
}

#help-text {
    height: 1;
    background: #0d1117;
    color: #484f58;
    margin: 0 1 1 1;
}

/* ── Prompt Container ── */

#input-section {
    height: auto;
    padding-bottom: 0;
}

#prompt-container {
    height: auto;
    min-height: 1;
    width: 1fr;
    layout: horizontal;
    align: left middle;
    margin: 1 0 0 0;
    padding: 0 1;
    background: #1c2128;
    border-top: inner #1c2128;
    border-bottom: inner #1c2128;
    border-left: none;
    border-right: none;
    layers: base surface overlay;
}

#prompt-label {
    height: 1;
    width: 2;
    background: transparent;
    layer: surface;
}

#prompt-input {
    layer: surface;
    width: 1fr;
    background: transparent;
}

#prompt-input .text-area--cursor-line {
    background: transparent;
}

#prompt-placeholder {
    content-align: left middle;
    height: 1;
    color: #484f58;
    background: transparent;
    layer: overlay;
    position: absolute;
    offset: 2 0;
}

/* ── Chat history scroll container ── */

#chat-history {
    background: #0d1117;
    height: 1fr;
    scrollbar-background: #0d1117;
    scrollbar-color: #30363d;
    scrollbar-color-hover: #5fd7ff;
    scrollbar-color-active: #5fd7ff;
}

/* ── Message labels ── */

.ai-label {
    height: 1;
    background: #0d1117;
    color: #5fd7ff;
    padding: 0 1;
    margin-top: 1;
    text-style: bold;
}

.tool-label {
    height: 1;
    background: #0d1117;
    color: #ff8700;
    padding: 0 1;
    margin-top: 1;
}

/* ── Message TextAreas ── */

.message-area {
    background: #161b22;
    color: #c9d1d9;
    border: round #30363d;
    margin: 0 1;
    padding: 0 1;
    min-height: 3;
    height: auto;
    overflow: hidden hidden;
    scrollbar-size: 0 0;
}

.message-area:focus {
    border: round #5fd7ff;
}

.user-msg-box {
    width: auto;
    min-width: 10;
    max-width: 100%;
    height: auto;
    background: #0d1117;
    color: #c9d1d9;
    border: round #5fd7ff;
    border-title-color: #5fd7ff;
    padding: 0 1;
    margin: 0 1;
}

.ai-msg {
    border: round #484f58;
    background: #0d1117;
    margin: 0 1;
    padding: 0 1;
}

.tool-msg {
    border: round #ff8700;
}

.tool-msg-error {
    border: round #ff5f5f;
}

.system-msg {
    background: #0d1117;
    color: #484f58;
    border: none;
    margin: 0 1;
    min-height: 1;
    height: auto;
}

/* ── Spinner ── */

.spinner {
    height: 1;
    background: #0d1117;
    padding: 0 1;
    margin: 0 1;
}

/* ── Input ── */

#prompt-input {
    height: auto;
    max-height: 15;
    width: 1fr;
    background: transparent;
    padding: 0 0;
    margin: 0 0;
    border: none;
}

#prompt-input:focus {
    border: none;
}

PromptInput > .text-area--cursor-line {
    background: transparent;
}

Input {
    background: #0d1117;
    color: #c9d1d9;
    border: none;
    padding: 0 0;
    height: 1;
}

Input:focus {
    border: none;
}

/* ── Footer bar (model) ── */

#footer-bar {
    height: 1;
    dock: bottom;
    background: #161b22;
    color: #484f58;
    padding: 0 1;
}

/* ── Rich markup messages ── */

.rich-msg {
    background: #0d1117;
    color: #c9d1d9;
    padding: 0 1;
    margin: 0 1;
    height: auto;
}

/* ── Command palette items ── */

.palette-item {
    height: 1;
    background: transparent;
    padding: 0 1;
    margin: 0;
    width: 100%;
}

.palette-item.active {
    background: #5fd7ff;
}

/* ── Notifications / Toast ── */
Toast {
    width: auto;
    min-width: 20;
    max-width: 50;
    padding: 0 1;
    margin: 0 1 1 0;
    background: #161b22;
    color: #c9d1d9;
    border-left: tall #5fd7ff;
}

Toast.-information {
    border-left: tall #5fd7ff;
}

Toast > .toast--title {
    color: #5fd7ff;
    text-style: bold;
}
Toast.-information > .toast--title {
    color: #5fd7ff;
}
"""
