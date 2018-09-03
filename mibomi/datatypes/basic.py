"""
This module contains basic data-types.
"""
import collections


Position = collections.namedtuple('Position', ['x', 'y', 'z'])
Rotation = collections.namedtuple('Rotation', ['x', 'y', 'z'])
Slot = collections.namedtuple('Slot', ['id', 'count', 'damage', 'nbt'])
