class Entities:
    def __init__(self):
        self._entities = {}

    def feed_player_spawn(self, item):
        self._entities[item.id] = item

    def feed_move(self, item):
        player = self._entities[item.id]
        player.x = item.x
        player.y = item.y
        player.z = item.z

    def feed_relative_move(self, item):
        player = self._entities[item.id]
        player.x += item.dx / (128 * 32)
        player.y += item.dy / (128 * 32)
        player.z += item.dz / (128 * 32)

    def __getitem__(self, item):
        return self._entities[item]

    def __iter__(self):
        return iter(self._entities.values())
