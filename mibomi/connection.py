import asyncio
import socket
import zlib

from . import datarw


class Connection:
    """
    This class is responsible for connecting to Minecraft servers,
    pack outgoing data as requests, and unpack incoming messages.
    """
    def __init__(self, ip, port=25565, *, loop=None):
        self.sock = None
        self.ip = ip
        self.port = port
        self._loop = loop or asyncio.get_event_loop()
        self._rlock = asyncio.Lock(loop=self._loop)
        self._compression = None
        self._decrypt = lambda x: x
        self._encrypt = lambda x: x

    async def connect(self):
        """
        Stabilises a connection to the server.
        """
        self.sock = socket.socket()
        self.sock.setblocking(False)
        await self._loop.sock_connect(self.sock, (self.ip, self.port))

    def disconnect(self):
        """
        Cleanly disconnects from the server.
        """
        self.sock.close()

    async def send(self, pid, data):
        """
        Sends a packet with the given Packet ID and payload binary data.
        """
        # For both modes, the data length that counts is Packet ID and Data
        data = datarw.DataRW.packvari(pid) + data
        if self._compression is not None:
            # If compression is enabled, compress unless below threshold, in
            # which case the inner data length should be 0 (not compressed).
            if len(data) < self._compression:
                data_length = 0
            else:
                data_length = len(data)
                data = zlib.compress(data)

            data = datarw.DataRW.packvari(data_length) + data

        data = datarw.DataRW.packvari(len(data)) + data
        await self._loop.sock_sendall(self.sock, data)

    async def recv(self):
        """
        Receives a packet from the network, returning ``(Packet ID, DataRW)``.
        """
        async with self._rlock:
            length = await datarw.DataRW.aunpackvari(self._recv1)
            data = datarw.DataRW(await self.read(length))

        if self._compression is not None:
            data_length = data.readvari32()
            if data_length:
                assert data_length >= self._compression
                data = zlib.decompress(data.read())
                assert len(data) == data_length
                data = datarw.DataRW(data)

        return data.readvari32(), data

    async def _recv1(self):
        return self._decrypt(await self._loop.sock_recv(self.sock, 1))[0]

    async def read(self, n):
        """
        Reads *exactly* `n` bytes from the network.
        """
        data = b''
        while len(data) != n:
            data += await self._loop.sock_recv(self.sock, n - len(data))
        return self._decrypt(data)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        self.disconnect()
