import hashlib
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key

from . import connection, enums, datarw, authenticator

PROTOCOL_V1_12_2 = 340


class Client(connection.Connection):
    def handshake(self, state: enums.HandshakeState):
        """
        Performs a handshake with the server.
        """
        data = datarw.DataRW()
        data.writevari32(PROTOCOL_V1_12_2)
        data.writestr(self.ip)
        data.writefmt('H', self.port)
        data.writevari32(state)
        self.send(0, data.getvalue())

    def login(self, username, access_token, profile_id):
        """
        Starts the login process with the server until its completion.
        """
        # Send the Login Start packet
        data = datarw.DataRW()
        data.writestr(username)
        self.send(0, data.getvalue())

        # Receive Encryption Request
        pid, data = self.recv()
        assert pid == 1
        server_id = data.readstr(str)
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
            assert authenticator.session_join(
                access_token, profile_id, server_hash)

        # Send the Encryption Request packet
        pk = load_der_public_key(pk, default_backend())
        encrypted_secret = pk.encrypt(shared_secret, PKCS1v15())
        token = pk.encrypt(verify_token, PKCS1v15())

        data = datarw.DataRW()
        data.writebytes(encrypted_secret)
        data.writebytes(token)
        self.send(1, data.getvalue())

        # Enable encryption on the socket level
        cipher = Cipher(
            algorithms.AES(shared_secret),
            modes.CFB8(shared_secret),
            backend=default_backend()
        )
        self._encrypt = cipher.encryptor().update
        self._decrypt = cipher.decryptor().update

        # Receive Login Success
        packet_id, data = self.recv()
        if packet_id == 3:
            self._compression = data.readvari32()
            if self._compression < 0:
                assert self._compression == -1
                self._compression = None

            # We may have received "enable compression first".
            # If that's the case, re-receive the actual login success.
            packet_id, data = self.recv()

        assert packet_id == 2
        player_uuid = data.readstr()
        player_name = data.readstr()
        return player_uuid, player_name

    def request(self):
        """
        Sends a (ping, empty) request to the server.
        """
        self.send(0, b'')
