"""Running blocking work off the event loop."""

import asyncio
from collections.abc import Callable


async def io_bound[**P, R](
    callback: Callable[P, R], *args: P.args, **kwargs: P.kwargs
) -> R:
    """Run a blocking, value-returning callback in a worker thread.

    `nicegui.run.io_bound` returns `None` instead of the result when the call
    is cancelled or the app is shutting down, which would otherwise leave every
    caller unpacking a `None`. Raising instead keeps the result type honest;
    NiceGUI 4.0 is slated to raise `CancelledError` itself.

    Use `nicegui.run.io_bound` directly for callbacks that return nothing.
    """
    from nicegui import run

    result = await run.io_bound(callback, *args, **kwargs)
    if result is None:
        raise asyncio.CancelledError(
            f"{getattr(callback, '__name__', callback)} was cancelled"
        )
    return result
