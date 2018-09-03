import collections


class World:
    """
    Represents an entire world. Access should be dictionary-like
    through (x, y, z) tuples, such as ``world[149, 64, -13]``.
    """
    def __init__(self):
        self._chunks = collections.defaultdict(list)

    def feed_chunk(self, chunk):
        self._chunks[chunk.x, chunk.z] = chunk

    def __getitem__(self, xyz):
        x, y, z = xyz
        xh, xl = divmod(x, 16)
        zh, zl = divmod(z, 16)
        chunk = self._chunks.get((xh, zh))
        if chunk:
            return chunk[xl, y, zl]
        else:
            return 0

    def __setitem__(self, xyz, value):
        x, y, z = xyz
        xh, xl = divmod(x, 16)
        zh, zl = divmod(z, 16)
        chunk = self._chunks.get((xh, zh))
        if chunk:
            chunk[xl, y, zl] = value
        else:
            raise NotImplementedError

    def get_chunk(self, x, z):
        """
        Returns the chunk at the given position, if known.
        """
        return self._chunks[x, z]
