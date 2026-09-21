"""Running blocking work off the event loop.

`nicegui.run.io_bound` returns `None` both when the callback returned nothing
and when the call was cancelled, which is ambiguous at the call site. These two
wrappers make the caller say which one they mean.
"""

import asyncio
from collections.abc import Callable


async def load[**P, R](
    callback: Callable[P, R], *args: P.args, **kwargs: P.kwargs
) -> R:
    """Compute a value in a worker thread.

    Raises `CancelledError` if NiceGUI cancelled the call (app shutting down or
    the client went away) rather than handing back a `None` the caller would
    have to unpack. NiceGUI 4.0 is slated to raise this itself.

    Only for callbacks that return something: a callback returning `None` is
    indistinguishable from cancellation here. Use `run_blocking` for those.
    """
    from nicegui import run

    result = await run.io_bound(callback, *args, **kwargs)
    if result is None:
        raise asyncio.CancelledError(
            f"{getattr(callback, '__name__', callback)} was cancelled"
        )
    return result


async def run_blocking[**P](
    callback: Callable[P, None], *args: P.args, **kwargs: P.kwargs
) -> None:
    """Run blocking work with no result in a worker thread."""
    from nicegui import run

    await run.io_bound(callback, *args, **kwargs)
