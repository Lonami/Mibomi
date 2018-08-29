# Heavily based off stackoverflow.com/a/22085679/4759433 but
# with a great amount of modifications to work under asyncio
# by Lonami Exo (https://lonamiwebs.github.io).
import asyncio
import os

if os.name == 'nt':
    import msvcrt

    class KBHit:
        def __init__(self, loop=None):
            self.loop = loop or asyncio.get_event_loop()

        async def getch(self):
            while not msvcrt.kbhit():
                await asyncio.sleep(0.01, loop=self.loop)

            return msvcrt.getch().decode('utf-8')

        def kbhit(self):
            return msvcrt.kbhit()

        def __enter__(self):
            return self

        async def __aenter__(self):
            return self.__enter__()

        def __exit__(self, *args):
            pass

        async def __aexit__(self, *args):
            return self.__exit__(*args)

else:
    import sys
    import termios
    import atexit
    from select import select

    class KBHit:
        def __init__(self, loop=None):
            self.loop = loop or asyncio.get_event_loop()
            self.fd = sys.stdin.fileno()
            self.ready = asyncio.Event(loop=self.loop)
            self.reading = False
            self.old_term = termios.tcgetattr(self.fd)
            self.new_term = self.old_term[:]
            self.new_term[3] = (
                self.new_term[3] & ~termios.ICANON & ~termios.ECHO)
            atexit.register(self.__exit__)

        async def getch(self):
            if not self.kbhit():
                self.ready.clear()
                await self.ready.wait()

            return sys.stdin.read(1)

        def kbhit(self):
            return bool(select([sys.stdin], [], [], 0)[0])

        def __enter__(self):
            if not self.reading:
                self.reading = True
                termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.new_term)
                self.loop.add_reader(self.fd, self.ready.set)

            return self

        async def __aenter__(self):
            return self.__enter__()

        def __exit__(self, *args):
            if self.reading:
                self.reading = False
                self.loop.remove_reader(self.fd)
                termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_term)

        async def __aexit__(self, *args):
            return self.__exit__(*args)
