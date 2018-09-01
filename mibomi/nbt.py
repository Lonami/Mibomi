import io
import struct


class BaseTag:
    __slots__ = ('name', 'value')

    def __init__(self, name, value):
        self.name = name or None
        self.value = value

    @classmethod
    def read(cls, stream, named=True):
        return TAGS[stream.read(1)[0]].read(stream, named)

    @staticmethod
    def _read_str(stream):
        return stream.read(
            struct.unpack('>h', stream.read(2))[0]).decode('utf-8')

    def __str__(self):
        if isinstance(self.value, list):
            return '{}({!r}, [{}])'.format(
                self.__class__.__name__, self.name,
                ', '.join(str(x) for x in self.value))
        else:
            return '{}({!r}, {!r})'.format(
                self.__class__.__name__, self.name, self.value)

    def __eq__(self, other):
        return other is self or (
            isinstance(other, self.__class__)
            and other.name == self.name
            and other.value == self.value
        )


class TagEnd(BaseTag):
    __slots__ = ()

    @classmethod
    def read(cls, stream, named=True):
        return cls(None, None)

    def __str__(self):
        return 'TagEnd()'


class TagByte(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>b', stream.read(1))[0])


class TagShort(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>h', stream.read(2))[0])


class TagInt(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>i', stream.read(4))[0])


class TagLong(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>q', stream.read(8))[0])


class TagFloat(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>f', stream.read(4))[0])


class TagDouble(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>d', stream.read(8))[0])


class TagByteArray(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   stream.read(struct.unpack('>i', stream.read(4))[0]))


class TagString(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   cls._read_str(stream))


class TagList(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        name = named and cls._read_str(stream)
        tag_cls = TAGS[stream.read(1)[0]]
        return cls(name, [
            tag_cls.read(stream, False) for _ in
            range(struct.unpack('>i', stream.read(4))[0])
        ])

    def __getitem__(self, item):
        return self.value.__getitem__(item)

    def __iter__(self):
        return self.value.__iter__()


class TagCompound(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        name = named and cls._read_str(stream)
        value = []
        while True:
            item = BaseTag.read(stream, True)
            if isinstance(item, TagEnd):
                break
            value.append(item)

        return cls(name, value)

    def __getattr__(self, item):
        try:
            return next(x for x in self.value if x.name == item)
        except StopIteration:
            return super().__getattribute__(item)


class TagIntArray(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        name = named and cls._read_str(stream)
        length = struct.unpack('>i', stream.read(4))[0]
        return cls(name, struct.unpack('>' + 'i' * length, length * 4))


class TagLongArray(BaseTag):
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        name = named and cls._read_str(stream)
        length = struct.unpack('>i', stream.read(4))[0]
        return cls(name, struct.unpack('>' + 'q' * length, length * 8))


TAGS = (
    TagEnd,
    TagByte,
    TagShort,
    TagInt,
    TagLong,
    TagFloat,
    TagDouble,
    TagByteArray,
    TagString,
    TagList,
    TagCompound,
    TagIntArray,
    TagLongArray
)


def read(data):
    if not isinstance(data, io.IOBase):
        if isinstance(data, (bytes, bytearray)):
            data = io.BytesIO(data)
        else:
            with open(data, 'rb') as f:
                return BaseTag.read(f)

    return BaseTag.read(data)
