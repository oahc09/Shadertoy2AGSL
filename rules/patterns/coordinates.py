"""Coordinates pattern: inject Y-axis flip at the start of main().

AGSL has Y=0 at top-left (screen coordinates).
Shadertoy (GLSL) has Y=0 at bottom-left.
To match Shadertoy behavior, we inject:
    fragCoord.y = iResolution.y - fragCoord.y;
at the beginning of the main function body.
"""
import re


# Match the main function opening brace.
# Handles both `main(...) {` and `main(...)\n{`.
_MAIN_OPEN_BRACE_RE = re.compile(
    r"(half4\s+main\s*\([^)]*\)\s*\{)",
    re.DOTALL,
)

# The Y-flip statement.
_Y_FLIP_LINE = "    fragCoord.y = iResolution.y - fragCoord.y;"


def inject_y_flip(source: str) -> tuple[str, bool]:
    """Inject Y-axis flip at the start of the main function body.

    Args:
        source: AGSL source code string (must have main() already converted).

    Returns:
        Tuple of (source with Y-flip injected, whether injection was applied).
    """
    # Check if Y-flip is already present.
    if "fragCoord.y = iResolution.y - fragCoord.y" in source:
        return source, False

    # Find the main function opening brace.
    match = _MAIN_OPEN_BRACE_RE.search(source)
    if not match:
        return source, False

    # Insert Y-flip after the opening brace.
    insert_pos = match.end()
    result = source[:insert_pos] + "\n" + _Y_FLIP_LINE + source[insert_pos:]

    return result, True
