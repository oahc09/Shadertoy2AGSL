"""Tests for the entry pattern: mainImage → main conversion."""
import pytest
from rules.patterns.entry import convert_entry


class TestConvertEntry:
    """Test suite for entry function conversion."""

    def test_converts_signature_single_line(self):
        """Single-line mainImage signature is converted to main."""
        glsl = "void mainImage(out vec4 fragColor, in vec2 fragCoord) {"
        result, applied = convert_entry(glsl)
        assert "half4 main(float2 fragCoord)" in result
        assert "void mainImage" not in result
        assert applied is True

    def test_converts_signature_multi_line(self):
        """Multi-line mainImage signature is converted to main."""
        glsl = (
            "void mainImage(\n"
            "    out vec4 fragColor,\n"
            "    in vec2 fragCoord\n"
            ")\n"
            "{"
        )
        result, applied = convert_entry(glsl)
        assert "half4 main(float2 fragCoord)" in result
        assert "void mainImage" not in result
        assert applied is True

    def test_replaces_fragColor_assignments(self):
        """All `fragColor = ...` assignments become `return ...`."""
        glsl = (
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    vec2 uv = fragCoord / iResolution.xy;\n"
            "    fragColor = vec4(uv, 0.0, 1.0);\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert "return vec4(uv, 0.0, 1.0);" in result
        assert "fragColor = " not in result
        assert applied is True

    def test_replaces_multiple_fragColor_assignments(self):
        """Shaders with multiple fragColor assignments (branches) all become return."""
        glsl = (
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    if (fragCoord.x < 100.0) {\n"
            "        fragColor = vec4(1.0, 0.0, 0.0, 1.0);\n"
            "    } else {\n"
            "        fragColor = vec4(0.0, 1.0, 0.0, 1.0);\n"
            "    }\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert result.count("return ") == 2
        assert "fragColor = " not in result
        assert applied is True

    def test_preserves_non_entry_code(self):
        """Code outside mainImage is left unchanged."""
        glsl = (
            "float helper(float x) {\n"
            "    return x * 2.0;\n"
            "}\n"
            "\n"
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    fragColor = vec4(1.0);\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert "float helper(float x)" in result
        assert "return x * 2.0;" in result
        assert applied is True

    def test_no_main_image_returns_unchanged(self):
        """If no mainImage function exists, input is returned unchanged."""
        glsl = "float foo(float x) { return x; }"
        result, applied = convert_entry(glsl)
        assert result == glsl
        assert applied is False

    def test_preserves_comments(self):
        """Comments in the shader are preserved."""
        glsl = (
            "// This is a test shader\n"
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    fragColor = vec4(1.0); // white\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert "// This is a test shader" in result
        assert "// white" in result
        assert applied is True

    def test_handles_fragColor_with_swizzle(self):
        """fragColor.rgb = ... is left for markers (not converted)."""
        glsl = (
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    fragColor = vec4(0.0);\n"
            "    fragColor.rgb = vec3(1.0, 0.0, 0.0);\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert "return vec4(0.0);" in result
        assert applied is True
        assert "fragColor.rgb" in result
