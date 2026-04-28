"""Tests for the types pattern: GLSL → AGSL type conversion."""
import pytest
from rules.patterns.types import convert_types


class TestConvertTypes:
    """Test suite for type conversion."""

    def test_converts_vec2(self):
        """vec2 → half2."""
        glsl = "vec2 uv = fragCoord / iResolution.xy;"
        result, applied = convert_types(glsl)
        assert "half2 uv" in result
        assert "vec2" not in result
        assert applied is True

    def test_converts_vec3(self):
        """vec3 → half3."""
        glsl = "vec3 color = vec3(1.0, 0.0, 0.0);"
        result, applied = convert_types(glsl)
        assert "half3 color" in result
        assert "half3(" in result
        assert "vec3" not in result
        assert applied is True

    def test_converts_vec4(self):
        """vec4 → half4."""
        glsl = "return vec4(uv, 0.0, 1.0);"
        result, applied = convert_types(glsl)
        assert "half4(" in result
        assert "vec4" not in result
        assert applied is True

    def test_converts_mat2(self):
        """mat2 → half2x2."""
        glsl = "mat2 rot = mat2(cos(t), -sin(t), sin(t), cos(t));"
        result, applied = convert_types(glsl)
        assert "half2x2 rot" in result
        assert "half2x2(" in result
        assert "mat2" not in result
        assert applied is True

    def test_converts_mat3(self):
        """mat3 → half3x3."""
        glsl = "mat3 m = mat3(1.0);"
        result, applied = convert_types(glsl)
        assert "half3x3 m" in result
        assert "half3x3(" in result
        assert "mat3" not in result
        assert applied is True

    def test_converts_mat4(self):
        """mat4 → half4x4."""
        glsl = "mat4 m = mat4(1.0);"
        result, applied = convert_types(glsl)
        assert "half4x4 m" in result
        assert "half4x4(" in result
        assert "mat4" not in result
        assert applied is True

    def test_converts_standalone_float_to_half(self):
        """Standalone `float` type → `half` (not float2/float3/float4)."""
        glsl = "float t = iTime * 2.0;"
        result, applied = convert_types(glsl)
        assert "half t" in result
        assert "float " not in result
        assert applied is True

    def test_does_not_convert_float2(self):
        """float2 should NOT be converted (it's already AGSL-compatible)."""
        glsl = "float2 uv = fragCoord / iResolution;"
        result, applied = convert_types(glsl)
        assert "float2" in result

    def test_converts_ivec2(self):
        """ivec2 → int2."""
        glsl = "ivec2 p = ivec2(1, 2);"
        result, applied = convert_types(glsl)
        assert "int2 p" in result
        assert "int2(" in result
        assert "ivec2" not in result
        assert applied is True

    def test_converts_bvec2(self):
        """bvec2 → bool2."""
        glsl = "bvec2 mask = bvec2(true, false);"
        result, applied = convert_types(glsl)
        assert "bool2 mask" in result
        assert "bool2(" in result
        assert "bvec2" not in result
        assert applied is True

    def test_no_types_returns_unchanged(self):
        """If no GLSL types found, input is returned unchanged."""
        glsl = "return half4(1.0);"
        result, applied = convert_types(glsl)
        assert result == glsl
        assert applied is False

    def test_converts_multiple_types_on_one_line(self):
        """Multiple type conversions on the same line all succeed."""
        glsl = "vec4 color = vec4(vec3(1.0), 1.0);"
        result, applied = convert_types(glsl)
        assert "half4 color = half4(half3(1.0), 1.0);" in result
        assert applied is True

    def test_converts_void_parameter_out_vec4(self):
        """out vec4 in function parameters is converted."""
        glsl = "void foo(out vec4 color) { color = vec4(1.0); }"
        result, applied = convert_types(glsl)
        assert "out half4 color" in result
        assert "half4(1.0)" in result
        assert applied is True
