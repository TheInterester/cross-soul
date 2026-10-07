// with the help of
// https://github.com/OuchenTech/Shaders-in-Kivy/blob/main/GUIDE.md
// https://kivy.org/doc/stable/api-kivy.graphics.shader.html

---VERTEX SHADER---
$HEADER$

uniform mat4 screen_to_space, perspective, space_to_screen;
varying float depth;

void main() {
    frag_color = color * vec4(1, 1, 1, opacity);
    tex_coord0 = vTexCoords0;
    vec4 pos = screen_to_space * modelview_mat * vec4(vPosition, 0.0, 1.0);
    depth = pos.y;
    gl_Position = projection_mat * space_to_screen * perspective * pos;
}

---FRAGMENT SHADER---
$HEADER$

varying float depth;

void main() {
    float fade = clamp(2. * (1. - depth / 4000.), 0., 1.); // Sizes.FIELD_DEPTH
    gl_FragColor = texture2D(texture0, tex_coord0) * frag_color * vec4(1., 1., 1., fade);
}
