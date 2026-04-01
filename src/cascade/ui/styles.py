"""TCSS stylesheet for Cascade Textual TUI."""

CASCADE_TCSS = """
Screen {
    background: #0d1117;
    layout: vertical;
}

/* ── Header ── */

#header-bar {
    height: 2;
    background: #161b22;
    color: #c9d1d9;
    padding: 0 1;
}

/* ── Chat history scroll container ── */

#chat-history {
    background: #0d1117;
}

/* ── Message labels ── */

.user-label {
    height: 1;
    background: #0d1117;
    color: #5fd7ff;
    padding: 0 1;
    margin-top: 1;
}

.ai-label {
    height: 1;
    background: #0d1117;
    color: #5fd7ff;
    padding: 0 1;
    margin-top: 1;
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
    max-height: 50;
    height: auto;
}

.message-area:focus {
    border: round #5fd7ff;
}

.user-msg {
    border: round #5fd7ff;
}

.ai-msg {
    border: round #30363d;
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
    dock: bottom;
    height: 3;
    background: #161b22;
    padding: 0 1;
}

Input {
    background: #21262d;
    color: #c9d1d9;
    border: tall #30363d;
}

Input:focus {
    border: tall #5fd7ff;
}

/* ── Footer ── */

Footer {
    background: #161b22;
}
"""
