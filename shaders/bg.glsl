// with the help of
// https://github.com/OuchenTech/Shaders-in-Kivy/blob/main/GUIDE.md
// https://kivy.org/doc/stable/api-kivy.graphics.shader.html

---VERTEX SHADER---
$HEADER$

uniform mat4 screen_to_space;
varying vec4 pos;

void main() {
    tex_coord0 = vTexCoords0;
    vec4 screen = modelview_mat * vec4(vPosition, 0.0, 1.0);
    pos = screen_to_space * screen;
    gl_Position = projection_mat * screen;
}

---FRAGMENT SHADER---
$HEADER$

// original: https://www.shadertoy.com/view/MtKXzc

uniform float iTime;
varying vec4 pos;
uniform vec3 baseRGB;
uniform vec3 glowRGB;

vec4 mainImage( vec2 screen )
{
    float fade = 1.-screen.y/300.;
    screen.x -= 200.;
    float h = 300.;
	vec2 space = vec2(screen.x * h / (h - screen.y), screen.y * 400. / (h - screen.y));
    space.y -= iTime * 100.;
    vec2 U = abs(fract(space / 100.+.5)-.5);           // distance to axis
    U = .1/ sqrt(U);                // turn to blured line
    return vec4((U.x*fade+U.y*fade*2.) * glowRGB + baseRGB, fade); // combine H&V + color * inverted fade
}

void main() {
    gl_FragColor = mainImage(pos.xy);
}
