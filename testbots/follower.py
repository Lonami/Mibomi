"""
This bot will follow the users who say "follow" in the chat.

Note that the bot does not bother with authentication, so only
offline servers will work. "stop" will prevent the bot from moving.
"""
import asyncio
import json
import sys

import mibomi


class Follower(mibomi.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._following = None

    async def on_chat_message(self, item):
        item = json.loads(item.data)['with']
        if item[1] == 'follow':
            fake_json = item[0]['hoverEvent']['value']['text']
            uuid = fake_json.split(',')[1].split(':')[1][1:-2]
            for ent in self.entities:
                if str(ent.uuid) == uuid:
                    self._following = ent.id
                    return
        elif item[1] == 'stop':
            self._following = None
            await self.look(1, -1, 1)

    async def game_loop(self, dt):
        if not self._following:
            return

        target = self.entities[self._following]
        sx, sy, sz = self.position
        tx, ty, tz = target.x, target.y, target.z
        dx, dy, dz = tx - sx, ty - sy, tz - sz
        dist = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
        if dist > 2:
            dx /= dist
            dy /= dist
            dz /= dist
            await self.walk(dx, dy, dz)
        else:
            await self.look(dx, dy, dz)


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    username = sys.argv[2] if len(sys.argv) > 2 else 'Mibomi'
    async with Follower(host) as client:
        await client.login(username)
        await client.run()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
