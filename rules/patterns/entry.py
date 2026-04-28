"""Entry pattern: convert Shadertoy mainImage to AGSL main.

Shadertoy:
    void mainImage(out vec4 fragColor, in vec2 fragCoord) { ... }

AGSL:
    half4 main(float2 fragCoord) { ... return ...; }
"""
import re


# Matches the full mainImage signature including optional newlines inside parens.
_MAIN_IMAGE_SIG_RE = re.compile(
    r"void\s+mainImage\s*\(\s*out\s+vec4\s+fragColor\s*,\s*in\s+vec2\s+fragCoord\s*\)",
    re.DOTALL,
)

# Matches standalone `fragColor = <expr>;` assignments (no swizzle on LHS).
_FRAG_COLOR_ASSIGN_RE = re.compile(
    r"^\s*fragColor\s*=\s*(.+;)\s*$",
    re.MULTILINE,
)


def convert_entry(source: str) -> tuple[str, bool]:
    """Convert mainImage signature and fragColor assignments.

    Args:
        source: GLSL source code string.

    Returns:
        Tuple of (converted source, whether conversion was applied).
    """
    if not _MAIN_IMAGE_SIG_RE.search(source):
        return source, False

    # Replace the signature.
    converted = _MAIN_IMAGE_SIG_RE.sub(
        "half4 main(float2 fragCoord)",
        source,
    )

    # Replace direct fragColor assignments with return statements.
    converted = _FRAG_COLOR_ASSIGN_RE.sub(
        lambda m: m.group(0).replace("fragColor = ", "return ", 1),
        converted,
    )

    return converted, True
