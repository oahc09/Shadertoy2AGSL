"""Top-level converter: rule engine + AI fallback orchestration.

This is the main entry point called by the Claude Code skill. It:
    1. Runs the rule engine to produce AGSL code
    2. Checks if AI fallback is needed (markers present)
    3. Produces a structured ConverterOutput for the skill to consume

Usage:
    from converter import convert, needs_ai_fallback

    output = convert(glsl_source)
    if output.needs_ai_fallback:
        # Pass output.unhandled_fragments to Claude for AI conversion
        ...
"""
from dataclasses import dataclass, field

from scripts.rules.engine import convert_shader


@dataclass
class ConverterOutput:
    """Structured output from the converter for the Claude Code skill."""
    agsl_code: str
    original_source: str
    needs_ai_fallback: bool
    unhandled_fragments: list[dict]
    report: dict


def convert(source: str) -> ConverterOutput:
    """Convert a Shadertoy GLSL shader to AGSL.

    Args:
        source: Shadertoy GLSL source code string.

    Returns:
        ConverterOutput with AGSL code, markers, and report.
    """
    result = convert_shader(source)

    # Convert Marker objects to dicts for serialization.
    unhandled_fragments = [
        {
            "kind": m.kind,
            "line": m.line,
            "snippet": m.snippet,
            "description": m.description,
        }
        for m in result.markers
    ]

    return ConverterOutput(
        agsl_code=result.code,
        original_source=source,
        needs_ai_fallback=len(result.markers) > 0,
        unhandled_fragments=unhandled_fragments,
        report={
            "applied_rules": result.report.applied_rules,
            "injected_uniforms": result.report.injected_uniforms,
            "warnings": result.report.warnings,
        },
    )


def needs_ai_fallback(source: str) -> bool:
    """Check if a source string contains patterns needing AI fallback.

    This is a quick check that can be used before running the full converter.

    Args:
        source: AGSL or GLSL source code string.

    Returns:
        True if AI fallback is needed.
    """
    from scripts.rules.markers import scan_markers
    return len(scan_markers(source)) > 0
