import io
import struct


# https://docs.python.org/3/library/struct.html#format-characters
# noinspection SpellCheckingInspection
import uuid


class DataRW(io.BytesIO):
    """
    Fast Data Read-Writer to serialize and deserialize binary data.
    """
    def readfmt(self, fmt):
        """
        Reads a tuple with the given format.
        """
        s = struct.Struct('>' + fmt)
        return s.unpack(self.read(s.size))

    def writefmt(self, fmt, *values):
        """
        Writes the given values with the given format.
        """
        self.write(struct.pack('>' + fmt, *values))

    def readstr(self):
        """
        Reads a text string of data.
        """
        return self.read(self.readvari32()).decode('utf-8')

    def readbytes(self):
        """
        Reads a byte string of data.
        """
        return self.read(self.readvari32())

    def writestr(self, value):
        """
        Writes the given text string of data.
        """
        value = value.encode('utf-8')
        self.writevari32(len(value))
        self.writebytes(value)

    def writebytes(self, value):
        """
        Writes the given byte string of data.
        """
        self.write(value)

    def readvari32(self):
        """
        Reads a variable-length integer of, at most, 32 bits.
        """
        return self.unpackvari(lambda: self.read(1)[0], 32)

    def readvari64(self):
        """
        Reads a variable-length integer of, at most, 64 bits.
        """
        return self.unpackvari(lambda: self.read(1)[0], 64)

    @staticmethod
    def unpackvari(read1, bits=32):
        """
        Unpacks a variable-length integer with at most the given bits.

        `read1` should be a function returning an integer bit every
        time it is called without parameters.
        """
        it = 0
        acc = 0
        count, u, p = (5, 'i', 'I')  if bits == 32 else (10, 'q', 'Q')
        while it != count:
            n = read1()
            acc |= (n & 0x7f) << (7 * it)
            if not (n & 0x80):
                return struct.unpack(u, struct.pack(p, acc))[0]
            it += 1
        raise ValueError('variable length integer is too long')

    @staticmethod
    async def aunpackvari(read1, bits=32):
        """
        Async version of `unpackvari`.
        """
        it = 0
        acc = 0
        count, u, p = (5, 'i', 'I')  if bits == 32 else (10, 'q', 'Q')
        while it != count:
            n = await read1()
            acc |= (n & 0x7f) << (7 * it)
            if not (n & 0x80):
                return struct.unpack(u, struct.pack(p, acc))[0]
            it += 1
        raise ValueError('variable length integer is too long')

    def writevari32(self, value):
        """
        Writes a variable-length integer of at most 32 bits.
        """
        self.write(self.packvari(value, 32))

    def writevari64(self, value):
        """
        Writes a variable-length integer of at most 64 bits.
        """
        self.write(self.packvari(value, 64))

    @staticmethod
    def packvari(value, bits=32):
        """
        Pack a variable-length integer with at most the given bits.
        """
        if not value:
            return b'\x00'

        result = []
        u, p = 'Ii' if bits == 32 else 'Qq'
        value = struct.unpack(u, struct.pack(p, value))[0]
        while value:
            byte = value & 0x7f
            value >>= 7
            if value:
                byte |= 0x80
            result.append(byte)
        return bytes(result)

    def readpos(self):
        """
        Reads a position, and returns a tuple of ``(x, y, z)``.
        """
        (value,) = self.readfmt('Q')
        x = (value >> 38) & 0x3ffffff
        y = (value >> 26) & 0xfff
        z = (value >>  0) & 0x3ffffff
        if x >= (1 << 25):
            x -= 1 << 26
        if y >= (1 << 11):
            y -= 1 << 12
        if z >= (1 << 25):
            z -= 1 << 26
        return x, y, z

    def writepos(self, x, y, z):
        """
        Writes a position.
        """
        x, y, z = struct.unpack('III', struct.pack('iii', x, y, z))
        self.writefmt('Q', (
            ((x & 0x3ffffff) << 38) |
            ((y & 0xfff)     << 26) |
            ((z & 0x3ffffff) << 0)
        ))

    def readangle(self):
        return self.read(1)[0]

    def writeangle(self, value):
        self.write(bytes([value]))

    def readuuid(self):
        return uuid.UUID(self.read(16))

    def writeuuid(self, value):
        self.write(value.bytes)

    def readleft(self):
        return self.read()

    def writeleft(self, value):
        self.write(value)
