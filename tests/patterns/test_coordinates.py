"""Tests for the coordinates pattern: Y-axis flip injection."""
import pytest
from scripts.rules.patterns.coordinates import inject_y_flip


class TestInjectYFlip:
    """Test suite for Y-axis coordinate flip injection."""

    def test_injects_y_flip_at_main_opening_brace(self):
        """Y-flip is injected after the opening brace of main()."""
        agsl = (
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    float2 uv = fragCoord / iResolution;\n"
            "    return float4(uv, 0.0, 1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result
        lines = result.split("\n")
        brace_line_idx = next(i for i, l in enumerate(lines) if "{" in l)
        flip_line_idx = next(
            i for i, l in enumerate(lines)
            if "fragCoord.y = iResolution.y - fragCoord.y" in l
        )
        assert flip_line_idx == brace_line_idx + 1
        assert applied is True

    def test_injects_y_flip_with_indented_brace(self):
        """Y-flip is injected even when opening brace is on the same line."""
        agsl = "float4 main(float2 fragCoord) {\n    return float4(1.0);\n}"
        result, applied = inject_y_flip(agsl)
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result
        assert applied is True

    def test_does_not_inject_if_already_present(self):
        """If Y-flip already exists, it is not injected again."""
        agsl = (
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    fragCoord.y = iResolution.y - fragCoord.y;\n"
            "    return float4(1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        assert result.count("fragCoord.y = iResolution.y - fragCoord.y;") == 1
        assert applied is False

    def test_no_main_function_returns_unchanged(self):
        """If no main() function found, input is returned unchanged."""
        agsl = "float helper(float x) { return x; }"
        result, applied = inject_y_flip(agsl)
        assert result == agsl
        assert applied is False

    def test_injects_with_existing_comments(self):
        """Y-flip is injected correctly even when main has a leading comment."""
        agsl = (
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    // begin shader\n"
            "    return float4(1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result
        assert applied is True

    def test_preserves_indentation(self):
        """Injected line uses 4-space indentation matching the function body."""
        agsl = (
            "float4 main(float2 fragCoord)\n"
            "{\n"
            "    return float4(1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        lines = result.split("\n")
        flip_line = next(l for l in lines if "fragCoord.y = iResolution.y" in l)
        assert flip_line.startswith("    ")
