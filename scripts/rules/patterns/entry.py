"""Entry pattern: convert Shadertoy mainImage to AGSL main.

Shadertoy:
    void mainImage(out vec4 fragColor, in vec2 fragCoord) { ... }
    void mainImage(out vec4 O, vec2 I) { ... }

AGSL:
    float4 main(float2 fragCoord) { ... return ...; }
"""
import re


# Matches mainImage signature with any parameter names.
# Groups: (1) output param name, (2) coord param name
_MAIN_IMAGE_SIG_RE = re.compile(
    r"void\s+mainImage\s*\(\s*out\s+vec4\s+(\w+)\s*,\s*(?:in\s+)?vec2\s+(\w+)\s*\)",
    re.DOTALL,
)


def convert_entry(source: str) -> tuple[str, bool]:
    """Convert mainImage signature and output variable assignments.

    Args:
        source: GLSL source code string.

    Returns:
        Tuple of (converted source, whether conversion was applied).
    """
    match = _MAIN_IMAGE_SIG_RE.search(source)
    if not match:
        return source, False

    out_name = match.group(1)  # e.g. "fragColor" or "O"
    coord_name = match.group(2)  # e.g. "fragCoord" or "I"

    # Replace the signature.
    converted = _MAIN_IMAGE_SIG_RE.sub(
        "float4 main(float2 fragCoord)",
        source,
    )

    # Replace the coord parameter name if non-standard.
    if coord_name != "fragCoord":
        # Use word-boundary replacement to avoid partial matches.
        converted = re.sub(r"\b" + re.escape(coord_name) + r"\b", "fragCoord", converted)

    # Replace direct output assignments with return statements.
    # Match `outName = <expr>;` but not `outName.rgb = ...` (swizzle assignments).
    assign_re = re.compile(
        r"^\s*" + re.escape(out_name) + r"\s*=\s*(.+;)\s*$",
        re.MULTILINE,
    )
    converted = assign_re.sub(
        lambda m: m.group(0).replace(f"{out_name} = ", "return ", 1),
        converted,
    )

    return converted, True
