"""Tests for the preprocessor pattern: #define -> const."""
import pytest
from scripts.rules.patterns.preprocessor import convert_preprocessor


class TestConvertPreprocessor:
    """Test suite for preprocessor conversion."""

    def test_converts_float_define(self):
        """#define PI 3.14159 -> const float PI = 3.14159;"""
        glsl = "#define PI 3.14159"
        result, applied = convert_preprocessor(glsl)
        assert "const float PI = 3.14159;" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_integer_define(self):
        """#define MAX_STEPS 64 -> const int MAX_STEPS = 64;"""
        glsl = "#define MAX_STEPS 64"
        result, applied = convert_preprocessor(glsl)
        assert "const int MAX_STEPS = 64;" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_expression_define(self):
        """#define SPEED (2.0 * 3.14) -> const float SPEED = (2.0 * 3.14);"""
        glsl = "#define SPEED (2.0 * 3.14)"
        result, applied = convert_preprocessor(glsl)
        assert "const float SPEED = (2.0 * 3.14);" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_negative_define(self):
        """#define OFFSET -1.5 -> const float OFFSET = -1.5;"""
        glsl = "#define OFFSET -1.5"
        result, applied = convert_preprocessor(glsl)
        assert "const float OFFSET = -1.5;" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_multiple_defines(self):
        """Multiple #define lines are all converted."""
        glsl = (
            "#define PI 3.14159\n"
            "#define TWO_PI 6.28318\n"
            "#define MAX_STEPS 64\n"
        )
        result, applied = convert_preprocessor(glsl)
        assert "const float PI = 3.14159;" in result
        assert "const float TWO_PI = 6.28318;" in result
        assert "const int MAX_STEPS = 64;" in result
        assert "#define" not in result
        assert applied is True

    def test_no_defines_returns_unchanged(self):
        """If no #define found, input is returned unchanged."""
        glsl = "float4 main(float2 fragCoord) { return half4(1.0); }"
        result, applied = convert_preprocessor(glsl)
        assert result == glsl
        assert applied is False

    def test_leaves_ifdef_alone(self):
        """#ifdef / #ifndef / #endif are left unchanged."""
        glsl = "#ifdef FEATURE_ENABLED\nfloat x = 1.0;\n#endif"
        result, applied = convert_preprocessor(glsl)
        assert "#ifdef FEATURE_ENABLED" in result
        assert "#endif" in result

    def test_converts_define_with_vec_constructor(self):
        """#define COLOR vec3(1.0, 0.0, 0.0) -> const float3 COLOR = vec3(1.0, 0.0, 0.0);"""
        glsl = "#define COLOR vec3(1.0, 0.0, 0.0)"
        result, applied = convert_preprocessor(glsl)
        assert "const float3 COLOR = vec3(1.0, 0.0, 0.0);" in result
        assert applied is True

    def test_leaves_multiline_macros_with_backslash(self):
        """Multi-line macros with backslash continuation are left for AI fallback."""
        glsl = "#define MACRO(a, b) \\\n    do_something(a, b)"
        result, applied = convert_preprocessor(glsl)
        assert "#define" in result
