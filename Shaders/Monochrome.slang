#version 450
// SPDX-License-Identifier: GPL-3.0-or-later
// EarthBound Companion: final-output shader, independent of game data.
layout(push_constant) uniform ImageSizes { vec4 SourceSize; vec4 OriginalSize; vec4 OutputSize; } image;
layout(std140, set=0, binding=0) uniform Transform { mat4 MVP; } transform;
#pragma stage vertex
layout(location=0) in vec4 Position;
layout(location=1) in vec2 TexCoord;
layout(location=0) out vec2 uv;
void main() { gl_Position=transform.MVP*Position; uv=TexCoord; }
#pragma stage fragment
layout(location=0) in vec2 uv;
layout(location=0) out vec4 FragColor;
layout(set=0, binding=2) uniform sampler2D Source;
void main() {
    vec3 color=texture(Source,uv).rgb;
    color=vec3(dot(color,vec3(0.2126,0.7152,0.0722)));
    FragColor=vec4(color,1.0);
}
