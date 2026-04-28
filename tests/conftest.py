"""Shared test fixtures for Shadertoy→AGSL converter tests."""
import pytest


@pytest.fixture
def simple_shadertoy_shader():
    """A minimal valid Shadertoy shader for testing."""
    return """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv.x, uv.y, 0.0, 1.0);
}
"""


@pytest.fixture
def texture_shadertoy_shader():
    """A Shadertoy shader that uses texture sampling."""
    return """
uniform sampler2D iChannel0;

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);
}
"""


@pytest.fixture
def complex_shadertoy_shader():
    """A Shadertoy shader with preprocessor, types, and coordinates."""
    return """
#define PI 3.14159
#define SPEED 2.0

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float t = iTime * SPEED;
    mat2 rot = mat2(cos(t), -sin(t), sin(t), cos(t));
    vec2 p = rot * (uv - 0.5);
    float d = length(p);
    fragColor = vec4(vec3(smoothstep(0.3, 0.35, d)), 1.0);
}
"""
