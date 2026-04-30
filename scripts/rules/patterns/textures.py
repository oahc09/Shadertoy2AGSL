"""Textures pattern: convert GLSL texture sampling to AGSL shader evaluation.

Shadertoy:
    uniform sampler2D iChannel0;
    fragColor = texture(iChannel0, uv);

AGSL:
    uniform shader iChannel0;
    iChannel0.eval(uv);
"""
import re


# Match `uniform sampler2D <name>;` declarations.
_SAMPLER2D_DECL_RE = re.compile(r"\buniform\s+sampler2D\b")

# Match `texture(<channel>, <coord>[, <lod>])` calls.
# Group 1: channel name (iChannel0..3)
# Group 2: coordinate expression
# Group 3: optional LOD (ignored in AGSL)
_TEXTURE_CALL_RE = re.compile(
    r"\btexture\s*\(\s*(iChannel\d)\s*,\s*([^,)]+?)(?:\s*,\s*[^)]+?)?\s*\)"
)


def _convert_texture_calls_in_line(line: str) -> str:
    """Convert texture() calls in a single line, skipping comments."""
    comment_idx = line.find("//")
    if comment_idx == -1:
        # No comment — convert the whole line.
        return _TEXTURE_CALL_RE.sub(
            lambda m: f"{m.group(1)}.eval({m.group(2).strip()})",
            line,
        )
    # Split into code and comment; only convert the code part.
    code_part = line[:comment_idx]
    comment_part = line[comment_idx:]
    code_part = _TEXTURE_CALL_RE.sub(
        lambda m: f"{m.group(1)}.eval({m.group(2).strip()})",
        code_part,
    )
    return code_part + comment_part


def convert_textures(source: str) -> tuple[str, bool]:
    """Convert GLSL texture sampling to AGSL shader evaluation.

    Args:
        source: GLSL source code string.

    Returns:
        Tuple of (converted source, whether any conversion was applied).
    """
    original = source
    result = source

    # Convert declarations: sampler2D → shader.
    result = _SAMPLER2D_DECL_RE.sub("uniform shader", result)

    # Convert texture() calls → .eval() (line by line to skip comments).
    result = "\n".join(
        _convert_texture_calls_in_line(line)
        for line in result.split("\n")
    )

    applied = result != original
    return result, applied
