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
_TEXTURE_CALL_RE = re.compile(
    r"\btexture\s*\(\s*(iChannel\d)\s*,\s*([^,)]+?)(?:\s*,\s*[^)]+?)?\s*\)"
)

# Match `texture2D(<channel>, <coord>[, <lod>])` calls (legacy GLSL).
_TEXTURE2D_CALL_RE = re.compile(
    r"\btexture2D\s*\(\s*(iChannel\d)\s*,\s*([^,)]+?)(?:\s*,\s*[^)]+?)?\s*\)"
)

# Detect used iChannel indices from .eval() calls.
_USED_CHANNEL_RE = re.compile(r"iChannel(\d+)\.eval\(")

# Detect existing uniform shader iChannelN declarations.
_DECLARED_CHANNEL_RE = re.compile(r"uniform\s+shader\s+iChannel(\d+)\s*;")


def _eval_sub(m: re.Match) -> str:
    """Substitution: texture call → .eval() call."""
    return f"{m.group(1)}.eval({m.group(2).strip()})"


def _convert_texture_calls_in_line(line: str) -> str:
    """Convert texture()/texture2D() calls in a single line, skipping comments."""
    comment_idx = line.find("//")
    if comment_idx == -1:
        result = _TEXTURE_CALL_RE.sub(_eval_sub, line)
        result = _TEXTURE2D_CALL_RE.sub(_eval_sub, result)
        return result
    code_part = line[:comment_idx]
    comment_part = line[comment_idx:]
    code_part = _TEXTURE_CALL_RE.sub(_eval_sub, code_part)
    code_part = _TEXTURE2D_CALL_RE.sub(_eval_sub, code_part)
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

    # Convert texture()/texture2D() calls → .eval() (line by line to skip comments).
    result = "\n".join(
        _convert_texture_calls_in_line(line)
        for line in result.split("\n")
    )

    # Auto-inject missing uniform shader iChannelN declarations.
    used_indices = set(_USED_CHANNEL_RE.findall(result))
    declared_indices = set(_DECLARED_CHANNEL_RE.findall(result))
    missing = sorted(used_indices - declared_indices)
    if missing:
        decl_block = "\n".join(f"uniform shader iChannel{i};" for i in missing) + "\n"
        result = decl_block + result

    applied = result != original
    return result, applied
