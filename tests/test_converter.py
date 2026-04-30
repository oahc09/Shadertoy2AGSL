"""Tests for the top-level converter: engine + AI fallback orchestration."""
import pytest
from scripts.converter import ConverterOutput, convert, needs_ai_fallback


class TestConvert:
    """Test suite for the top-level converter."""

    def test_simple_shader_no_ai_needed(self):
        """A simple shader converts fully without AI fallback."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv, 0.0, 1.0);
}
"""
        output = convert(glsl)
        assert isinstance(output, ConverterOutput)
        assert output.agsl_code != ""
        assert output.needs_ai_fallback is False
        assert output.unhandled_fragments == []

    def test_discard_shader_needs_ai_fallback(self):
        """A shader with discard needs AI fallback."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    if (fragCoord.x < 100.0) discard;
    fragColor = vec4(1.0);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is True
        assert len(output.unhandled_fragments) > 0
        assert any(f["kind"] == "discard" for f in output.unhandled_fragments)

    def test_multi_dim_array_needs_ai_fallback(self):
        """A shader with multi-dimensional arrays needs AI fallback."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    float data[4][4];
    fragColor = vec4(1.0);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is True
        assert any(f["kind"] == "multi_dim_array" for f in output.unhandled_fragments)

    def test_output_contains_report(self):
        """The output includes the conversion report."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    fragColor = vec4(1.0);
}
"""
        output = convert(glsl)
        assert isinstance(output.report, dict)
        assert "applied_rules" in output.report

    def test_output_contains_original_source(self):
        """The output includes the original source for AI context."""
        glsl = "void mainImage(out vec4 fragColor, in vec2 fragCoord) { fragColor = vec4(1.0); }"
        output = convert(glsl)
        assert output.original_source == glsl


class TestNeedsAiFallback:
    """Test suite for the needs_ai_fallback helper."""

    def test_returns_false_for_clean_code(self):
        """Clean code does not need AI fallback."""
        glsl = "float4 main(float2 fragCoord) { return float4(1.0); }"
        assert needs_ai_fallback(glsl) is False

    def test_returns_true_for_discard(self):
        """Code with discard needs AI fallback."""
        glsl = "if (x < 0.0) discard;"
        assert needs_ai_fallback(glsl) is True

    def test_returns_true_for_multi_dim_array(self):
        """Code with multi-dimensional arrays needs AI fallback."""
        glsl = "float arr[4][4];"
        assert needs_ai_fallback(glsl) is True
