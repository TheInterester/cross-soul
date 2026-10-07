from utils import *
from config import Colors

class Placer(RelativeLayout, Generic[T]):
    """Widget wrapper for applying canvas transformations."""
    def __init__(self, widget: T):
        super().__init__()

        with StackFrame(self.canvas):
            with self.canvas:
                self.trans = Translate()
                self.scale = Scale()
                self.rot = Rotate()
            self.widget: T = widget
            self.add_widget(widget)

    def set_pos(self, pos):
        self.trans.xy = pos

    def set_scale(self, scale):
        self.scale.xyz = (scale,) * 3

    def set_angle(self, angle):
        self.rot.angle = angle

class TransPlacer(RelativeLayout, Generic[T]):
    """Widget wrapper for applying canvas transformations, that allows for interpolating to a new positioner."""
    def __init__(self, widget: T):
        super().__init__()

        with StackFrame(self.canvas):
            with self.canvas:
                self.trans = Translate()
                self.scale = Scale()
                self.rot = Rotate()
            self.widget: T = widget
            self.add_widget(widget)
        Clock.schedule_interval(self._update, 0)

    def set_pos(self, pos):
        self._pos = pos

    def set_scale(self, scale):
        self._scale = scale

    def set_angle(self, angle):
        self._angle = angle

    def _update(self, dt):
        self.oldness = max(0, self.oldness - dt * 2)
        s = slide(self.oldness, 1, 0, lambda x: 1-(1-x)**3)
        self.trans.xy = s(self.old_pos, self._pos)
        self.scale.xyz = (s(self.old_scale, self._scale),) * 3
        self.rot.angle = s(self.old_angle, self._angle)

    def snapshot(self):
        self.old_pos = self._pos
        self.old_scale = self._scale
        self.old_angle = self._angle
        self.oldness = 1

    _pos = ListProperty([0, 0])
    _scale = NumericProperty(1)
    _angle = NumericProperty(0)
    old_pos = ListProperty([0, 0])
    old_scale = NumericProperty(1)
    old_angle = NumericProperty(0)
    oldness = NumericProperty(0)

class Grid(RelativeLayout):
    """Debug visual for positioning help."""
    def __init__(self):
        super().__init__()

        with self.canvas:
            Color()
            for x in range(0, 401, 20):
                Line(
                    points=[x,0,x,300],
                    cap="square",
                )
            for y in range(0, 301, 20):
                Line(
                    points=[0,y,400,y],
                    cap="square",
                )
        self.hide()

    def show(self):
        self.canvas.opacity = 1

    def hide(self):
        self.canvas.opacity = 0

class DrawLabel(RelativeLayout):
    """An alternative label widget, since Label's quality doesn't account for canvas transforms."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._trigger = Clock.create_trigger(self._refresh, -1)
        self.bind(**{attr : self._trigger for attr in ["pos", "text", "variant", "anchor", "font_size", "quality", "color", "kwargs"]})
        with self.canvas:
            self.col = Color()
            self.rect = Rectangle()

    def _refresh(self, dt=0):
        title = CoreLabel(
            text=self.text,
            font_size=self.font_size * self.quality,
            font_name=f"./assets/SourceSans3-{self.variant}.ttf",
            **self.kwargs,
        )
        title.refresh()
        w, h = title.texture.size
        height = h / self.quality
        width = w / self.quality

        self.col.rgba = self.color
        self.rect.texture = title.texture
        self.rect.pos = (-self.anchor[0] * width, -self.anchor[1] * height)
        self.rect.size = (width, height)

    text = StringProperty("")
    variant = StringProperty("Regular")
    anchor = ListProperty([.5, .5])
    font_size = NumericProperty(0)
    quality = NumericProperty(10)
    color = ColorProperty([1, 1, 1, 1])
    kwargs = DictProperty({})

Factory.register("DrawLabel", cls=DrawLabel)

Builder.load_string("""
#: import math math

<GlitchRect>:
    canvas:
        Color:
            rgba: self.glitch1
        Line:
            rounded_rectangle: ( \
                math.cos(self.angle) * self.thickness, math.sin(self.angle) * self.thickness, \
                self.width, self.height, \
                self.radius, \
            )
            width: self.thickness / 2
        Color:
            rgba: self.glitch2
        Line:
            rounded_rectangle: ( \
                -math.cos(self.angle) * self.thickness, -math.sin(self.angle) * self.thickness, \
                self.width, self.height, \
                self.radius, \
            )
            width: self.thickness / 2
        Color:
            rgba: self.bg
        RoundedRectangle:
            size: self.size
            radius: [(self.radius, self.radius)]
        Color:
            rgba: self.border
        Line:
            rounded_rectangle: (0, 0, self.width, self.height, self.radius)
            width: self.thickness / 2

<GlitchText>:
    DrawLabel:
        pos: math.cos(self.parent.angle) * self.parent.thickness, math.sin(self.parent.angle) * self.parent.thickness
        text: self.parent.text
        variant: "Bold"
        font_size: self.parent.font_size
        color: self.parent.glitch1
    DrawLabel:
        pos: -math.cos(self.parent.angle) * self.parent.thickness, -math.sin(self.parent.angle) * self.parent.thickness
        text: self.parent.text
        variant: "Bold"
        font_size: self.parent.font_size
        color: self.parent.glitch2
    DrawLabel:
        pos: 0, 0
        text: self.parent.text
        variant: "Bold"
        font_size: self.parent.font_size
        color: self.parent.color
""")

class GlitchRect(RelativeLayout):
    """A cool rectangle."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.angle = rand.uniform(0, math.tau)
        self.vel = rand.uniform(.4, .6)
        if rand.getrandbits(1):
            self.vel *= -1
        Clock.schedule_interval(self._update, 0)

    def _update(self, dt):
        self.angle += dt * self.vel

    radius = NumericProperty(5)
    thickness = NumericProperty(3)
    angle = NumericProperty(0)

    glitch1 = ColorProperty(Colors.CYAN.rgba)
    glitch2 = ColorProperty(Colors.MAGENTA.rgba)
    bg = ColorProperty(Colors.PALE.rgba)
    border = ColorProperty(Colors.BORDER.rgba)

class GlitchText(RelativeLayout):
    """Cool text."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.angle = rand.uniform(0, math.tau)
        self.vel = -.5
        Clock.schedule_interval(self._update, 0)

    def _update(self, dt):
        self.angle += dt * self.vel

    text = StringProperty("CROSS SOUL")
    font_size = NumericProperty(40)

    thickness = NumericProperty(3)
    angle = NumericProperty(0)

    glitch1 = ColorProperty(Colors.CYAN.rgba)
    glitch2 = ColorProperty(Colors.MAGENTA.rgba)
    color = ColorProperty(Colors.VIOLET.rgba)
