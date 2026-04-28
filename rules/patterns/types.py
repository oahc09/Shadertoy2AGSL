"""Types pattern: convert GLSL type names to AGSL type names.

Conversion table:
    vec2 → half2, vec3 → half3, vec4 → half4
    mat2 → half2x2, mat3 → half3x3, mat4 → half4x4
    ivec2 → int2, ivec3 → int3, ivec4 → int4
    bvec2 → bool2, bvec3 → bool3, bvec4 → bool4
    float (standalone) → half
"""
import re


# Ordered longest-first to avoid partial matches.
_TYPE_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\bvec4\b", "half4"),
    (r"\bvec3\b", "half3"),
    (r"\bvec2\b", "half2"),
    (r"\bmat4\b", "half4x4"),
    (r"\bmat3\b", "half3x3"),
    (r"\bmat2\b", "half2x2"),
    (r"\bivec4\b", "int4"),
    (r"\bivec3\b", "int3"),
    (r"\bivec2\b", "int2"),
    (r"\bbvec4\b", "bool4"),
    (r"\bbvec3\b", "bool3"),
    (r"\bbvec2\b", "bool2"),
]

# Standalone float → half. Negative lookahead to avoid float2, float3, float4, float2x2 etc.
_FLOAT_RE = re.compile(r"\bfloat\b(?![234x])")


def convert_types(source: str) -> tuple[str, bool]:
    """Convert GLSL type names to AGSL type names.

    Args:
        source: GLSL source code string.

    Returns:
        Tuple of (converted source, whether any conversion was applied).
    """
    original = source
    result = source

    # Apply vec/mat/ivec/bvec replacements.
    for pattern, replacement in _TYPE_REPLACEMENTS:
        result = re.sub(pattern, replacement, result)

    # Apply standalone float → half.
    result = _FLOAT_RE.sub("half", result)

    applied = result != original
    return result, applied
