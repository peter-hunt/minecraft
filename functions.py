from constants import *


__all__ = [
    'cube_vertices', 'normalize', 'sectorize', 'tex_coord', 'tex_coords',
]


def cube_vertices(x, y, z, n):
    'Return the vertices of the cube at position x, y, z with size 2*n.'
    return [
        x-n, y+n, z-n, x-n, y+n, z+n, x+n, y+n, z+n, x+n, y+n, z-n,  # top
        x-n, y-n, z-n, x+n, y-n, z-n, x+n, y-n, z+n, x-n, y-n, z+n,  # bottom
        x-n, y-n, z-n, x-n, y-n, z+n, x-n, y+n, z+n, x-n, y+n, z-n,  # left
        x+n, y-n, z+n, x+n, y-n, z-n, x+n, y+n, z-n, x+n, y+n, z+n,  # right
        x-n, y-n, z+n, x+n, y-n, z+n, x+n, y+n, z+n, x-n, y+n, z+n,  # front
        x+n, y-n, z-n, x-n, y-n, z-n, x-n, y+n, z-n, x+n, y+n, z-n,  # back
    ]


def normalize(position):
    """
    Accepts `position` of arbitrary precision and returns the block
    containing that position.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    block_position : tuple of ints of len 3
    """

    x, y, z = position
    return round(x), round(y), round(z)


def sectorize(position):
    """
    Returns a tuple representing the sector for the given `position`.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    sector : tuple of len 3
    """

    x, _, z = normalize(position)
    return x // CHUNK_SIZE, 0, z // CHUNK_SIZE


def tex_coord(x, y, n=4):
    'Return the bounding vertices of the texture square.'
    m = 1 / n
    dx, dy = x * m, y * m
    return dx, dy, dx + m, dy, dx + m, dy + m, dx, dy + m


def tex_coords(top, bottom, side):
    'Return a list of the texture squares for the top, bottom and side.'
    top = tex_coord(*top)
    bottom = tex_coord(*bottom)
    side = tex_coord(*side)
    return [top, bottom, side, side, side, side]
