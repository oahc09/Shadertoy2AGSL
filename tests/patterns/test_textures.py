"""Tests for the textures pattern: sampler2D → shader, texture() → .eval()."""
import pytest
from scripts.rules.patterns.textures import convert_textures


class TestConvertTextures:
    """Test suite for texture sampling conversion."""

    def test_converts_sampler2D_declaration(self):
        """uniform sampler2D iChannel0 → uniform shader iChannel0."""
        glsl = "uniform sampler2D iChannel0;"
        result, applied = convert_textures(glsl)
        assert "uniform shader iChannel0;" in result
        assert "sampler2D" not in result
        assert applied is True

    def test_converts_texture_call_single_channel(self):
        """texture(iChannel0, uv) → iChannel0.eval(uv)."""
        glsl = "fragColor = texture(iChannel0, uv);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert "texture(iChannel0" not in result
        assert applied is True

    def test_converts_texture_call_with_lod(self):
        """texture(iChannel0, uv, lod) → iChannel0.eval(uv)."""
        glsl = "fragColor = texture(iChannel0, uv, 0.0);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert applied is True

    def test_converts_multiple_channels(self):
        """Multiple texture channels are all converted."""
        glsl = (
            "uniform sampler2D iChannel0;\n"
            "uniform sampler2D iChannel1;\n"
            "vec4 c0 = texture(iChannel0, uv);\n"
            "vec4 c1 = texture(iChannel1, uv);\n"
        )
        result, applied = convert_textures(glsl)
        assert "uniform shader iChannel0;" in result
        assert "uniform shader iChannel1;" in result
        assert "iChannel0.eval(uv)" in result
        assert "iChannel1.eval(uv)" in result
        assert "sampler2D" not in result
        assert "texture(" not in result
        assert applied is True

    def test_no_textures_returns_unchanged(self):
        """If no texture usage found, input is returned unchanged."""
        glsl = "float4 main(float2 fragCoord) { return float4(1.0); }"
        result, applied = convert_textures(glsl)
        assert result == glsl
        assert applied is False

    def test_converts_sampler2D_without_explicit_declaration(self):
        """Even without explicit uniform declaration, texture() calls are converted."""
        glsl = "fragColor = texture(iChannel0, uv);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert applied is True

    def test_preserves_texture_in_comments(self):
        """Texture references inside comments are left alone."""
        glsl = "// texture(iChannel0, uv)\nfragColor = texture(iChannel1, uv);"
        result, applied = convert_textures(glsl)
        assert "// texture(iChannel0, uv)" in result
        assert "iChannel1.eval(uv)" in result
        assert applied is True

    def test_handles_whitespace_in_texture_call(self):
        """texture calls with extra whitespace are handled."""
        glsl = "fragColor = texture(  iChannel0 , uv );"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert applied is True

    def test_converts_texture2D_call(self):
        """texture2D(iChannel0, uv) -> iChannel0.eval(uv)."""
        glsl = "fragColor = texture2D(iChannel0, uv);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert "texture2D(" not in result
        assert applied is True

    def test_converts_texture2D_with_lod(self):
        """texture2D(iChannel0, uv, lod) -> iChannel0.eval(uv), LOD dropped."""
        glsl = "fragColor = texture2D(iChannel0, uv, 0.0);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert "texture2D(" not in result
        assert applied is True

    def test_auto_injects_missing_uniform_shader_declaration(self):
        """When texture(iChannel0, uv) is called without a declaration, one is injected."""
        glsl = "fragColor = texture(iChannel0, uv);"
        result, applied = convert_textures(glsl)
        assert "uniform shader iChannel0;" in result
        assert "iChannel0.eval(uv)" in result
        assert applied is True

    def test_does_not_duplicate_existing_shader_declaration(self):
        """If uniform shader iChannel0 already exists, do not inject again."""
        glsl = "uniform shader iChannel0;\nfragColor = iChannel0.eval(uv);"
        result, applied = convert_textures(glsl)
        assert result.count("uniform shader iChannel0;") == 1

    def test_auto_injects_multiple_channels(self):
        """Multiple missing channel declarations are all injected."""
        glsl = "vec4 c0 = texture(iChannel0, uv);\nvec4 c1 = texture(iChannel1, uv);"
        result, applied = convert_textures(glsl)
        assert "uniform shader iChannel0;" in result
        assert "uniform shader iChannel1;" in result
        assert "iChannel0.eval(uv)" in result
        assert "iChannel1.eval(uv)" in result
        assert applied is True

    def test_auto_injects_for_texture2D(self):
        """texture2D calls also trigger auto-injection of uniform shader declarations."""
        glsl = "fragColor = texture2D(iChannel2, uv);"
        result, applied = convert_textures(glsl)
        assert "uniform shader iChannel2;" in result
        assert "iChannel2.eval(uv)" in result
        assert applied is True
