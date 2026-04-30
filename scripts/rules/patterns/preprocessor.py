"""Preprocessor pattern: convert #define macros to const declarations.

Shadertoy:
    #define PI 3.14159
    #define MAX_STEPS 64

AGSL:
    const half PI = 3.14159;
    const int MAX_STEPS = 64;

AGSL does not support GLSL preprocessor directives. #define value macros
are converted to const variables. Macro functions and multi-line macros
are left for AI fallback.
"""
import re


# Match simple `#define NAME value` (no parentheses = not a macro function).
# Captures: (1) name, (2) value.
_SIMPLE_DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)\s+(.+?)\s*$", re.MULTILINE)

# Match integer literal (optional negative sign).
_INT_LITERAL_RE = re.compile(r"^-?\d+$")

# Match GLSL vector/matrix constructors to infer the correct type.
_CONSTRUCTOR_TYPE_RE = re.compile(r"^(vec[234]|mat[234]|ivec[234]|bvec[234])\s*\(")

# Map GLSL constructor names to AGSL types.
_CONSTRUCTOR_TYPE_MAP: dict[str, str] = {
    "vec2": "float2", "vec3": "float3", "vec4": "float4",
    "mat2": "float2x2", "mat3": "float3x3", "mat4": "float4x4",
    "ivec2": "int2", "ivec3": "int3", "ivec4": "int4",
    "bvec2": "bool2", "bvec3": "bool3", "bvec4": "bool4",
}


def _infer_type(value: str) -> str:
    """Infer the AGSL type for a #define value.

    Rules:
        - Integer literal -> int
        - GLSL constructor (vec3(...), mat2(...), etc.) -> corresponding AGSL type
        - Anything else -> float
    """
    stripped = value.strip()
    if _INT_LITERAL_RE.match(stripped):
        return "int"
    # Check for GLSL vector/matrix constructors.
    m = _CONSTRUCTOR_TYPE_RE.match(stripped)
    if m:
        return _CONSTRUCTOR_TYPE_MAP.get(m.group(1), "float")
    return "float"


def convert_preprocessor(source: str) -> tuple[str, bool]:
    """Convert #define value macros to const declarations.

    Only handles simple `#define NAME value` macros (no parameters, no continuation lines).
    Multi-line macros and function macros are left unchanged for AI fallback.

    Args:
        source: GLSL source code string.

    Returns:
        Tuple of (converted source, whether any conversion was applied).
    """
    original = source

    def _replace_define(match: re.Match) -> str:
        name = match.group(1)
        value = match.group(2).strip()

        # Skip if the value line ends with backslash (multi-line macro).
        if value.endswith("\\"):
            return match.group(0)

        # Skip if name contains parentheses (function-like macro).
        if "(" in name:
            return match.group(0)

        type_name = _infer_type(value)
        return f"const {type_name} {name} = {value};"

    result = _SIMPLE_DEFINE_RE.sub(_replace_define, source)
    applied = result != original
    return result, applied
