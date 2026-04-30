"""Types pattern: convert GLSL type names to AGSL type names.

Conversion table:
    vec2 → float2, vec3 → float3, vec4 → float4
    mat2 → float2x2, mat3 → float3x3, mat4 → float4x4
    ivec2 → int2, ivec3 → int3, ivec4 → int4
    bvec2 → bool2, bvec3 → bool3, bvec4 → bool4
    float (standalone) → float (no change)

We use float (not half) for intermediate calculations to avoid precision loss
in iterative shaders. AGSL supports both float and half; half is only faster
on some mobile GPUs but causes visible artifacts in loops.
"""
import re


# Ordered longest-first to avoid partial matches.
_TYPE_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\bvec4\b", "float4"),
    (r"\bvec3\b", "float3"),
    (r"\bvec2\b", "float2"),
    (r"\bmat4\b", "float4x4"),
    (r"\bmat3\b", "float3x3"),
    (r"\bmat2\b", "float2x2"),
    (r"\bivec4\b", "int4"),
    (r"\bivec3\b", "int3"),
    (r"\bivec2\b", "int2"),
    (r"\bbvec4\b", "bool4"),
    (r"\bbvec3\b", "bool3"),
    (r"\bbvec2\b", "bool2"),
]

# Match const declarations with type mismatch after vec/mat conversion.
# e.g., "const float ACCENT = float3(..." should be "const float3 ACCENT = float3(..."
_CONST_TYPE_MISMATCH_RE = re.compile(
    r"const\s+float\s+(\w+)\s*=\s*(float[234]|float[234]x[234]|int[234]|bool[234])\s*\("
)

# Map initializer constructor to correct const type.
_INIT_TYPE_MAP: dict[str, str] = {
    "float2": "float2", "float3": "float3", "float4": "float4",
    "float2x2": "float2x2", "float3x3": "float3x3", "float4x4": "float4x4",
    "int2": "int2", "int3": "int3", "int4": "int4",
    "bool2": "bool2", "bool3": "bool3", "bool4": "bool4",
}


def _fix_const_type_mismatches(source: str) -> str:
    """Fix const declarations where type doesn't match initializer.

    After vec/mat conversion, a #define like:
        #define ACCENT vec3(0.5, 0.2, 0.8)
    may have been converted to:
        const float ACCENT = float3(0.5, 0.2, 0.8);
    This fixes it to:
        const float3 ACCENT = float3(0.5, 0.2, 0.8);
    """
    def _fix_match(m: re.Match) -> str:
        name = m.group(1)
        init_type = m.group(2)
        correct_type = _INIT_TYPE_MAP.get(init_type, "float")
        return f"const {correct_type} {name} = {init_type}("
    return _CONST_TYPE_MISMATCH_RE.sub(_fix_match, source)


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

    # Convert integer modulo operator (%) to mod() — AGSL does not support % on int.
    # Pattern 1: identifier % integer_literal (e.g., VARIANT % 3)
    result = re.sub(
        r"\b(\w+)\s*%\s*(\d+)",
        r"mod(float(\1), float(\2))",
        result,
    )
    # Pattern 2: identifier % identifier (e.g., a % b)
    result = re.sub(
        r"\b(\w+)\s*%\s*(\w+)",
        r"mod(float(\1), float(\2))",
        result,
    )

    # Fix const type mismatches caused by constructor conversion.
    result = _fix_const_type_mismatches(result)

    applied = result != original
    return result, applied
