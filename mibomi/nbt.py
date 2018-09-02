import io
import struct


class BaseTag:
    ID = b'\x00'
    __slots__ = ('name', 'value')

    def __init__(self, name, value):
        self.name = name or None
        self.value = value

    @classmethod
    def read(cls, stream, named=True):
        return TAGS[stream.read(1)[0]].read(stream, named)

    def write(self, stream):
        if self.name is not None:
            stream.write(self.__class__.ID)
            self._write_str(stream, self.name)

    @staticmethod
    def _read_str(stream):
        return stream.read(
            struct.unpack('>h', stream.read(2))[0]).decode('utf-8')

    @staticmethod
    def _write_str(stream, name):
        name = name.encode('utf-8')
        stream.write(struct.pack('>h', len(name)))
        stream.write(name)

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
    ID = b'\x00'
    __slots__ = ()

    @classmethod
    def read(cls, stream, named=True):
        return cls(None, None)

    def write(self, stream):
        stream.write(b'\0')

    def __str__(self):
        return 'TagEnd()'


class TagByte(BaseTag):
    ID = b'\x01'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>b', stream.read(1))[0])

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack('>b', self.value))


class TagShort(BaseTag):
    ID = b'\x02'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>h', stream.read(2))[0])

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack('>h', self.value))


class TagInt(BaseTag):
    ID = b'\x03'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>i', stream.read(4))[0])

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack('>i', self.value))


class TagLong(BaseTag):
    ID = b'\x04'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>q', stream.read(8))[0])

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack('>q', self.value))


class TagFloat(BaseTag):
    ID = b'\x05'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>f', stream.read(4))[0])

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack('>f', self.value))


class TagDouble(BaseTag):
    ID = b'\x06'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   struct.unpack('>d', stream.read(8))[0])

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack('>d', self.value))


class TagByteArray(BaseTag):
    ID = b'\x07'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   stream.read(struct.unpack('>i', stream.read(4))[0]))

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack('>i', len(self.value)))
        stream.write(self.value)


class TagString(BaseTag):
    ID = b'\x08'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        return cls(named and cls._read_str(stream),
                   cls._read_str(stream))

    def write(self, stream):
        super().write(stream)
        self._write_str(stream, self.value)


class TagList(BaseTag):
    ID = b'\x09'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        name = named and cls._read_str(stream)
        tag_cls = TAGS[stream.read(1)[0]]
        return cls(name, [
            tag_cls.read(stream, False) for _ in
            range(struct.unpack('>i', stream.read(4))[0])
        ])

    def write(self, stream):
        super().write(stream)
        if not self.value:
            stream.write(b'\0\0\0\0\0')
        else:
            stream.write(struct.pack(
                '>Bi', TAGS.index(self.value[0].__class__), len(self.value)))
            for item in self.value:
                item.write(stream)

    def __getitem__(self, item):
        return self.value.__getitem__(item)

    def __iter__(self):
        return self.value.__iter__()


class TagCompound(BaseTag):
    ID = b'\x0a'
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

    def write(self, stream):
        super().write(stream)
        for tag in self.value:
            tag.write(stream)
        TagEnd(None, None).write(stream)

    def __getattr__(self, item):
        try:
            return next(x for x in self.value if x.name == item)
        except StopIteration:
            return super().__getattribute__(item)


class TagIntArray(BaseTag):
    ID = b'\x0b'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        name = named and cls._read_str(stream)
        length = struct.unpack('>i', stream.read(4))[0]
        return cls(name, struct.unpack('>' + 'i' * length, length * 4))

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack(
            '>i' + 'i' * len(self.value), len(self.value), *self.value))


class TagLongArray(BaseTag):
    ID = b'\x0c'
    __slots__ = ('name', 'value')

    @classmethod
    def read(cls, stream, named=True):
        name = named and cls._read_str(stream)
        length = struct.unpack('>i', stream.read(4))[0]
        return cls(name, struct.unpack('>' + 'q' * length, length * 8))

    def write(self, stream):
        super().write(stream)
        stream.write(struct.pack(
            '>i' + 'q' * len(self.value), len(self.value), *self.value))


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


def write(data):
    stream = io.BytesIO()
    data.write(stream)
    return stream.getvalue()
