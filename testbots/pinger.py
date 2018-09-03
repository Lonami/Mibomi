"""
This bot just pings to localhost (or server from command line arguments).
"""
import asyncio
import json
import sys
import time

import mibomi


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    print('Pinging {}...'.format(host), end='', flush=True, file=sys.stderr)
    start = time.time()

    async with mibomi.Client(host) as client:
        pong = await client.ping()

    delta = time.time() - start
    print(' Done ({:.1f}ms).'.format(delta * 1000), file=sys.stderr)
    print(json.dumps(pong, indent=4))


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
