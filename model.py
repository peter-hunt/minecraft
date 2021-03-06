from collections import deque
from logging import info
from math import floor
from time import perf_counter

from perlin_noise import PerlinNoise
from pyglet import image
from pyglet.gl import *
from pyglet.graphics import Batch, TextureGroup, VertextList

from constants import *
from functions import *
from utils import *


__all__ = ['Model']

BLOCKS: dict[str, list[list[number]]] = {
    'dirt': tex_coords((0, 1), (0, 1), (0, 1)),
    'grass_block': tex_coords((1, 0), (0, 1), (0, 0)),
    'sand': tex_coords((1, 1), (1, 1), (1, 1)),
    'bricks': tex_coords((2, 0), (2, 0), (2, 0)),
    'bedrock': tex_coords((2, 1), (2, 1), (2, 1)),
}


class Model(object):
    def __init__(self):
        # A Batch is a collection of vertex lists for batched rendering.
        self.batch: Batch = Batch()

        # A TextureGroup manages an OpenGL texture.
        self.group: TextureGroup = TextureGroup(image.load(TEXTURE_PATH).get_texture())

        # A mapping from position to the name of the block at that position.
        # This defines all the blocks that are currently in the world.
        self.world: dict[tuple[int], str] = {}

        # Same mapping as `world` but only contains blocks that are shown.
        self.shown: dict[tuple[int], list[list[int]]] = {}

        # Mapping from position to a pyglet `VertextList` for all shown blocks.
        self._shown: dict[tuple[int], VertextList] = {}

        # Mapping from sector to a list of positions inside that sector.
        self.sectors: dict[tuple[int], list[tuple[int]]] = {}

        # Simple function queue implementation. The queue is populated with
        # _show_block() and _hide_block() calls
        self.queue: deque = deque()

        self.generate_terrain()

    def generate_terrain(self):
        'Generate the world terrain.'

        info('Generating world terrain...')

        noise1 = PerlinNoise(octaves=7, seed=WORLD_SEED)
        noise2 = PerlinNoise(octaves=9, seed=WORLD_SEED + 1)
        noise3 = PerlinNoise(octaves=10, seed=WORLD_SEED + 2)

        n = 64  # 1 / 2 width and height of world
        for x in range(-n, n + 1):
            for z in range(-n, n + 1):
                y = 15
                y += noise1((x / 150, z / 150)) * 8
                y += noise2((x / 700, z / 700)) * 15
                y += noise3((x / 2000, z / 32000)) * 30
                y = floor(y)

                self.add_block((x, 0, z), 'bedrock', immediate=False)
                for _y in range(1, y):
                    self.add_block((x, _y, z), 'dirt', immediate=False)
                self.add_block((x, y, z), 'grass_block', immediate=False)

        info('Generated world terrain!')

    def hit_test(self, position: tuple[number],
                 vector: tuple[number], max_distance: number = 8) -> tuple[None | tuple[number]]:
        """
        Line of sight search from current position. If a block is
        intersected it is returned, along with the block previously in the line
        of sight. If no block is found, return None, None.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check visibility from.
        vector : tuple of len 3
            The line of sight vector.
        max_distance : int
            How many blocks away to search for a hit.
        """

        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in range(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self.world:
                return key, previous
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        return None, None

    def exposed(self, position: tuple[int]) -> bool:
        """
        Returns False is given `position` is surrounded on all 6 sides by
        blocks, True otherwise.
        """

        x, y, z = position
        for dx, dy, dz in FACES:
            if (x + dx, y + dy, z + dz) not in self.world:
                return True
        return False

    def add_block(self, position: tuple[int], name: str, immediate: bool = True):
        """
        Add a block with the given `name` and `position` to the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to add.
        name : string
            ID of the block.
        immediate : bool
            Whether or not to draw the block immediately.
        """

        if position in self.world:
            self.remove_block(position, immediate)
        self.world[position] = name
        self.sectors.setdefault(sectorize(position), []).append(position)
        if immediate:
            if self.exposed(position):
                self.show_block(position)
            self.check_neighbors(position)

    def remove_block(self, position: tuple[int], immediate: bool = True):
        """
        Remove the block at the given `position`.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to remove.
        immediate : bool
            Whether or not to immediately remove block from canvas.
        """

        del self.world[position]
        self.sectors[sectorize(position)].remove(position)
        if immediate:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(position)

    def check_neighbors(self, position: tuple[int]):
        """
        Check all blocks surrounding `position` and ensure their visual
        state is current. This means hiding blocks that are not exposed and
        ensuring that all exposed blocks are shown. Usually used after a block
        is added or removed.
        """

        x, y, z = position
        for dx, dy, dz in FACES:
            key = (x + dx, y + dy, z + dz)
            if key not in self.world:
                continue
            if self.exposed(key):
                if key not in self.shown:
                    self.show_block(key)
            else:
                if key in self.shown:
                    self.hide_block(key)

    def show_block(self, position: tuple[int], immediate: bool = True):
        """
        Show the block at the given `position`. This method assumes the
        block has already been added with add_block()

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        immediate : bool
            Whether or not to show the block immediately.
        """

        name = self.world[position]
        coords = BLOCKS[name]
        self.shown[position] = coords
        if immediate:
            self._show_block(position, coords)
        else:
            self._enqueue(self._show_block, position, coords)

    def _show_block(self, position: tuple[int], coords: list[list[number]]):
        """
        Private implementation of the `show_block()` method.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        coords : list of len 3
            The coordinates of the coords squares. Use `tex_coords()` to
            generate.
        """

        x, y, z = position
        vertex_data = cube_vertices(x, y, z, 0.5)
        coords_data = sum(coords, start=())
        # create vertex list
        # FIXME Maybe `add_indexed()` should be used instead
        self._shown[position] = self.batch.add(24, GL_QUADS, self.group,
            ('v3f/static', vertex_data),
            ('t2f/static', coords_data))

    def hide_block(self, position: tuple[int], immediate: bool = True):
        """
        Hide the block at the given `position`. Hiding does not remove the
        block from the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to hide.
        immediate : bool
            Whether or not to immediately remove the block from the canvas.
        """

        self.shown.pop(position)
        if immediate:
            self._hide_block(position)
        else:
            self._enqueue(self._hide_block, position)

    def _hide_block(self, position: tuple[int]):
        "Private implementation of the 'hide_block()` method."
        self._shown.pop(position).delete()

    def show_sector(self, sector: tuple[int]):
        """
        Ensure all blocks in the given sector that should be shown are
        drawn to the canvas.
        """

        for position in self.sectors.get(sector, []):
            if position not in self.shown and self.exposed(position):
                self.show_block(position, False)

    def hide_sector(self, sector: tuple[int]):
        """
        Ensure all blocks in the given sector that should be hidden are
        removed from the canvas.
        """

        for position in self.sectors.get(sector, []):
            if position in self.shown:
                self.hide_block(position, False)

    def change_sectors(self, before: tuple[int], after: tuple[int]):
        """
        Move from sector `before` to sector `after`. A sector is a
        contiguous x, y sub-region of world. Sectors are used to speed up
        world rendering.
        """

        before_set = set()
        after_set = set()
        pad = 4
        for dx in range(-pad, pad + 1):
            for dy in (0,):  # range(-pad, pad + 1):
                for dz in range(-pad, pad + 1):
                    if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                        continue
                    if before:
                        x, y, z = before
                        before_set.add((x + dx, y + dy, z + dz))
                    if after:
                        x, y, z = after
                        after_set.add((x + dx, y + dy, z + dz))
        show = after_set - before_set
        hide = before_set - after_set
        for sector in show:
            self.show_sector(sector)
        for sector in hide:
            self.hide_sector(sector)

    def _enqueue(self, func, *args):
        'Add `func` to the internal queue.'
        self.queue.append((func, args))

    def _dequeue(self):
        'Pop the top function from the internal queue and call it.'
        func, args = self.queue.popleft()
        func(*args)

    def process_queue(self):
        """
        Process the entire queue while taking periodic breaks. This allows
        the game loop to run smoothly. The queue contains calls to
        _show_block() and _hide_block() so this method should be called if
        add_block() or remove_block() was called with immediate=False
        """

        start = perf_counter()
        while self.queue and perf_counter() - start < 1 / TICKS_PER_SEC:
            self._dequeue()

    def process_entire_queue(self):
        'Process the entire queue without breaks.'
        while self.queue:
            self._dequeue()