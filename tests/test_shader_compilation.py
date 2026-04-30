"""Validate converted AGSL shaders for known problematic patterns.

These tests run without an Android device. They check the AGSL code
for syntax issues that would cause RuntimeShader compilation failures.
"""
import json
import re
from pathlib import Path

import pytest

from scripts.converter import convert

CONVERTED_FILE = Path(__file__).resolve().parent.parent / "output" / "converted_shaders.json"
SHADERS_DIR = Path("D:/AI/Shadertoy/generated_shaders_100")


def _load_converted_shaders() -> list[dict]:
    """Load previously converted shaders from JSON."""
    if not CONVERTED_FILE.exists():
        pytest.skip(f"Converted shaders file not found: {CONVERTED_FILE}")
    data = json.loads(CONVERTED_FILE.read_text(encoding="utf-8"))
    return [d for d in data if d.get("agsl_code") and not d.get("needs_ai_fallback")]


def _load_glsl_shaders() -> list[tuple[str, str]]:
    """Load GLSL source files and convert them fresh."""
    if not SHADERS_DIR.exists():
        pytest.skip(f"Shaders directory not found: {SHADERS_DIR}")
    results = []
    for glsl_file in sorted(SHADERS_DIR.glob("*.glsl")):
        name = glsl_file.stem
        glsl_code = glsl_file.read_text(encoding="utf-8")
        output = convert(glsl_code)
        if output.agsl_code and not output.needs_ai_fallback:
            results.append((name, output.agsl_code))
    return results


class TestAGSLStaticValidation:
    """Validate converted AGSL code against known AGSL constraints."""

    @pytest.fixture(params=["converted", "fresh_convert"],
                    ids=["from_json", "fresh_convert"])
    def shaders(self, request):
        if request.param == "converted":
            return [(d["name"], d["agsl_code"]) for d in _load_converted_shaders()]
        return _load_glsl_shaders()

    def test_no_gl_fragcoord(self, shaders):
        """AGSL uses fragCoord parameter, not gl_FragCoord."""
        failures = []
        for name, code in shaders:
            if "gl_FragCoord" in code:
                failures.append(name)
        assert not failures, f"Shaders still using gl_FragCoord: {failures}"

    def test_no_integer_modulo(self, shaders):
        """AGSL does not support % operator on integers."""
        failures = []
        for name, code in shaders:
            # Match identifier % integer_literal
            if re.search(r"\b\w+\s*%\s*\d+", code):
                failures.append(name)
        assert not failures, f"Shaders using integer %: {failures}"

    def test_no_hashtag_define(self, shaders):
        """AGSL does not support #define preprocessor directives."""
        failures = []
        for name, code in shaders:
            if re.search(r"^\s*#\s*define\b", code, re.MULTILINE):
                failures.append(name)
        assert not failures, f"Shaders using #define: {failures}"

    def test_no_void_mainimage(self, shaders):
        """mainImage must be converted to float4 main."""
        failures = []
        for name, code in shaders:
            if "void mainImage" in code:
                failures.append(name)
        assert not failures, f"Shaders with unconverted mainImage: {failures}"

    def test_no_glsl_type_names(self, shaders):
        """vec/mat types must be converted to float/int types."""
        failures = []
        glsl_types = re.compile(r"\b(vec[234]|mat[234]|ivec[234]|bvec[234])\b")
        for name, code in shaders:
            # Skip comments and strings
            cleaned = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
            cleaned = re.sub(r'"[^"]*"', "", cleaned)
            if glsl_types.search(cleaned):
                failures.append(name)
        assert not failures, f"Shaders with unconverted GLSL types: {failures}"

    def test_has_main_entry_point(self, shaders):
        """AGSL code must have float4 main(float2 fragCoord) entry point."""
        failures = []
        main_re = re.compile(r"float4\s+main\s*\(\s*float2\s+fragCoord\s*\)")
        for name, code in shaders:
            if not main_re.search(code):
                failures.append(name)
        assert not failures, f"Shaders missing main() entry: {failures}"

    def test_has_y_flip(self, shaders):
        """AGSL code must have Y-axis flip for Shadertoy compatibility."""
        failures = []
        for name, code in shaders:
            if "fragCoord.y = iResolution.y - fragCoord.y" not in code:
                failures.append(name)
        assert not failures, f"Shaders missing Y-flip: {failures}"

    def test_uniform_declarations_present(self, shaders):
        """All used uniforms must have declarations."""
        uniform_names = {
            "iResolution", "iTime", "iTimeDelta", "iFrame",
            "iMouse", "iDate", "iSampleRate",
        }
        decl_re = re.compile(
            r"^\s*(?:uniform\s+)?(?:float[234]?)\s+"
            r"(iResolution|iTime|iTimeDelta|iFrame|iMouse|iDate|iSampleRate)\s*;",
            re.MULTILINE,
        )
        failures = []
        for name, code in shaders:
            used = uniform_names & set(re.findall(r"\b(iResolution|iTime|iTimeDelta|iFrame|iMouse|iDate|iSampleRate)\b", code))
            declared = set(decl_re.findall(code))
            missing = used - declared
            if missing:
                failures.append(f"{name}: missing {sorted(missing)}")
        assert not failures, f"Shaders with undeclared uniforms:\n" + "\n".join(failures)

    def test_const_type_matches_initializer(self, shaders):
        """const declarations must have matching type (e.g., const float3, not const float for float3 init)."""
        # Pattern: const float NAME = float3(...)  — type mismatch
        mismatch_re = re.compile(r"const\s+float\s+\w+\s*=\s*float[234]\s*\(")
        failures = []
        for name, code in shaders:
            if mismatch_re.search(code):
                failures.append(name)
        assert not failures, f"Shaders with const type mismatch: {failures}"


class TestConvertFresh:
    """Run the converter on GLSL sources and verify output quality."""

    def test_all_shaders_convert_without_error(self):
        """Every GLSL shader should convert without throwing an exception."""
        if not SHADERS_DIR.exists():
            pytest.skip(f"Shaders directory not found: {SHADERS_DIR}")
        errors = []
        for glsl_file in sorted(SHADERS_DIR.glob("*.glsl")):
            name = glsl_file.stem
            glsl_code = glsl_file.read_text(encoding="utf-8")
            try:
                output = convert(glsl_code)
                assert output.agsl_code is not None or output.needs_ai_fallback
            except Exception as e:
                errors.append(f"{name}: {e}")
        assert not errors, f"Shaders that threw exceptions:\n" + "\n".join(errors)

    def test_conversion_summary(self):
        """Print a summary of conversion results for CI visibility."""
        if not SHADERS_DIR.exists():
            pytest.skip(f"Shaders directory not found: {SHADERS_DIR}")
        ok = ai = err = 0
        for glsl_file in sorted(SHADERS_DIR.glob("*.glsl")):
            glsl_code = glsl_file.read_text(encoding="utf-8")
            output = convert(glsl_code)
            if output.agsl_code and not output.needs_ai_fallback:
                ok += 1
            elif output.needs_ai_fallback:
                ai += 1
            else:
                err += 1
        total = ok + ai + err
        print(f"\nConversion summary: {total} total, {ok} OK, {ai} AI-needed, {err} errors")
        assert ok > 0, "No shaders converted successfully"
