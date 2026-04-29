"""Tests for the rule engine: orchestrates all patterns and markers."""
import pytest
from rules.engine import ConversionResult, convert_shader


class TestConvertShader:
    """Test suite for the main rule engine."""

    def test_simple_shader_full_pipeline(self):
        """A simple Shadertoy shader is fully converted to AGSL."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv.x, uv.y, 0.0, 1.0);
}
"""
        result = convert_shader(glsl)
        assert isinstance(result, ConversionResult)
        # Entry converted.
        assert "half4 main(float2 fragCoord)" in result.code
        assert "void mainImage" not in result.code
        # Types converted.
        assert "half2 uv" in result.code
        assert "half4(" in result.code
        # Coordinates flipped.
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result.code
        # Uniforms injected.
        assert "uniform float2 iResolution;" in result.code
        # FragColor replaced.
        assert "return " in result.code
        assert "fragColor = " not in result.code

    def test_texture_shader_full_pipeline(self):
        """A texture shader is fully converted."""
        glsl = """
uniform sampler2D iChannel0;

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);
}
"""
        result = convert_shader(glsl)
        assert "uniform shader iChannel0;" in result.code
        assert "iChannel0.eval(uv)" in result.code
        assert "sampler2D" not in result.code
        assert "texture(" not in result.code

    def test_complex_shader_full_pipeline(self):
        """A complex shader with defines, types, time is fully converted."""
        glsl = """
#define PI 3.14159

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float t = iTime * PI;
    mat2 rot = mat2(cos(t), -sin(t), sin(t), cos(t));
    vec2 p = rot * (uv - 0.5);
    float d = length(p);
    fragColor = vec4(vec3(smoothstep(0.3, 0.35, d)), 1.0);
}
"""
        result = convert_shader(glsl)
        assert "const half PI = 3.14159;" in result.code
        assert "uniform float iTime;" in result.code
        assert "uniform float2 iResolution;" in result.code
        assert "half2 uv" in result.code
        assert "half t" in result.code
        assert "half2x2 rot" in result.code
        assert "half4(" in result.code
        assert "half3(" in result.code

    def test_report_contains_applied_rules(self):
        """The conversion report lists which rules were applied."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv, 0.0, 1.0);
}
"""
        result = convert_shader(glsl)
        assert "entry" in result.report.applied_rules
        assert "types" in result.report.applied_rules
        assert "uniforms" in result.report.applied_rules
        assert "coordinates" in result.report.applied_rules

    def test_report_contains_markers_when_discard_found(self):
        """When discard is present, the report lists it as a marker."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    if (fragCoord.x < 100.0) discard;
    fragColor = vec4(1.0);
}
"""
        result = convert_shader(glsl)
        assert len(result.markers) > 0
        assert any(m.kind == "discard" for m in result.markers)

    def test_empty_input(self):
        """Empty input returns empty result."""
        result = convert_shader("")
        assert result.code == ""
        assert result.markers == []
        assert result.report.applied_rules == []

    def test_no_main_image_shader(self):
        """A shader without mainImage is still processed for types etc."""
        glsl = "float helper(float x) { return x * 2.0; }"
        result = convert_shader(glsl)
        assert "half helper(half x)" in result.code
        assert "entry" not in result.report.applied_rules
        assert "types" in result.report.applied_rules
