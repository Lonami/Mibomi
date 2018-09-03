"""
This module contains basic definitions that
allow defining and deserialize entire chunk data.
"""
from . import datarw

CHUNK_HEIGHT = 256
SECTION_WIDTH = 16
SECTION_HEIGHT = 16
SECTION_SIZE = SECTION_WIDTH * SECTION_HEIGHT * SECTION_WIDTH


def _get_palette_map(data, bits_per_block):
    """
    Retrieve the appropriated block palette based on the bits per block
    as a mapping function ``f(palette index) -> block index``.
    """
    if bits_per_block > 8:
        data.readvari32()  # Direct palette stub
        return lambda x: x
    else:
        # Indirect palette is a vari32 and N vari32 block IDs
        # TODO This will change in 1.13.
        return [Chunk.get_block_id(data.readvari32())
                for _ in range(data.readvari32())].__getitem__


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
        bpb = data.read(1)[0]  # bits per block
        palette = _get_palette_map(data, bpb)

        length = data.readvari32()
        assert (length * 64) // bpb >= SECTION_SIZE
        # It's VERY important that we read UNSIGNED.
        #
        # We want to work with the BITS and shift BITS alone;
        # shifting negative integers in Python, where the numbers
        # have no bounded size, produces strange results; this
        # took a few hours to debug and obviously fails "randomly".
        #
        # Note that the bits are read from *low to high* in chunks
        # of *long values*. For this reason we have an integer with
        # an amount of bits, and every time we need more bits, read
        # another long worth of bits.
        #
        # This is a very tight loop, and iter() + next() seems to
        # play best, as well as avoiding .append() calls, pre-allocating
        # enough block IDs, a simple mapping function for the palette.
        bits = 0
        integer = 0
        mask = (1 << bpb) - 1
        block_ids = [0] * SECTION_SIZE
        longs = iter(data.readfmt('Q' * length))
        for i in range(SECTION_SIZE):
            if bits < bpb:
                integer |= next(longs) << bits
                bits += 64

            block_ids[i] = palette(integer & mask)
            integer >>= bpb
            bits -= bpb

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


"""
A way to access palette indices straight from the array of longs:

def get_index(xyz):
    x, y, z = xyz
    bpb = self._bits_per_block
    # We want the i'th block at the right bit index.
    # Each long is 64 bits; return long index + offset.
    i, o = divmod(
        bpb * ((y * SECTION_HEIGHT + z) * SECTION_WIDTH + x),
        64
    )
    # Retrieve the correct long Result and shift it by Offset
    r = self._longs[i] >> o
    if o + bpb > 64:
        # We have some Missing bits from the next long
        m = (o + bpb) - 64
        m = self._longs[i + 1] & ((1 << m) - 1)
        r |= m << (bpb - o)

    return self._palette[r & self._mask]

The problem with this approach is that, when a block needs to
be updated ((over)written), it would need to be looked up in
the palette, which may or may not have the block and may or
may not need resizing, so it's only suitable for reading.
"""


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
