import asyncio
import time


class Timer:
    """
    Timer class that will fire a callback once its timeout is over.

    It supports cancellation and resetting the timeout to start
    counting again from the beginning (i.e. giving more time).
    """
    def __init__(self, timeout, callback, *, loop=None):
        self._timeout = timeout
        self.callback = callback
        self._loop = loop or asyncio.get_event_loop()
        self._due = None
        self._task = None
        self._cancel = asyncio.Event(loop=self._loop)

    def start(self):
        """
        Starts the timer. This is a no-op if it was already started.
        """
        if self._task is None:
            self._cancel.clear()
            self.reset()
            self._task = self._loop.create_task(self._checker())

    def reset(self):
        """
        Resets the timer, giving it more time before firing the timeout.
        """
        self._due = time.time() + self._timeout

    async def stop(self):
        """
        Stops the timer. The timeout callback will not be fired.
        """
        self._cancel.set()
        self._due = None
        await self._task
        self._task = None

    async def _checker(self):
        while not self._cancel.is_set():
            if time.time() >= self._due:
                await self.callback()
                await self.stop()
                break

            try:
                await asyncio.wait_for(
                    self._cancel.wait(),
                    self._due - time.time(),
                    loop=self._loop
                )
            except asyncio.TimeoutError:
                pass
