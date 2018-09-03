import asyncio
import hashlib
import logging
import math
import os
import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key

from . import requester
from ..datatypes import types, enums, DataRW, Chunk, World, Entities
from ..mojang import authenticator
from ..utils import Timer

PROTOCOL_V1_12_2 = 340

_log = logging.getLogger(__name__)


class Client(requester.Requester):
    """
    This class is an abstraction over the connection
    and requester classes, and offers some basic methods
    such as logging in, preparing encryption, running in
    a loop to receive new items, and so on.

    You are encouraged to subclass this class when
    creating your own bot client.
    """
    def __init__(self, ip, port=25565, *, loop=None):
        super().__init__(ip, port, loop=loop)
        self.world = World()
        self.entities = Entities()
        self.position = None
        self._id_to_handler = {
            pid: getattr(self, 'on_' + cls.NAME)
            if hasattr(self, 'on_' + cls.NAME)
            else self.on_generic
            for pid, cls in types.TYPES.items()
        }

        self._running = False
        self._disconnect_timer = Timer(
            20, self.keep_alive_disconnect, loop=loop)

    async def handshake(self, state: enums.HandshakeState):
        """
        Performs a handshake with the server.
        """
        data = DataRW()
        data.writevari32(PROTOCOL_V1_12_2)
        data.writestr(self.ip)
        data.writefmt('H', self.port)
        data.writevari32(state)
        await self.send(0, data.getvalue())

    async def login(self, username, access_token, profile_id):
        """
        Starts the login process with the server until its completion.
        """
        # Send the Login Start packet
        data = DataRW()
        data.writestr(username)
        await self.send(0, data.getvalue())

        # Receive Encryption Request
        pid, data = await self.recv()
        if pid == 1:
            await self._setup_encryption(data, access_token, profile_id)
            pid, data = await self.recv()

        # Receive Login Success
        if pid == 3:
            self._compression = data.readvari32()
            if self._compression < 0:
                assert self._compression == -1
                self._compression = None

            # We may have received "enable compression first".
            # If that's the case, re-receive the actual login success.
            pid, data = await self.recv()

        assert pid == 2
        player_uuid = data.readstr()
        player_name = data.readstr()
        self._disconnect_timer.start()
        return player_uuid, player_name

    async def _setup_encryption(self, data, access_token, profile_id):
        server_id = data.readstr()
        pk_len = data.readvari32()
        pk = data.read(pk_len)
        vt_len = data.readvari32()
        verify_token = data.read(vt_len)

        # Generate a shared secret
        shared_secret = os.urandom(16)

        # If we're in online mode (not '-'), assert valid credentials
        if server_id != '-':  # '-' == offline mode
            # Calculate the SHA1 hash before using the authenticator
            sha = hashlib.sha1()
            sha.update(server_id.encode('ascii'))
            sha.update(shared_secret)
            sha.update(pk)

            # Minecraft uses signed hexadecimal digest
            server_hash = sha.digest()
            server_hash = int.from_bytes(server_hash, 'big', signed=True)
            server_hash = '{:x}'.format(server_hash)

            # Assert joining the session succeeds
            assert await authenticator.session_join(
                access_token, profile_id, server_hash)

        # Send the Encryption Request packet
        pk = load_der_public_key(pk, default_backend())
        encrypted_secret = pk.encrypt(shared_secret, PKCS1v15())
        token = pk.encrypt(verify_token, PKCS1v15())

        data = DataRW()
        data.writevari32(len(encrypted_secret))
        data.write(encrypted_secret)
        data.writevari32(len(token))
        data.write(token)
        await self.send(1, data.getvalue())

        # Enable encryption on the socket level
        cipher = Cipher(
            algorithms.AES(shared_secret),
            modes.CFB8(shared_secret),
            backend=default_backend()
        )
        self._encrypt = cipher.encryptor().update
        self._decrypt = cipher.decryptor().update

    async def run(self):
        try:
            self._running = True
            self._loop.create_task(self._game_loop())
            while True:
                pid, data = await self.recv()
                try:
                    if pid in types.TYPES:
                        await self._id_to_handler[pid](types.TYPES[pid](data))
                        left = data.read()
                        if left:
                            _log.warning('Missing data after %d %s', pid, left)
                    else:
                        await self.on_unknown(pid, data)
                except Exception as e:
                    _log.exception(
                        'Unhandled exception processing %s: %s', pid, e)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self.disconnect()

    async def walk(self, dx, dy, dz, scale=0.1):
        if not self.position:
            return

        x, y, z = self.position
        x += dx * scale
        z += dz * scale
        self.position = x, y, z

        yaw = -math.atan2(dx, dz) / math.pi * 180
        if yaw < 0:
            yaw = 360 + yaw

        r = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
        pitch = -math.asin(dy / r) / math.pi * 180
        await self.player_position_and_look(
            x, y, z, yaw, pitch, on_ground=True)

    async def on_unknown(self, pid, data):
        _log.debug('Unknown packet %x', pid)

    async def on_keep_alive(self, keep_alive: types.KeepAlive):
        # Keep Alive packet, must respond within 30 seconds
        self._disconnect_timer.reset()
        _log.debug('Responding to keep-alive')
        await self.keep_alive(keep_alive.id)
        await self.player(on_ground=True)  # Send periodically or get kicked

    async def on_player_abilities(self, player_ab: types.PlayerAbilities):
        # https://wiki.vg/Protocol_FAQ#What.27s_the_normal_login_sequence
        # _for_a_client.3F
        _log.debug('Responding to Player Abilities and Client Settings')
        await self.plugin_message('LW|Mibomi', b'')
        await self.client_settings(
            locale='en_GB',
            view_distance=8,
            chat_mode=0,
            chat_colors=False,
            displayed_skin_parts=0x3f,
            main_hand=1
        )

    async def on_player_position_and_look(
            self, pos: types.PlayerPositionAndLook):
        _log.debug('Received position (%.2f, %.2f, %.2f)', pos.x, pos.y, pos.z)
        await self.teleport_confirm(pos.teleport_id)

        await self.player_position_and_look(
            pos.x, pos.y, pos.z, pos.yaw, pos.pitch, on_ground=True)

        await self.client_status(action_id=0)
        self.position = pos.x, pos.y, pos.z
        # int() rounds towards zero, math.floor works for negative numbers
        x = math.floor(pos.x)
        y = math.floor(pos.y) - 1
        z = math.floor(pos.z)
        _log.debug('The block below us (%d, %d, %d) is %d',
                   x, y, z, self.world[x, y, z])

    async def on_disconnect(self, obj):
        _log.debug('Server disconnected us')
        self.disconnect()
        quit()  # TODO Don't quit

    async def on_generic(self, obj):
        """Callback to handle a generic Packet ID."""
        if not isinstance(obj, (types.TimeUpdate, types.ChunkData)):
            _log.debug('Received %s: %s', obj.NAME, obj)

    async def on_chunk_data(self, data: types.ChunkData):
        self.world.feed_chunk(Chunk(data))

    async def on_block_change(self, data: types.BlockChange):
        x, y, z = data.location
        self.world[x, y, z] = Chunk.get_block_id(data.id)

    async def on_multi_block_change(self, data: types.MultiBlockChange):
        c = self.world.get_chunk(data.chunk_x, data.chunk_z)
        for record in data.records:
            x = record.h_pos >> 4
            z = record.h_pos & 0xf
            c[x, record.y, z] = Chunk.get_block_id(record.block_id)

    async def on_spawn_player(self, data):
        self.entities.feed_player_spawn(data)

    async def on_entity_relative_move(self, data):
        self.entities.feed_relative_move(data)

    async def on_entity_look_and_relative_move(self, data):
        self.entities.feed_relative_move(data)

    async def on_entity_teleport(self, data):
        self.entities.feed_move(data)

    async def _game_loop(self):
        last = time.time()
        while self._running:
            now = time.time()
            try:
                await self.game_loop(now - last)
            except Exception as e:
                _log.exception('Unhandled game loop exception: %s', e)
            last = now
            await asyncio.sleep(0.015, loop=self._loop)

    async def game_loop(self, dt):
        pass

    async def request(self):
        """
        Sends a (ping, empty) request to the server.
        """
        await self.send(0, b'')

    async def keep_alive_disconnect(self):
        _log.info('Server did not send a keep-alive in time; disconnecting')
        self.disconnect()
