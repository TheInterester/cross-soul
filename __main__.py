from kivy.config import Config

Config.set("graphics", "maxfps", "240")

import os, sys

from kivy.graphics.transformation import Matrix
from imslib.core import BaseWidget, run
from imslib.mixer import Mixer

from utils import *
from config import Colors, Texts, Sizes
import config as cfg
from widgets.common import Grid
from ranger import Rangers
from inputs import SurferInput, LanerInput
from cards import Card as ResultCard, State as ResultState
from menus.title import TitleMenu
from menus.select import SelectMenu
from menus.confirm import ConfirmMenu
from menus.game import GameMenu
from menus.results import ResultsMenu

from game.game import Game

from data import get_card_info

class MainWidget(BaseWidget):
    """The game is separated into Menus. This class should serve as a light wrapper;
    all specific functionality should be implemented in a Menu's handler."""

    MENUS = {
        "title": TitleMenu,
        "select": SelectMenu,
        "confirm": ConfirmMenu,
        "game": GameMenu,
        "results": ResultsMenu,
    }

    def __init__(self, demo):
        super().__init__()

        Window.show_cursor = False

        self.mixer = Mixer()
        self.mixer.set_gain(0.2)
        AUDIO.set_generator(self.mixer)

        # TODO read this from somewhere
        self.settings = {
            "speed": 4,
            "index": 0,
            "difficulty": 0,
        }

        self.surfer_input = SurferInput(self.on_surf)
        self.laner_input = LanerInput(self.on_down, self.on_up)

        self.screen_to_space = Matrix()
        self.perspective = Matrix()
        self.space_to_screen = Matrix()

        with self.canvas:
            self.bg = RenderContext(use_parent_modelview=True, use_parent_projection=True)
            self.translate = Translate()
            self.scale = Scale()

        self.bg.shader.source = "./shaders/bg.glsl"
        self.bg["screen_to_space"] = self.screen_to_space
        self.bg["iTime"] = rand.uniform(0, 3600)
        self.bg["baseRGB"] = (0.4, 0.1, 0.2)
        self.bg["glowRGB"] = (0.3, 0.3, 1.0)
        with self.bg:
            self.bg_rect = Rectangle()

        self.wrapper = RelativeLayout()
        """container for the current menu"""
        self.add_widget(self.wrapper)

        self.rangers = Rangers()
        self.add_widget(self.rangers)

        self.grid = Grid()
        self.add_widget(self.grid)

        self.old_menu = None
        self.menu = None
        if demo:
            # TODO temp testing
            song_info = get_card_info("./songs/Window View/")
            self.transition("game", Game(self, cb=None, song_info=song_info, diff=0, preview=False))
        else:
            self.transition("title")

        self.on_resize(Window.size)

    def transition(self, menu_name, *args):
        if self.old_menu is not None:
            warn("Old menu didn't have time to disappear!")
            self.wrapper.remove_widget(self.old_menu)
        menu = self.MENUS[menu_name](self, *args)
        menu.on_surf(self.surfer_input.pos)
        self.old_menu = self.menu
        self.menu = menu
        menu.size = (400, 300)
        self.wrapper.add_widget(menu)

    def on_key_down(self, keycode, modifiers):
        """forwarder to self.laner which is the laner input authority"""
        if hasattr(self.menu, "on_key_down"):
            self.menu.on_key_down(keycode, modifiers)
        self.laner_input.on_key_down(keycode)
        # the below is temp debugging
        match keycode[1]:
            case "`":
                self.grid.show()

    def on_key_up(self, keycode):
        """forwarder to self.laner which is the laner input authority"""
        if hasattr(self.menu, "on_key_up"):
            self.menu.on_key_up(keycode)
        self.laner_input.on_key_up(keycode)
        # the below is temp debugging
        match keycode[1]:
            case "`":
                self.grid.hide()

    def on_resize(self, win_size):
        """Ensures the game can pretend it's in a 400x300 area.
        Said area is centered in the window and as large as possible."""
        w, h = win_size
        w /= 400
        h /= 300
        s = min(w, h)
        if w < h:
            self.translate.xy = (0, (h - w) * 300 / 2)
        else:
            self.translate.xy = ((w - h) * 400 / 2, 0)
        self.scale.xyz = (s,) * 3
        self.bg_rect.size = win_size

        # Kivy .multiply() kills the w coordinate...
        self.screen_to_space.set(array=
            # transform to game coordinates
            translate(*(-x for x in self.translate.xyz))
            @ scale(1/s)
        )
        self.perspective.set(array=
            # treat y as -z (+y -> into the screen)
            np.array([
                [1.,0.,0.,0.],
                [0.,0.,-1.,0.],
                [0.,0.,0.,0.],
                [0.,0.,0.,1.],
            ])
            # translate to observer's perspective
            @ translate(*(-x for x in Sizes.OBSERVER))
            # do perspective such that z = -Sizes.OBSERVER[2] is unchanged
            @ np.array([
                [1.,0.,0.,0.],
                [0.,1.,0.,0.],
                [0.,0.,0.,-1./Sizes.OBSERVER[2]],
                [0.,0.,0.,0.],
            ])
            # un-translate, but we ignore z now
            @ translate(Sizes.OBSERVER[0], Sizes.OBSERVER[1], 0)
        )
        self.space_to_screen.set(array=
            # un-transform from game coordinates
            scale(s)
            @ translate(*self.translate.xyz)
        )

    def on_surf(self, pos):
        """surfer position change handler"""
        self.menu.on_surf(pos)

    def on_down(self, pos):
        """laner key down handler"""
        # TODO a bit hacky, maybe menus should inherit from base class?
        if hasattr(self.menu, "on_down"):
            self.menu.on_down(pos)
        self.rangers.on_down(pos)

    def on_up(self, pos):
        """laner key up handler"""
        if hasattr(self.menu, "on_up"):
            self.menu.on_up(pos)
        self.rangers.on_up(pos)

    def on_update(self):
        dt = Clock.frametime
        self.bg["iTime"] += dt
        AUDIO.on_update()
        if self.menu.update(dt):
            warn("Active menu claims done!")
        if self.old_menu is not None:
            if self.old_menu.update(dt):
                self.wrapper.remove_widget(self.old_menu)
                self.old_menu = None
        self.rangers.update(dt)


if __name__ == "__main__":
    args = set(sys.argv[1:])
    run(MainWidget(demo="--demo" in args), fullscreen="--full" in args)
