import pytest
import asyncio
from cascade.ui.spinner import Spinner


@pytest.mark.asyncio
async def test_spinner_lifecycle():
    spinner = Spinner(message="Thinking")

    # Start spinner
    spinner.start()
    assert spinner._task is not None

    # Let it run briefly
    await asyncio.sleep(0.15)

    # Stop and get elapsed time
    elapsed = spinner.stop()
    assert elapsed > 0.1
    assert spinner._task is None or spinner._task.done()
