"""Rule engine: orchestrates all conversion patterns and marker scanning.

Runs the conversion pipeline in this fixed order:
    1. Preprocessor (#define to const)
    2. Entry (mainImage to main)
    3. Types (vec/mat to half)
    4. Textures (sampler2D to shader, texture() to .eval())
    5. Uniforms (inject declarations)
    6. Coordinates (Y-axis flip)
    7. Markers (scan for unhandled patterns)

Each pattern reports whether it was applied. The engine produces a
ConversionResult with the final code, markers, and a conversion report.
"""
from dataclasses import dataclass, field

from rules.patterns.preprocessor import convert_preprocessor
from rules.patterns.entry import convert_entry
from rules.patterns.types import convert_types
from rules.patterns.textures import convert_textures
from rules.patterns.uniforms import inject_uniforms
from rules.patterns.coordinates import inject_y_flip
from rules.markers import scan_markers, Marker


@dataclass
class ConversionReport:
    """Report of which rules were applied during conversion."""
    applied_rules: list[str] = field(default_factory=list)
    injected_uniforms: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    """Result of the rule engine conversion."""
    code: str
    markers: list[Marker]
    report: ConversionReport


def convert_shader(source: str) -> ConversionResult:
    """Run the full conversion pipeline on a GLSL shader source.

    Args:
        source: Shadertoy GLSL source code string.

    Returns:
        ConversionResult with converted code, markers, and report.
    """
    report = ConversionReport()
    code = source

    # 1. Preprocessor: #define to const
    code, applied = convert_preprocessor(code)
    if applied:
        report.applied_rules.append("preprocessor")

    # 2. Entry: mainImage to main
    code, applied = convert_entry(code)
    if applied:
        report.applied_rules.append("entry")

    # 3. Types: vec/mat to half
    code, applied = convert_types(code)
    if applied:
        report.applied_rules.append("types")

    # 4. Textures: sampler2D to shader, texture() to .eval()
    code, applied = convert_textures(code)
    if applied:
        report.applied_rules.append("textures")

    # 5. Uniforms: inject declarations
    code, injected = inject_uniforms(code)
    if injected:
        report.applied_rules.append("uniforms")
        report.injected_uniforms = injected

    # 6. Coordinates: Y-axis flip
    code, applied = inject_y_flip(code)
    if applied:
        report.applied_rules.append("coordinates")

    # 7. Markers: scan for unhandled patterns
    markers = scan_markers(code)

    return ConversionResult(
        code=code,
        markers=markers,
        report=report,
    )
