import collections


class World:
    def __init__(self):
        self._chunks = collections.defaultdict(list)

    def feed_chunk(self, chunk):
        self._chunks[chunk.x, chunk.z] = chunk

    def __getitem__(self, xyz):
        x, y, z = xyz
        chunk = self._chunks.get((x // 16, z // 16))
        if not chunk or not chunk.sections[y // 16]:
            return 0

        return chunk.sections[y // 16][(x % 16, y % 16, z % 16)]
