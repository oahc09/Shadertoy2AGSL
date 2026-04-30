"""Markers: detect unhandled GLSL patterns that require AI fallback.

Scans the source for patterns the rule engine cannot convert:
    - discard statements (not supported in AGSL)
    - Multi-dimensional arrays (AGSL only supports 1D)
    - Recursive function calls (not supported in AGSL)

Returns a list of Marker objects with location info and snippets.
"""
import re
from dataclasses import dataclass


@dataclass
class Marker:
    """Represents an unhandled code fragment detected during conversion."""
    kind: str        # "discard", "multi_dim_array", "recursion"
    line: int        # 1-based line number
    snippet: str     # The relevant source line(s)
    description: str # Human-readable description of the issue


# Match `discard` as a standalone statement, not inside comments or strings.
_DISCARD_RE = re.compile(r"\bdiscard\b")

# Match multi-dimensional array declarations: type name[dim1][dim2]
_MULTI_DIM_ARRAY_RE = re.compile(r"\w+\s+\w+\s*\[\s*\d+\s*\]\s*\[\s*\d+\s*\]")

# Match single-line comments.
_SINGLE_LINE_COMMENT_RE = re.compile(r"//.*$", re.MULTILINE)

# Match multi-line comments.
_MULTI_LINE_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

# Match string literals.
_STRING_LITERAL_RE = re.compile(r'"[^"]*"')


def _strip_comments_and_strings(source: str) -> str:
    """Replace comments and string literals with whitespace to avoid false matches."""
    result = _MULTI_LINE_COMMENT_RE.sub(lambda m: " " * len(m.group(0)), source)
    result = _SINGLE_LINE_COMMENT_RE.sub(lambda m: " " * len(m.group(0)), result)
    result = _STRING_LITERAL_RE.sub(lambda m: " " * len(m.group(0)), result)
    return result


def _get_line_number(source: str, pos: int) -> int:
    """Get 1-based line number for a position in source."""
    return source[:pos].count("\n") + 1


def _get_line_content(source: str, line_num: int) -> str:
    """Get the content of a specific line (1-based)."""
    lines = source.split("\n")
    if 1 <= line_num <= len(lines):
        return lines[line_num - 1].strip()
    return ""


def _detect_discard(source: str, cleaned: str) -> list[Marker]:
    """Detect discard statements."""
    markers = []
    for match in _DISCARD_RE.finditer(cleaned):
        line = _get_line_number(source, match.start())
        snippet = _get_line_content(source, line)
        markers.append(Marker(
            kind="discard",
            line=line,
            snippet=snippet,
            description="AGSL does not support 'discard'. Must rewrite as conditional return.",
        ))
    return markers


def _detect_multi_dim_arrays(source: str, cleaned: str) -> list[Marker]:
    """Detect multi-dimensional array declarations."""
    markers = []
    for match in _MULTI_DIM_ARRAY_RE.finditer(cleaned):
        line = _get_line_number(source, match.start())
        snippet = _get_line_content(source, line)
        markers.append(Marker(
            kind="multi_dim_array",
            line=line,
            snippet=snippet,
            description="AGSL only supports 1-dimensional arrays. Multi-dimensional arrays must be flattened.",
        ))
    return markers


def _detect_recursion(source: str, cleaned: str) -> list[Marker]:
    """Detect recursive function calls.

    Strategy: find all function definitions, then check if any function
    calls itself within its own body.
    """
    markers = []

    # Find function definitions and their bodies.
    lines = cleaned.split("\n")
    in_function = False
    func_name = ""
    brace_depth = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect function definition (simplistic: word followed by parenthesis with type before it).
        if not in_function:
            # Look for pattern: type name(...) {
            func_match = re.match(r"^(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{?", stripped)
            if func_match and not stripped.startswith(("if", "for", "while", "switch", "return")):
                candidate_name = func_match.group(1)
                # Skip built-in and main.
                if candidate_name not in ("main", "if", "for", "while"):
                    in_function = True
                    func_name = candidate_name
                    brace_depth = stripped.count("{") - stripped.count("}")
                    continue

        if in_function:
            brace_depth += stripped.count("{") - stripped.count("}")

            # Check for recursive call.
            call_pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
            if call_pattern.search(stripped):
                markers.append(Marker(
                    kind="recursion",
                    line=i + 1,
                    snippet=stripped,
                    description=f"Recursive call to '{func_name}()' detected. AGSL does not support recursion.",
                ))

            if brace_depth <= 0:
                in_function = False
                func_name = ""

    return markers


def scan_markers(source: str) -> list[Marker]:
    """Scan source for unhandled patterns requiring AI fallback.

    Args:
        source: AGSL source code string.

    Returns:
        List of Marker objects describing each unhandled pattern found.
    """
    cleaned = _strip_comments_and_strings(source)
    markers: list[Marker] = []
    markers.extend(_detect_discard(source, cleaned))
    markers.extend(_detect_multi_dim_arrays(source, cleaned))
    markers.extend(_detect_recursion(source, cleaned))
    # Sort by line number.
    markers.sort(key=lambda m: m.line)
    return markers
