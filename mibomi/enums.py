import enum


class HandshakeState(enum.IntEnum):
    """
    Enumeration of possible values for handshake state.
    """
    STATUS = 1
    LOGIN = 2
