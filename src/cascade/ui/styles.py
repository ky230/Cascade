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
    padding-bottom: 8;
}

#prompt-container {
    height: 1;
    layout: horizontal;
    margin: 1 0 0 1;
}

#prompt-label {
    height: 1;
    width: 2;
    background: #0d1117;
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
    max-height: 3;
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
    height: 1;
    width: 1fr;
    background: #0d1117;
    padding: 0 0;
    margin: 0 0;
    border: none;
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
    background: #1a1a2e;
    padding: 0 0;
    margin: 0 0;
}

/* ── Modal Screens ── */
ModelPickerScreen {
    align: center middle;
    background: rgba(13, 17, 23, 0.8);
}

#model-picker-container {
    width: 90%;
    height: 80%;
    background: #161b22;
    border: solid #5fd7ff;
    padding: 1 2;
}

#model-picker-header {
    height: 3;
    margin-bottom: 1;
}

#model-list {
    height: 1fr;
    background: #0d1117;
    border: solid #30363d;
}

#model-picker-footer {
    height: 1;
    margin-top: 1;
    text-align: center;
}
"""
