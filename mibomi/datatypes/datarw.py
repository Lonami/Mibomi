import io
import struct
import uuid


from .basic import Position, Rotation, Slot
from . import nbt


# https://docs.python.org/3/library/struct.html#format-characters
# noinspection SpellCheckingInspection
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
        Reads the remaining byte string of data.
        """
        return self.read()

    def writestr(self, value):
        """
        Writes the given text string of data.
        """
        value = value.encode('utf-8')
        self.writevari32(len(value))
        self.write(value)

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
        return Position(x, y, z)

    def writepos(self, xyz):
        """
        Writes a position.
        """
        x, y, z = struct.unpack('III', struct.pack('iii', *xyz))
        self.writefmt('Q', (
            ((x & 0x3ffffff) << 38) |
            ((y & 0xfff)     << 26) |
            ((z & 0x3ffffff) << 0)
        ))

    def readuuid(self):
        return uuid.UUID(bytes=self.read(16))

    def writeuuid(self, value):
        self.write(value.bytes)

    def readleft(self):
        return self.read()

    def writeleft(self, value):
        self.write(value)

    def readentmeta(self):
        result = []
        while True:
            index = self.read(1)[0]
            if index == 0xff:
                return result
            cls = self.readvari32()
            if cls == 0:
                value = self.read(1)[0]
            elif cls == 1:
                value = self.readvari32()
            elif cls == 2:
                (value,) = self.readfmt('f')
            elif cls == 3:
                value = self.readstr()
            elif cls == 4:
                value = self.readstr()  # Chat
            elif cls == 5:
                value = self.readslot()
            elif cls == 6:
                (value,) = self.readfmt('?')
            elif cls == 7:
                value = Rotation(*self.readfmt('fff'))
            elif cls == 8:
                value = self.readpos()
            elif cls == 9:
                value = self.readpos() if self.readfmt('?')[0] else None
            elif cls == 10:
                value = self.readvari32()  # Direction
            elif cls == 11:
                value = self.readuuid() if self.readfmt('?')[0] else None
            elif cls == 12:
                value = self.readvari32() if self.readfmt('?')[0] else None
            elif cls == 13:
                value = self.readnbt()
            else:
                raise ValueError('invalid entmeta type {}'.format(cls))
            result.append((index, value))

    def writeentmeta(self, value):
        raise NotImplementedError

    def readnbt(self):
        return nbt.read(self)

    def writenbt(self, value):
        value.write(self)

    def readslot(self):
        (block_id,) = self.readfmt('h')
        if block_id == -1:
            return

        count, dmg = self.readfmt('bh')
        return Slot(block_id, count, dmg, self.readnbt())

    def writeslot(self, value):
        if not value:
            self.writefmt('h', -1)
            return

        block_id, count, dmg, nbt = value
        self.writefmt('hbh', block_id, count, dmg)
        self.writenbt(value)
