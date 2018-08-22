import socket
from . import datarw


class Connection:
    """
    This class is responsible for connecting to Minecraft servers,
    pack outgoing data as requests, and unpack incoming messages.
    """
    def __init__(self, ip, port=25565):
        self.sock = None
        self.ip = ip
        self.port = port

    def connect(self):
        """
        Stabilises a connection to the server.
        """
        self.sock = socket.socket()
        self.sock.connect((self.ip, self.port))

    def disconnect(self):
        """
        Cleanly disconnects from the server.
        """
        self.sock.close()

    def send(self, pid, data):
        """
        Sends a packet with the given Packet ID and payload binary data.
        """
        pid = datarw.DataRW.packvari(pid)
        length = datarw.DataRW.packvari(len(pid) + len(data))
        self.sock.sendall(length + pid + data)

    def recv(self):
        """
        Receives a packet from the network, returning ``(Packet ID, DataRW)``.
        """
        length = datarw.DataRW.unpackvari(lambda: self.sock.recv(1)[0])
        data = datarw.DataRW(self.read(length))
        return data.readvari32(), data

    def read(self, n):
        """
        Reads *exactly* `n` bytes from the network.
        """
        data = b''
        while len(data) != n:
            data += self.sock.recv(n - len(data))
        return data

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
