from . import connection, enums, datarw

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

    def login_start(self, username):
        """
        Starts the login process with the server.
        """
        data = datarw.DataRW()
        data.writestr(username)
        self.send(0, data.getvalue())

    def request(self):
        """
        Sends a (ping, empty) request to the server.
        """
        self.send(0, b'')
