from json import load as json_load
from logging import INFO, getLogger, info
from os.path import join
from pathlib import Path
from sys import version_info

from pyglet import app, image
from pyglet.gl import *
from pyglet.graphics import TextureGroup

from constants import *
from window import Window


if (*version_info,) < (3, 10):
    raise Exception('This project requires at least Python 3.10 to execute!')

if USE_LOG:
    getLogger().setLevel(INFO)

info('Loading Assets...')

TEXTURES = {}
MODELS = {}


def init_data(namespace):
    """
    Load vanilla minecraft data.

    Parameters
    ----------
    namespace : namespace in the assets folder
    """

    info('Assets: Loading models...')
    for folder in Path(join('assets', namespace, 'models')).iterdir():
        if not folder.is_dir():
            continue
        for file in folder.iterdir():
            if not file.is_file():
                continue
            if file.suffix != '.json':
                continue
            with open(file) as model:
                MODELS[f'{namespace}:{folder.name}/{file.name.rstrip(file.suffix)}'] = \
                    json_load(model)

    info('Assets: Loading textures...')
    for folder in Path(join('assets', namespace, 'textures')).iterdir():
        if not folder.is_dir():
            continue
        for file in folder.iterdir():
            if not file.is_file():
                continue
            if file.suffix != '.png':
                continue
            TEXTURES[f'{namespace}:{folder.name}/{file.name.rstrip(file.suffix)}'] = \
                TextureGroup(image.load(file).get_texture())

        for subfolder in folder.iterdir():
            if not subfolder.is_dir():
                continue
            for file in subfolder.iterdir():
                if not file.is_file():
                    continue
                if file.suffix != '.png':
                    continue
                TEXTURES[f'{namespace}:{folder.name}/{subfolder.name}/{file.name.rstrip(file.suffix)}'] = \
                    TextureGroup(image.load(file).get_texture())


init_data(NAMESPACE)

info('Loaded Assets!')


def setup_fog():
    'Configure the OpenGL fog properties.'
    # Enable fog. Fog "blends a fog color with each
    # rasterized pixel fragment's post-texturing color."
    glEnable(GL_FOG)
    # transparency
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # Set the fog color.
    glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.47, 0.65, 1.0, 1))
    # Say we have no preference between rendering speed and quality.
    glHint(GL_FOG_HINT, GL_DONT_CARE)
    # Specify the equation used to compute the blending factor.
    glFogi(GL_FOG_MODE, GL_LINEAR)
    # How close and far away fog starts and ends. The closer the start and end,
    # the denser the fog in the fog range.
    glFogf(GL_FOG_START, 20)
    glFogf(GL_FOG_END, 60)


def setup():
    'Basic OpenGL configuration.'
    # Set the color of "clear", i.e. the sky, in rgba.
    glClearColor(0.47, 0.65, 1.0, 1)
    # Enable culling (not rendering) of back-facing facets -- facets that aren't
    # visible to you.
    glEnable(GL_CULL_FACE)
    # Set the texture minification/magnification function to GL_NEAREST (nearest
    # in Manhattan distance) to the specified texture coordinates. GL_NEAREST
    # "is generally faster than GL_LINEAR, but it can produce textured images
    # with sharper edges because the transition between texture elements is not
    # as smooth."
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    setup_fog()


def main():
    window = Window(width=800, height=600,
                    caption='Minecraft Python', resizable=True)
    # Hide the mouse cursor and prevent the mouse from leaving the window.
    window.set_exclusive_mouse(True)
    setup()
    app.run()
