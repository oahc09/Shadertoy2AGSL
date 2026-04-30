"""Coordinates pattern: inject Y-axis flip and propagate fragCoord.

AGSL has Y=0 at top-left (screen coordinates).
Shadertoy (GLSL) has Y=0 at bottom-left.
To match Shadertoy behavior, we inject:
    fragCoord.y = iResolution.y - fragCoord.y;
at the beginning of the main function body.

Also propagates fragCoord as a parameter to helper functions that use it,
since gl_FragCoord is a global in GLSL but fragCoord is only a main() parameter in AGSL.
"""
import re


# Match the main function opening brace.
# Handles both `main(...) {` and `main(...)\n{`.
_MAIN_OPEN_BRACE_RE = re.compile(
    r"((?:half4|float4)\s+main\s*\([^)]*\)\s*\{)",
    re.DOTALL,
)

# The Y-flip statement.
_Y_FLIP_LINE = "    fragCoord.y = iResolution.y - fragCoord.y;"

# Match function definitions: returnType funcName(params) {
_FUNC_DEF_RE = re.compile(
    r"([\w]+)\s+([\w]+)\s*\(([^)]*)\)\s*\{",
)


def _extract_function_bodies(source: str) -> dict[str, tuple[str, int, int]]:
    """Extract function names, bodies, and parameter lists from source.

    Returns dict of {func_name: (params, body_start, body_end)}.
    """
    functions = {}
    for m in _FUNC_DEF_RE.finditer(source):
        ret_type = m.group(1)
        func_name = m.group(2)
        params = m.group(3)
        # Find matching closing brace
        start = m.end()
        depth = 1
        pos = start
        while pos < len(source) and depth > 0:
            if source[pos] == '{':
                depth += 1
            elif source[pos] == '}':
                depth -= 1
            pos += 1
        functions[func_name] = (params, start, pos)
    return functions


def _propagate_fragcoord(source: str) -> str:
    """Add float2 fragCoord parameter to helper functions that use it.

    Iteratively finds functions using fragCoord (other than main),
    adds the parameter, and updates call sites until stable.
    """
    for _ in range(10):  # max iterations to handle call chains
        functions = _extract_function_bodies(source)
        changed = False

        for func_name, (params, body_start, body_end) in functions.items():
            if func_name == "main":
                continue
            # Check if fragCoord already in params
            if "fragCoord" in params:
                continue
            # Check if fragCoord is used in the body
            body = source[body_start:body_end]
            if "fragCoord" not in body:
                continue

            # Add fragCoord parameter
            new_params = params.rstrip()
            if new_params:
                new_params += ", float2 fragCoord"
            else:
                new_params = "float2 fragCoord"

            # Replace the function signature
            old_sig = f"{func_name}({params})"
            new_sig = f"{func_name}({new_params})"
            source = source.replace(old_sig, new_sig, 1)

            # Update all call sites to pass fragCoord
            # Match funcName(args) but not the definition
            call_re = re.compile(r"\b" + re.escape(func_name) + r"\s*\(([^)]*)\)")
            for cm in list(call_re.finditer(source)):
                call_args = cm.group(1).strip()
                # Skip if it's the definition (has float2 fragCoord)
                if "float2 fragCoord" in call_args:
                    continue
                # Skip if fragCoord already passed
                if "fragCoord" in call_args and call_args.count("fragCoord") > 0:
                    # Could be a false positive from a different variable
                    pass
                # Add fragCoord to the call
                if call_args:
                    new_call = f"{func_name}({call_args}, fragCoord)"
                else:
                    new_call = f"{func_name}(fragCoord)"
                old_call = cm.group(0)
                if old_call != new_call:
                    source = source.replace(old_call, new_call, 1)

            changed = True
            break  # restart iteration after modification

        if not changed:
            break

    return source


def inject_y_flip(source: str) -> tuple[str, bool]:
    """Inject Y-axis flip at the start of the main function body.

    Args:
        source: AGSL source code string (must have main() already converted).

    Returns:
        Tuple of (source with Y-flip injected, whether injection was applied).
    """
    original = source

    # Replace gl_FragCoord with fragCoord — AGSL uses fragCoord parameter, not gl_FragCoord.
    source = source.replace("gl_FragCoord", "fragCoord")

    # Propagate fragCoord to helper functions that use it.
    source = _propagate_fragcoord(source)

    # Check if Y-flip is already present.
    if "fragCoord.y = iResolution.y - fragCoord.y" in source:
        return source, source != original

    # Find the main function opening brace.
    match = _MAIN_OPEN_BRACE_RE.search(source)
    if not match:
        return source, False

    # Insert Y-flip after the opening brace.
    insert_pos = match.end()
    result = source[:insert_pos] + "\n" + _Y_FLIP_LINE + source[insert_pos:]

    return result, True
