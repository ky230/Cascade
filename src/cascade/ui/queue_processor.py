"""Queue Processor for Cascade TUI.

Mirrors Claude Code's queueProcessor.ts — dequeue strategy:
  - Slash commands and bash: process individually (not batched)
  - Non-slash, same-mode commands: batch drain all at once
    → becomes multiple user messages in ONE API call
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from cascade.ui.message_queue import MessageQueueManager, QueuedCommand

logger = logging.getLogger(__name__)


def process_queue_if_ready(
    queue: MessageQueueManager,
    execute_input: Callable[[list[QueuedCommand]], Awaitable[None]],
) -> bool:
    """Process next command(s) from queue if any are available.

    Returns True if a command was dispatched, False if queue was empty.

    Strategy (mirrors Claude Code):
    1. Peek at next command
    2. If slash command → dequeue single, execute individually
    3. If non-slash → drain ALL same-mode non-slash commands, execute as batch
    """
    next_cmd = queue.peek()
    if next_cmd is None:
        return False

    # Slash commands: process individually (not batched)
    if queue.is_slash_command(next_cmd):
        cmd = queue.dequeue()
        if cmd:
            logger.debug("Queue processor: dispatching slash command '%s'", cmd.value[:50])
            asyncio.create_task(execute_input([cmd]))
        return True

    # Non-slash: drain all same-mode commands at once
    target_mode = next_cmd.mode
    commands = queue.dequeue_all_matching(
        lambda cmd: not queue.is_slash_command(cmd) and cmd.mode == target_mode
    )
    if not commands:
        return False

    logger.debug(
        "Queue processor: batch dispatching %d command(s), mode='%s'",
        len(commands),
        target_mode,
    )
    asyncio.create_task(execute_input(commands))
    return True
