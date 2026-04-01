"""Async animated spinner for API wait states."""
import sys
import asyncio
import time

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# Rich-compatible ANSI (no dependency on deleted colors.py)
_CYAN = "\033[36m"
_DIM = "\033[2m"
_RESET = "\033[0m"


class Spinner:
    """Async spinner that shows animated feedback during API calls."""

    def __init__(self, message: str = "Thinking"):
        self.message = message
        self._task: asyncio.Task | None = None
        self._start_time: float = 0

    def start(self):
        """Start the spinner animation."""
        self._start_time = time.perf_counter()
        self._task = asyncio.get_event_loop().create_task(self._animate())

    def stop(self) -> float:
        """Stop the spinner, clear the line, return elapsed seconds."""
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        return time.perf_counter() - self._start_time

    async def _animate(self):
        """Render spinner frames at ~80ms interval."""
        i = 0
        try:
            while True:
                frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
                elapsed = time.perf_counter() - self._start_time
                text = f"\r{_CYAN}{frame}{_RESET} {_DIM}{self.message}... ({elapsed:.1f}s){_RESET}"
                sys.stdout.write(text)
                sys.stdout.flush()
                i += 1
                await asyncio.sleep(0.08)
        except asyncio.CancelledError:
            pass
