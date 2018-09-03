"""
This module contains basic definitions that
allow defining and deserialize entire chunk data.
"""
from . import datarw

CHUNK_HEIGHT = 256
SECTION_WIDTH = 16
SECTION_HEIGHT = 16


class _IndirectPalette:
    """
    Indirect block palette, which needs a mapping block -> real ID.
    """
    def __init__(self, bits_per_block):
        self.bits_per_block = bits_per_block
        self.state_ids = []

    def read(self, data):
        # NOTE: This changes in 1.13
        # The 4 low bits represent metadata, and the rest is the block ID.
        self.state_ids = [Chunk.get_block_id(data.readvari32())
                          for _ in range(data.readvari32())]

    def __getitem__(self, item):
        return self.state_ids[item]


class _DirectPalette:
    """
    Direct block palette, where sending an indirect palette would be costly.
    """
    def read(self, data):
        data.readvari32()  # stub

    def __getitem__(self, item):
        return item


def _get_palette(bits_per_block):
    """
    Retrieve the appropriated block palette based on the bits per block.
    """
    if bits_per_block > 8:
        return _DirectPalette()
    else:
        return _IndirectPalette(max(bits_per_block, 4))


class Chunk:
    """
    This class represents an entire chunk, with dimensions
    `BLOCK_WIDTH` x `BLOCK_HEIGHT` x `BLOCK_WIDTH`.

    Access should be dictionary-like through tuples,
    such as ``chunk[7, 64, 12]`` to retrieve the block
    at the position ``(7, 64, 129)``.

    In addition, it has its `x` and `y` positions, the
    `entities` in the chunk, all its `sections` and
    `biome_info`.
    """
    def __init__(self, chunk, over_world=True):
        data = datarw.DataRW(chunk.data)
        self.x = chunk.x
        self.z = chunk.z
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

        assert not data.read()

    @staticmethod
    def get_block_id(n):
        """
        Returns the block ID for the given compound ID.
        """
        # n & 0x0f  # metadata
        return n >> 4  # block_id

    def __getitem__(self, xyz):
        x, y, z = xyz
        yh, yl = divmod(y, 16)
        if self.sections[yh]:
            return self.sections[yh][x, yl, z]
        else:
            return 0

    def __setitem__(self, xyz, value):
        x, y, z = xyz
        yh, yl = divmod(y, 16)
        if self.sections[yh]:
            self.sections[yh][x, yl, z] = value
        else:
            raise NotImplementedError


class Section:
    """
    Represents a single section of a chunk. Its intended
    usage is access similar to how the chunk data is
    accessed.

    Sections have `light` and `sky_light` data.
    """
    def __init__(self, data, over_world):
        self._bits_per_block = data.read(1)[0]
        self._palette = _get_palette(self._bits_per_block)
        self._palette.read(data)

        block_ids = []
        length = data.readvari32()
        section_size = SECTION_HEIGHT * SECTION_WIDTH * SECTION_WIDTH
        assert (length * 64) // self._bits_per_block >= section_size

        # Note that the bits are read from *low to high* in chunks
        # of *long values*. For this reason we have an integer with
        # an amount of bits, and every time we need more bits, read
        # another long worth of bits.
        bits = 0  # How many bits do we have available...
        integer = 0  # ...in this integer?
        mask = (1 << self._bits_per_block) - 1
        for _ in range(section_size):
            if bits < self._bits_per_block:
                # It's VERY important that we read UNSIGNED.
                #
                # We want to work with the BITS and shift BITS alone;
                # shifting negative integers in Python, where the numbers
                # have no bounded size, produces strange results; this
                # took a few hours to debug and obviously fails "randomly".
                integer |= data.readfmt('Q')[0] << bits
                bits += 64
                length -= 1

            block_ids.append(self._palette[integer & mask])
            integer >>= self._bits_per_block
            bits -= self._bits_per_block

        # Assert that we have read exactly all the longs we needed
        assert length == 0

        self._blocks = block_ids
        self.light = LightData(data)
        if over_world:
            self.sky_light = LightData(data)
        else:
            self.sky_light = None

    def __getitem__(self, xyz):
        x, y, z = xyz
        return self._blocks[(y * SECTION_HEIGHT + z) * SECTION_WIDTH + x]

    def __setitem__(self, xyz, value):
        x, y, z = xyz
        self._blocks[(y * SECTION_HEIGHT + z) * SECTION_WIDTH + x] = value


class LightData:
    """
    Light data for a section.
    """
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
    """
    Biome information for a chunk.
    """
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
