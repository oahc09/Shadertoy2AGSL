"""Tests for the markers module: detect unhandled patterns for AI fallback."""
import pytest
from scripts.rules.markers import scan_markers, Marker


class TestScanMarkers:
    """Test suite for unhandled pattern detection."""

    def test_detects_discard_statement(self):
        """'discard' statements are detected as unhandled."""
        source = (
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    if (fragCoord.x < 0.0) discard;\n"
            "    return float4(1.0);\n"
            "}"
        )
        markers = scan_markers(source)
        assert len(markers) == 1
        assert markers[0].kind == "discard"
        assert markers[0].line == 3

    def test_detects_multi_dimensional_array(self):
        """Multi-dimensional array declarations are detected as unhandled."""
        source = "float arr[4][4];"
        markers = scan_markers(source)
        assert len(markers) == 1
        assert markers[0].kind == "multi_dim_array"

    def test_detects_2d_array(self):
        """2D array like float data[3][3] is detected."""
        source = "float data[3][3];"
        markers = scan_markers(source)
        assert len(markers) == 1
        assert markers[0].kind == "multi_dim_array"

    def test_detects_recursive_function(self):
        """Functions that call themselves are detected as recursive."""
        source = (
            "float fib(float n) {\n"
            "    if (n <= 1.0) return n;\n"
            "    return fib(n - 1.0) + fib(n - 2.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        recursion_markers = [m for m in markers if m.kind == "recursion"]
        assert len(recursion_markers) >= 1

    def test_no_markers_for_clean_code(self):
        """Clean AGSL code produces no markers."""
        source = (
            "uniform float3 iResolution;\n"
            "uniform float iTime;\n"
            "\n"
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    fragCoord.y = iResolution.y - fragCoord.y;\n"
            "    float2 uv = fragCoord / iResolution;\n"
            "    return float4(uv, 0.0, 1.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        assert len(markers) == 0

    def test_detects_discard_in_nested_block(self):
        """discard inside nested if/for is detected."""
        source = (
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    for (int i = 0; i < 10; i++) {\n"
            "        if (i > 5) discard;\n"
            "    }\n"
            "    return float4(1.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        discard_markers = [m for m in markers if m.kind == "discard"]
        assert len(discard_markers) == 1

    def test_detects_multiple_issues(self):
        """Multiple unhandled patterns in one shader are all detected."""
        source = (
            "float matrix[4][4];\n"
            "\n"
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    if (fragCoord.x < 0.0) discard;\n"
            "    return float4(1.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        kinds = {m.kind for m in markers}
        assert "discard" in kinds
        assert "multi_dim_array" in kinds

    def test_marker_has_source_snippet(self):
        """Each marker includes the relevant source snippet."""
        source = "if (x < 0.0) discard;\n"
        markers = scan_markers(source)
        assert len(markers) == 1
        assert "discard" in markers[0].snippet

    def test_ignores_discard_in_comments(self):
        """'discard' inside comments is not flagged."""
        source = "// this shader uses discard\nreturn float4(1.0);\n"
        markers = scan_markers(source)
        discard_markers = [m for m in markers if m.kind == "discard"]
        assert len(discard_markers) == 0

    def test_ignores_discard_in_strings(self):
        """'discard' inside string literals is not flagged."""
        source = 'return float4(1.0); // "discard"\n'
        markers = scan_markers(source)
        discard_markers = [m for m in markers if m.kind == "discard"]
        assert len(discard_markers) == 0

    def test_detects_textureLod(self):
        """textureLod() calls are detected as unhandled."""
        source = "half4 c = textureLod(iChannel0, uv, 2.0);"
        markers = scan_markers(source)
        assert any(m.kind == "texture_lod" for m in markers)

    def test_detects_textureSize(self):
        """textureSize() calls are detected as unhandled."""
        source = "vec2 size = textureSize(iChannel0, 0);"
        markers = scan_markers(source)
        assert any(m.kind == "texture_size" for m in markers)

    def test_detects_texelFetch(self):
        """texelFetch() calls are detected as unhandled."""
        source = "vec4 texel = texelFetch(iChannel0, ivec2(0,0), 0);"
        markers = scan_markers(source)
        assert any(m.kind == "texel_fetch" for m in markers)

    def test_ignores_texture_funcs_in_comments(self):
        """texture functions inside comments are not flagged."""
        source = "// uses textureLod and textureSize\nfloat4 main() { return float4(1.0); }\n"
        markers = scan_markers(source)
        texture_markers = [m for m in markers if m.kind.startswith("texture_")]
        assert len(texture_markers) == 0
