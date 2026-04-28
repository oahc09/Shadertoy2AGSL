"""Uniforms pattern: inject AGSL uniform declarations for Shadertoy built-ins.

Shadertoy auto-provides uniforms like iResolution, iTime, iMouse, etc.
AGSL requires explicit declarations. This module detects usage of these
uniforms and injects declarations at the top of the source.
"""
import re


# Map of uniform name → AGSL declaration.
UNIFORM_DECLARATIONS: dict[str, str] = {
    "iResolution": "uniform float2 iResolution;",
    "iTime": "uniform float iTime;",
    "iTimeDelta": "uniform float iTimeDelta;",
    "iFrame": "uniform float iFrame;",
    "iMouse": "uniform float4 iMouse;",
    "iDate": "uniform float4 iDate;",
    "iSampleRate": "uniform float iSampleRate;",
}

# Match uniform names as whole words (not as substrings of longer names).
_UNIFORM_WORD_RE = re.compile(
    r"\b(iResolution|iTime|iTimeDelta|iFrame|iMouse|iDate|iSampleRate)\b"
)

# Match existing uniform declarations to avoid duplicates.
_EXISTING_UNIFORM_RE = re.compile(r"^\s*uniform\s+.*;\s*$", re.MULTILINE)


def inject_uniforms(source: str) -> tuple[str, list[str]]:
    """Detect used built-in uniforms and inject AGSL declarations.

    Args:
        source: GLSL/AGSL source code string.

    Returns:
        Tuple of (source with declarations injected, list of injected uniform names).
    """
    # Find which built-in uniforms are used.
    used_names = set(_UNIFORM_WORD_RE.findall(source))
    if not used_names:
        return source, []

    # Find which are already declared.
    existing_decls = _EXISTING_UNIFORM_RE.findall(source)
    already_declared: set[str] = set()
    for decl in existing_decls:
        for name in used_names:
            if name in decl:
                already_declared.add(name)

    # Determine which need injection.
    to_inject = used_names - already_declared
    if not to_inject:
        return source, []

    # Build declaration block. Sort for deterministic output.
    decl_lines = [UNIFORM_DECLARATIONS[name] for name in sorted(to_inject)]
    decl_block = "\n".join(decl_lines) + "\n"

    # Prepend declarations to source.
    result = decl_block + source

    return result, sorted(to_inject)
