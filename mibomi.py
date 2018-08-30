import logging
logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger(__name__)

import asyncio
import getpass
import json
import os
import pprint

import mibomi.akbhit
import mibomi.authenticator
import mibomi.client
import mibomi.enums

AUTH_DATA = 'auth.data'


async def main():
    if os.path.isfile(AUTH_DATA):
        with open(AUTH_DATA) as file:
            access_token = file.readline().rstrip()
            client_token = file.readline().rstrip()
            profile_id = file.readline().rstrip()
    else:
        response = await mibomi.authenticator.authenticate(
            input('Enter Mojang username (or email): '),
            getpass.getpass('Enter account password: ')
        )
        access_token = response.access_token
        client_token = response.client_token
        profile_id = response.selected_profile.id
        with open(AUTH_DATA, 'w') as f:
            f.write('\n'.join((
                access_token,
                client_token,
                profile_id
            )))

    print('The client token is', client_token)
    async with mibomi.client.Client('localhost') as client:
        await client.handshake(mibomi.enums.HandshakeState.STATUS)
        await client.request()

        packet_id, data = await client.recv()
        if packet_id == 0:
            packet = 'Response'
        else:
            packet = '?'

        print('Received packet ID: ', packet_id, ' (', packet, ')', sep='')
        print('JSON data:')
        pprint.pprint(json.loads(data.readstr()))

    loop = asyncio.get_event_loop()
    async with mibomi.client.Client('localhost') as client,\
            mibomi.akbhit.KBHit(loop) as kb:
        async def handle_key(key):
            key = key.lower()
            if key == 'w':
                await client.walk(+1, 0)
            elif key == 'a':
                await client.walk(0, -1)
            elif key == 's':
                await client.walk(-1, 0)
            elif key == 'd':
                await client.walk(0, +1)
            elif key == 'm':
                s = ''
                while True:
                    k = await kb.getch()
                    if k == '\n':
                        break
                    else:
                        s += k
                await client.chat_message(s)

        done = False
        async def loop_keys():
            while not done:
                try:
                    await handle_key(await kb.getch())
                except Exception:
                    _log.exception('Unhandled exception handling key')

        task = loop.create_task(loop_keys())

        # username = input('Enter player name: ')
        username = 'Memelord'
        print('Logging in...', end='', flush=True)
        await client.handshake(mibomi.enums.HandshakeState.LOGIN)
        await client.login(username, access_token, profile_id)
        print(' Done.')
        print('Running client...', end='', flush=True)
        await client.run()
        print(' Done.')
        done = True
        await task


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
