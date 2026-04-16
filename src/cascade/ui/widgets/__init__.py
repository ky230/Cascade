# Cascade UI widgets sub-package
#
# Original widgets lived in a sibling widgets.py. That file has been moved
# to widgets/_core.py to avoid the package-shadows-module collision.
# All public symbols are re-exported here so existing imports keep working.

from cascade.ui.widgets._core import (  # noqa: F401
    CopyableStatic,
    CopyableTextArea,
    PromptInput,
    SpinnerWidget,
)
from cascade.ui.widgets.queue_preview import QueuePreview  # noqa: F401

__all__ = [
    "CopyableStatic",
    "CopyableTextArea",
    "PromptInput",
    "SpinnerWidget",
    "QueuePreview",
]
