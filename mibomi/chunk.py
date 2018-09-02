CHUNK_HEIGHT = 256
SECTION_WIDTH = 16
SECTION_HEIGHT = 16

from . import datarw


class IndirectPalette:
    def __init__(self, bits_per_block):
        self.bits_per_block = bits_per_block
        self.state_ids = []

    def read(self, data):
        # NOTE: This changes in 1.13
        # The 4 low bits represent metadata, and the rest is the block ID.
        self.state_ids = [data.readvari32() >> 4
                          for _ in range(data.readvari32())]

    def __getitem__(self, item):
        return self.state_ids[item]


class DirectPalette:
    def read(self, data):
        data.readvari32()  # stub

    def __getitem__(self, item):
        return item


def get_palette(bits_per_block):
    if bits_per_block <= 4:
        return IndirectPalette(4)
    elif bits_per_block <= 8:
        return IndirectPalette(bits_per_block)
    else:
        return DirectPalette()


class Chunk:
    def __init__(self, chunk, over_world=True):
        data = datarw.DataRW(chunk.data)
        self.x = chunk.x
        self.z = chunk.z
        self.bit_mask = chunk.bit_mask
        self.entities = chunk.block_entities
        self.sections = []
        for section_y in range(CHUNK_HEIGHT // SECTION_HEIGHT):
            if chunk.bit_mask & (1 << section_y):
                self.sections.append(Section(data, over_world))
            else:
                self.sections.append(None)

        if chunk.new_chunk:
            self.biome_info = BiomeInfo(data)
        else:
            self.biome_info = None


class Section:
    def __init__(self, data, over_world):
        self._bits_per_block = data.read(1)[0]
        self._palette = get_palette(self._bits_per_block)
        self._palette.read(data)
        # N longs in big-endian follow. Due to the endianness,
        # we can also read (N * 8) bytes to have a single array
        # of bytes and access its bits directly as required.
        #
        # This is a lot more space friendly, and since we don't
        # need to render the blocks, we don't care about some
        # extra processing needed to extract the actual blocks.
        length = data.readvari32() * 8
        self._data = data.read(length)
        assert len(self._data) == length
        # Cache the bits per block masking not to redo this on get item
        self._mask = (1 << self._bits_per_block) - 1
        self.light = LightData(data)
        if over_world:
            self.sky_light = LightData(data)
        else:
            self.sky_light = None

    def __getitem__(self, xyz):
        x, y, z = xyz
        # TODO Slicing bits like this is not tested well enough
        index = (y * SECTION_HEIGHT + z) * SECTION_WIDTH + x
        bit_index = self._bits_per_block * index
        start = bit_index >> 3
        end = (bit_index + self._bits_per_block - 1) >> 3
        result = int.from_bytes(self._data[start:end + 1], 'big')
        shift = (bit_index + self._bits_per_block) & 7
        if shift:
            shift = 8 - shift
        data = (result >> shift) & self._mask
        return self._palette[data]


class LightData:
    def __init__(self, data):
        length = SECTION_HEIGHT * SECTION_WIDTH * SECTION_WIDTH // 2
        self._data = bytearray(data.read(length))
        assert len(self._data) == length

    # TODO This requires more testing
    def __getitem__(self, xyz):
        x, y, z = xyz
        i = self._data[(y * SECTION_HEIGHT + z) * SECTION_WIDTH + x // 2]
        if x & 1:
            i >>= 4  # odd, use higher bits
        return i & 0x0f

    def __setitem__(self, xyz, value):
        x, y, z = xyz
        i = (y * SECTION_HEIGHT + z) * SECTION_WIDTH + x // 2
        j = self._data[i]
        if x & 1:
            j &= 0x0f
            j |= value << 4
        else:
            j &= 0xf0
            j |= value
        self._data[i] = j


class BiomeInfo:
    def __init__(self, data):
        length = SECTION_WIDTH * SECTION_WIDTH
        self._data = bytearray(data.read(length))
        assert len(self._data) == length

    # TODO This requires more testing
    def __getitem__(self, xz):
        x, z = xz
        return self._data[z * SECTION_WIDTH + x]

    def __setitem__(self, xz, value):
        x, z = xz
        self._data[z * SECTION_WIDTH + x] = value
