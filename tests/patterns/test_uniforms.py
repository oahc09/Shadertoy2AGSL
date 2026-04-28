"""Tests for the uniforms pattern: inject AGSL uniform declarations."""
import pytest
from rules.patterns.uniforms import inject_uniforms


class TestInjectUniforms:
    """Test suite for uniform declaration injection."""

    def test_injects_iResolution(self):
        """iResolution usage triggers uniform float2 iResolution declaration."""
        glsl = "vec2 uv = fragCoord / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float2 iResolution;" in result
        assert injected == ["iResolution"]

    def test_injects_iTime(self):
        """iTime usage triggers uniform float iTime declaration."""
        glsl = "float t = iTime * 2.0;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float iTime;" in result
        assert injected == ["iTime"]

    def test_injects_iMouse(self):
        """iMouse usage triggers uniform float4 iMouse declaration."""
        glsl = "vec2 mouse = iMouse.xy / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float4 iMouse;" in result
        assert "iMouse" in injected

    def test_injects_iResolution_and_iTime(self):
        """Multiple uniforms are all injected."""
        glsl = "vec2 uv = fragCoord / iResolution.xy;\nfloat t = iTime;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float2 iResolution;" in result
        assert "uniform float iTime;" in result
        assert set(injected) == {"iResolution", "iTime"}

    def test_no_uniforms_injected_when_none_used(self):
        """If no built-in uniforms are used, nothing is injected."""
        glsl = "half4 main(float2 fragCoord) { return half4(1.0); }"
        result, injected = inject_uniforms(glsl)
        assert "uniform" not in result
        assert injected == []

    def test_does_not_duplicate_existing_declarations(self):
        """If uniform is already declared, it is not injected again."""
        glsl = "uniform float2 iResolution;\nvec2 uv = fragCoord / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        assert result.count("uniform float2 iResolution;") == 1

    def test_injects_iFrame(self):
        """iFrame usage triggers uniform float iFrame declaration."""
        glsl = "if (iFrame < 10) { }"
        result, injected = inject_uniforms(glsl)
        assert "uniform float iFrame;" in result
        assert "iFrame" in injected

    def test_injects_iDate(self):
        """iDate usage triggers uniform float4 iDate declaration."""
        glsl = "float day = iDate.x;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float4 iDate;" in result
        assert "iDate" in injected

    def test_injects_iSampleRate(self):
        """iSampleRate usage triggers uniform float iSampleRate declaration."""
        glsl = "float rate = iSampleRate;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float iSampleRate;" in result
        assert "iSampleRate" in injected

    def test_uniforms_injected_before_first_line(self):
        """Injected declarations appear at the very top of the source."""
        glsl = "// My shader\nvec2 uv = fragCoord / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        lines = result.strip().split("\n")
        assert lines[0] == "uniform float2 iResolution;"

    def test_does_not_false_match_partial_names(self):
        """Names like iResolutionScale should not trigger iResolution injection."""
        glsl = "float iResolutionScale = 2.0;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float2 iResolution;" not in result
