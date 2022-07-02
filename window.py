from math import atan2, cos, degrees, floor, radians, sin, sqrt
from sys import version_info

import pyglet
from pyglet import clock, graphics
from pyglet.gl import *
from pyglet.shapes import Rectangle
from pyglet.text import Label
from pyglet.window import Window as PygletWindow, key, mouse

from constants import *
from functions import *
from model import Model


keyboard = key.KeyStateHandler()

JUMP_SPEED = sqrt(2 * GRAVITY * MAX_JUMP_HEIGHT)


class Window(PygletWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        # Whether or not the window exclusively captures the mouse.
        self.exclusive = False
        self.flying = False
        self.sneaking = False
        self.sprinting = False

        # Whether F3 Debug Screen is toggled
        self.do_debug = False

        # Strafing is moving lateral to the direction you are facing,
        # e.g. moving to the left or right while continuing to face forward.
        #
        # First element is -1 when moving forward, 1 when moving back, and 0
        # otherwise. The second element is -1 when moving left, 1 when moving
        # right, and 0 otherwise.
        self.strafe = [0, 0]

        # First element is rotation of the player in the x-z plane (ground
        # plane) measured from the z-axis down. The second is the rotation
        # angle from the ground plane up. Rotation is in degrees.
        #
        # The vertical plane rotation ranges from -90 (looking straight down) to
        # 90 (looking straight up). The horizontal rotation range is unbounded.
        self.rotation = (0, 0)

        # Which sector the player is currently in.
        self.sector = None

        # The crosshairs at the center of the screen.
        self.reticle = None

        # Velocity in the y (upward) direction.
        self.dy = 0

        # A list of blocks the player can place. Hit num keys to cycle.
        self.inventory = ['dirt', 'grass_block', 'sand', 'bricks']

        # The current block the user can place. Hit num keys to cycle.
        self.block = self.inventory[0]

        # Convenience list of num keys.
        self.num_keys = [
            key._1, key._2, key._3, key._4, key._5,
            key._6, key._7, key._8, key._9, key._0]

        # Instance of the model that handles the world.
        self.model = Model()

        spawny = 1
        self.position = (0, 1, 0)
        while self.position in self.model.world:
            self.position = (0, spawny, 0)
            spawny += 1
        self.position = (0, spawny, 0)

        # Debug screen labels.
        self.left_labels = []
        self.left_label_size = 7
        self.left_label_bg = []
        y = self.height * 0.97
        for i in range(self.left_label_size):
            self.left_labels.append(
                Label(
                    '', font_name='Arial', font_size=self.height * 0.02,
                    bold=True, x=self.width * 0.03, y=y,
                    anchor_x='left', anchor_y='top',
                    color=(255, 255, 255, 255)))
            self.left_label_bg.append(
                Rectangle(
                    x=self.width * 0.025, y=y - self.height * 0.035,
                    width=1, height=1,
                    color=(40, 40, 40)))
            self.left_label_bg[i].opacity = 40
            y -= self.height * 0.03

        self.right_labels = []
        self.right_label_size = 1
        self.right_label_bg = []
        y = self.height * 0.97
        for i in range(self.right_label_size):
            self.right_labels.append(
                Label(
                    '', font_name='Arial', font_size=self.height * 0.02,
                    bold=True, x=self.width * 0.97, y=y,
                    anchor_x='right', anchor_y='top',
                    color=(255, 255, 255, 255)))
            self.right_label_bg.append(
                Rectangle(
                    x=self.width * 0.975, y=y - self.height * 0.035,
                    width=1, height=1,
                    color=(40, 40, 40)))
            self.right_label_bg[i].opacity = 40
            y -= self.height * 0.03

        # This call schedules the `update()` method to be called
        # TICKS_PER_SEC. This is the main game event loop.
        clock.schedule_interval(self.update, 1 / TICKS_PER_SEC)

        self.push_handlers(keyboard)

    def set_exclusive_mouse(self, exclusive):
        """
        If `exclusive` is True, the game will capture the mouse, if False
        the game will ignore the mouse.
        """

        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def get_sight_vector(self):
        """
        Returns the current line of sight vector indicating the direction
        the player is looking.
        """

        x, y = self.rotation
        # y ranges from -90 to 90, or -pi/2 to pi/2, so m ranges from 0 to 1 and
        # is 1 when looking ahead parallel to the ground and 0 when looking
        # straight up or down.
        m = cos(radians(y))
        # dy ranges from -1 to 1 and is -1 when looking straight down and 1 when
        # looking straight up.
        dy = sin(radians(y))
        dx = cos(radians(x - 90)) * m
        dz = sin(radians(x - 90)) * m
        return (dx, dy, dz)

    def get_motion_vector(self):
        """
        Returns the current motion vector indicating the velocity of the
        player.

        Returns
        -------
        vector : tuple of len 3
            Tuple containing the velocity in x, y, and z respectively.
        """

        if any(self.strafe):
            x, y = self.rotation
            strafe = degrees(atan2(*self.strafe))
            x_angle = radians(x + strafe)
            if self.flying:
                dx = cos(x_angle)
                dy = 0
                if keyboard[key.SPACE]:
                    dy += FLYING_Y_SPEED
                if keyboard[key.LSHIFT]:
                    dy -= FLYING_Y_SPEED
                dz = sin(x_angle)
            else:
                dx = cos(x_angle)
                dy = 0
                dz = sin(x_angle)
        else:
            dy = 0
            dx = 0
            dz = 0
            if self.flying:
                if keyboard[key.SPACE]:
                    dy += FLYING_Y_SPEED
                if keyboard[key.LSHIFT]:
                    dy -= FLYING_Y_SPEED
        return dx, dy, dz

    def update(self, dt):
        """
        This method is scheduled to be called repeatedly by the pyglet
        clock.

        Parameters
        ----------
        dt : float
            The change in time since the last call.
        """

        self.model.process_queue()
        sector = sectorize(self.position)
        if sector != self.sector:
            self.model.change_sectors(self.sector, sector)
            if self.sector is None:
                self.model.process_entire_queue()
            self.sector = sector
        m = 8  # TODO: increase this
        dt = min(dt, 0.2)
        for _ in range(m):
            self._update(dt / m)

    def _update(self, dt):
        """
        Private implementation of the `update()` method. This is where most
        of the motion logic lives, along with gravity and collision detection.

        Parameters
        ----------
        dt : float
            The change in time since the last call.
        """

        # moving
        if self.sneaking:
            speed = SNEAKING_SPEED
        else:
            if self.sprinting:
                speed = FLYING_SPRINT_SPEED if self.flying else SPRINTING_SPEED
            else:
                speed = FLYING_SPEED if self.flying else WALKING_SPEED

        d = dt * speed # distance covered this tick.
        dx, dy, dz = self.get_motion_vector()
        # New position in space, before accounting for gravity.
        dx, dy, dz = dx * d, dy * d, dz * d
        # gravity
        if not self.flying:
            # Update your vertical speed: if you are falling, speed up until you
            # hit terminal velocity; if you are jumping, slow down until you
            # start falling.
            self.dy -= dt * GRAVITY
            self.dy = max(self.dy, -TERMINAL_VELOCITY)
            dy += self.dy * dt
        # collisions
        x, y, z = self.position
        x, y, z = self.collide((x + dx, y + dy, z + dz), PLAYER_HEIGHT)
        self.position = (x, y, z)

    def collide(self, position, height):
        """
        Checks to see if the player at the given `position` and `height`
        is colliding with any blocks in the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check for collisions at.
        height : int or float
            The height of the player.

        Returns
        -------
        position : tuple of len 3
            The new position of the player taking into account collisions.
        """

        # How much overlap with a dimension of a surrounding block you need to
        # have to count as a collision. If 0, touching terrain at all counts as
        # a collision. If .49, you sink into the ground, as if walking through
        # tall grass. If >= .5, you'll fall through the ground.
        pad = 0.2
        p = list(position)
        np = normalize(position)
        for face in FACES:  # check all surrounding blocks
            for i in range(3):  # check each dimension independently
                if not face[i]:
                    continue
                # How much overlap you have with this dimension.
                d = (p[i] - np[i]) * face[i]
                if d < pad:
                    continue
                for dy in range(floor(height)):  # check each height
                    op = list(np)
                    op[1] -= dy
                    op[i] += face[i]
                    if tuple(op) not in self.model.world:
                        continue
                    p[i] -= (d - pad) * face[i]
                    if face == (0, -1, 0) or face == (0, 1, 0):
                        # You are colliding with the ground or ceiling, so stop
                        # falling / rising.
                        self.dy = 0
                    break
        return tuple(p)

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Called when a mouse button is pressed. See pyglet docs for button
        amd modifier mappings.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        button : int
            Number representing mouse button that was clicked. 1 = left button,
            4 = right button.
        modifiers : int
            Number representing any modifying keys that were pressed when the
            mouse button was clicked.
        """

        if self.exclusive:
            vector = self.get_sight_vector()
            block, previous = self.model.hit_test(self.position, vector)
            if (button == mouse.RIGHT) or \
                    ((button == mouse.LEFT) and (modifiers & key.MOD_CTRL)):
                # ON OSX, control + left click = right click.
                if previous:
                    self.model.add_block(previous, self.block)
            elif button == mouse.LEFT and block:
                name = self.model.world[block]
                if name != 'bedrock':
                    self.model.remove_block(block)
        else:
            self.set_exclusive_mouse(True)

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called when the player moves the mouse.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        dx, dy : float
            The movement of the mouse.
        """

        if self.exclusive:
            m = 0.15
            x, y = self.rotation
            x, y = x + dx * m, y + dy * m
            y = max(-90, min(90, y))
            self.rotation = (x, y)

    def on_key_press(self, symbol, modifiers):
        """
        Called when the player presses a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.
        """

        if symbol == key.W:
            self.strafe[0] -= 1
        elif symbol == key.S:
            self.strafe[0] += 1
        elif symbol == key.A:
            self.strafe[1] -= 1
        elif symbol == key.D:
            self.strafe[1] += 1
        elif symbol == key.LSHIFT:
            if not self.flying:
                self.sneaking = True
        elif symbol == key.SPACE:
            if not self.flying:
                if self.dy == 0:
                    self.dy = JUMP_SPEED
        elif symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)
        elif symbol == key.TAB:
            self.flying = not self.flying
            if self.flying:
                self.sneaking = False
        elif symbol == key.LALT:
            self.sprinting = True
        elif symbol in self.num_keys:
            index = (symbol - self.num_keys[0]) % len(self.inventory)
            self.block = self.inventory[index]
        elif symbol == key.F3:
            self.do_debug = not self.do_debug

    def on_key_release(self, symbol, modifiers):
        """
        Called when the player releases a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.
        """

        if symbol == key.W:
            self.strafe[0] += 1
        elif symbol == key.S:
            self.strafe[0] -= 1
        elif symbol == key.A:
            self.strafe[1] += 1
        elif symbol == key.D:
            self.strafe[1] -= 1
        elif symbol == key.LSHIFT:
            if self.flying:
                self.dy += FLYING_Y_SPEED
            else:
                self.sneaking = False
        elif symbol == key.SPACE:
            if self.flying:
                self.dy -= FLYING_Y_SPEED

    def on_resize(self, width, height):
        'Called when the window is resized to a new `width` and `height`.'
        # reticle
        if self.reticle:
            self.reticle.delete()
        x, y = width // 2, height // 2
        n = 10
        self.reticle = graphics.vertex_list(4,
            ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n))
        )

        # labels
        y = height * 0.97
        for i in range(self.left_label_size):
            self.left_labels[i].font_size = height * 0.02
            self.left_labels[i].x = width * 0.03
            self.left_labels[i].y = y
            self.left_label_bg[i].x = width * 0.025
            self.left_label_bg[i].y = y - height * 0.035
            y -= height * 0.03

        y = height * 0.97
        for i in range(self.right_label_size):
            self.right_labels[i].font_size = height * 0.02
            self.right_labels[i].x = width * 0.97
            self.right_labels[i].y = y
            self.right_label_bg[i].x = width * 0.975
            self.right_label_bg[i].y = y - height * 0.035
            y -= height * 0.03

    def set_2d(self):
        'Configure OpenGL to draw in 2d.'
        width, height = self.get_size()
        glDisable(GL_DEPTH_TEST)
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, max(1, width), 0, max(1, height), -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set_3d(self):
        'Configure OpenGL to draw in 3d.'
        width, height = self.get_size()
        glEnable(GL_DEPTH_TEST)
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(65, width / float(height), 0.1, 60)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        x, y = self.rotation
        glRotatef(x, 0, 1, 0)
        glRotatef(-y, cos(radians(x)), 0, sin(radians(x)))
        x, y, z = self.position
        glTranslatef(-x, -y, -z)

    def on_draw(self):
        'Called by pyglet to draw the canvas.'
        self.clear()
        self.set_3d()
        glColor3d(1, 1, 1)
        self.model.batch.draw()
        self.draw_focused_block()
        self.set_2d()

        if self.do_debug:
            self.draw_label()

        self.draw_reticle()

    def draw_focused_block(self):
        """
        Draw black edges around the block that is currently under the
        crosshairs.
        """

        vector = self.get_sight_vector()
        block = self.model.hit_test(self.position, vector)[0]
        if block:
            x, y, z = block
            vertex_data = cube_vertices(x, y, z, 0.51)
            glColor3d(0, 0, 0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            pyglet.graphics.draw(24, GL_QUADS, ('v3f/static', vertex_data))
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def draw_label(self):
        'Draw the label in the top left of the screen.'
        rot_1 = self.rotation[0] % 360
        x, y, z = self.position
        ix, iy, iz = floor(x), floor(y), floor(z)
        if rot_1 < 45 or rot_1 >= 315:
            direction = 'north (Towards negative Z)'
        elif 45 <= rot_1 < 135:
            direction = 'east (Towards positive X)'
        elif 135 <= rot_1 < 225:
            direction = 'south (Towards positive Z)'
        else:
            direction = 'west (Towards negative X)'

        left_debug = f'''\
Minecraft Python (recreation)
{clock.get_fps():.0f} fps

XYZ: {x:.3f} / {y:.5f} / {z:.3f}
Block: {ix:d} {iy:d} {iz:d}
Chunk: {ix%16:d} {iy%16:d} {iz%16:d} in {ix//16} {iy//16} {iz//16}
Facing: {direction} ({rot_1:.1f} / {self.rotation[1]:.1f})\
'''.split('\n')

        # len(self.model._shown), len(self.model.world)
        for i in range(min(self.left_label_size, len(left_debug))):
            self.left_labels[i].text = left_debug[i]

        for label in self.left_labels:
            self.left_label_bg[i].width = label.content_width + self.width + 0.01
            self.left_label_bg[i].height = label.content_height + self.height + 0.01
            self.left_label_bg[i].x = self.width * 0.975 - self.left_label_bg[i].width
            self.left_label_bg[i].draw()

        right_debug = f'''\
Python: {version_info.major}.{version_info.minor}.{version_info.micro}\
'''.split('\n')

        # len(self.model._shown), len(self.model.world)
        for i in range(min(self.right_label_size, len(right_debug))):
            self.right_labels[i].text = right_debug[i]

        for label in self.right_labels:
            self.right_label_bg[i].width = label.content_width + self.width + 0.01
            self.right_label_bg[i].height = label.content_height + self.height + 0.01
            self.right_label_bg[i].x = self.width * 0.975 - self.right_label_bg[i].width
            self.right_label_bg[i].draw()

        for label in self.left_labels:
            label.draw()
        for label in self.right_labels:
            label.draw()

    def draw_reticle(self):
        'Draw the crosshairs in the center of the screen.'
        glColor3d(0, 0, 0)
        self.reticle.draw(GL_LINES)
