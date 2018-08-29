import hashlib
import logging
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key

from . import connection, enums, datarw, authenticator

PROTOCOL_V1_12_2 = 340

_log = logging.getLogger(__name__)

class Client(connection.Connection):
    def __init__(self, ip, port=25565, *, loop=None):
        super().__init__(ip, port, loop=loop)
        self._position = None

    async def handshake(self, state: enums.HandshakeState):
        """
        Performs a handshake with the server.
        """
        data = datarw.DataRW()
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
        data = datarw.DataRW()
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

        data = datarw.DataRW()
        data.writebytes(encrypted_secret)
        data.writebytes(token)
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
            while True:
                pid, data = await self.recv()
                try:
                    await self.on_generic(pid, data)
                except Exception as e:
                    _log.exception(
                        'Unhandled exception processing %s: %s', pid, e)
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()

    async def player_position(self, dx, dy, dz):
        if not self._position:
            return

        x, y, z = self._position
        x += dx
        y += dy
        z += dz
        self._position = x, y, z
        data = datarw.DataRW()
        data.writefmt('ddd?', x, y, z, True)
        await self.send(0xd, data.getvalue())

    async def chat_message(self, message):
        data = datarw.DataRW()
        data.writestr(message)
        await self.send(0x2, data.getvalue())

    async def on_generic(self, pid, data):
        """Callback to handle a generic Packet ID."""
        if pid == 0x1f:
            # Keep Alive packet, must respond within 30 seconds
            # TODO We should disconnect if we don't receive these for 20s
            # The data to send is the same as the data we received (a long).
            _log.debug('Responding to keep-alive')
            await self.send(0x0b, data.read())
        elif pid == 0x2c:
            # https://wiki.vg/Protocol_FAQ#What
            # .27s_the_normal_login_sequence_for_a_client.3F
            _log.debug('Responding to Player Abilities and Client Settings')
            data = datarw.DataRW()
            data.writestr('LW|Mibomi')
            await self.send(0x9, data.getvalue())
            data = datarw.DataRW()
            data.writestr('en_GB')
            data.writefmt('B', 8)
            data.writevari32(0)
            data.writefmt('?B', False, 0x3f)
            data.writevari32(1)
            await self.send(0x4, data.getvalue())
        elif pid == 0x2f:
            x, y, z, yaw, pitch, flags = data.readfmt('dddffB')
            _log.debug('Received position (%.2f, %.2f, %.2f)', x, y, z)
            tp_id = data.readvari32()
            data = datarw.DataRW()
            data.writevari32(tp_id)
            await self.send(0x0, data.getvalue())  # Teleport confirm
            data = datarw.DataRW()
            data.writefmt('dddff?', x, y, z, yaw, pitch, True)
            await self.send(0xe, data.getvalue())  # Player position
            data = datarw.DataRW()
            data.writevari32(0)
            await self.send(0x3, data.getvalue())  # Client status -> Respawn
            self._position = x, y, z
        elif pid == 0x1a:
            _log.debug('Server disconnected us')
            self.disconnect()
            quit()
        else:
            _log.debug('Unknown packet %x', pid)

    async def request(self):
        """
        Sends a (ping, empty) request to the server.
        """
        await self.send(0, b'')
