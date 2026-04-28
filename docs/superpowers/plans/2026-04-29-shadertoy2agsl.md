# Shadertoy → AGSL Conversion Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill with Python rule engine that converts Shadertoy GLSL shaders to Android AGSL, generating complete runnable Android projects.

**Architecture:** Hybrid approach — Python rule engine handles deterministic GLSL→AGSL pattern conversions (entry functions, types, textures, uniforms, preprocessor, coordinates), with Claude AI fallback for complex patterns (discard, multi-dimensional arrays, recursion). Android project templates are filled with converted shader code.

**Tech Stack:** Python 3.10+, pytest, regex, Android (Java, API 34+, RuntimeShader, ViewPager2, ValueAnimator)

---

## Task 1: Project Scaffolding + pytest Setup

**Goal:** Create the directory structure, `__init__.py` files, and pytest configuration so all subsequent tasks can write and run tests immediately.

### Step 1.1: Create directory structure

```bash
mkdir -p D:/AI/Shadertoy2AGSL/rules/patterns
mkdir -p D:/AI/Shadertoy2AGSL/templates/app/src/main/java/com/example/shadertoy
mkdir -p D:/AI/Shadertoy2AGSL/templates/app/src/main/res/layout
mkdir -p D:/AI/Shadertoy2AGSL/templates/app/src/main/res/values
mkdir -p D:/AI/Shadertoy2AGSL/templates/gradle/wrapper
mkdir -p D:/AI/Shadertoy2AGSL/tests/patterns
```

### Step 1.2: Create `__init__.py` files

Create the following empty files:

- `D:/AI/Shadertoy2AGSL/rules/__init__.py`
- `D:/AI/Shadertoy2AGSL/rules/patterns/__init__.py`
- `D:/AI/Shadertoy2AGSL/tests/__init__.py`
- `D:/AI/Shadertoy2AGSL/tests/patterns/__init__.py`

Each file should contain:

```python
```

(Empty file — just needs to exist for Python package imports.)

### Step 1.3: Create `D:/AI/Shadertoy2AGSL/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Step 1.4: Create `D:/AI/Shadertoy2AGSL/conftest.py`

```python
"""Root conftest for Shadertoy→AGSL converter tests."""
import sys
from pathlib import Path

# Ensure project root is on sys.path so `rules` and `converter` are importable.
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
```

### Step 1.5: Create `D:/AI/Shadertoy2AGSL/tests/conftest.py`

```python
"""Shared test fixtures for Shadertoy→AGSL converter tests."""
import pytest


@pytest.fixture
def simple_shadertoy_shader():
    """A minimal valid Shadertoy shader for testing."""
    return """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv.x, uv.y, 0.0, 1.0);
}
"""


@pytest.fixture
def texture_shadertoy_shader():
    """A Shadertoy shader that uses texture sampling."""
    return """
uniform sampler2D iChannel0;

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);
}
"""


@pytest.fixture
def complex_shadertoy_shader():
    """A Shadertoy shader with preprocessor, types, and coordinates."""
    return """
#define PI 3.14159
#define SPEED 2.0

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float t = iTime * SPEED;
    mat2 rot = mat2(cos(t), -sin(t), sin(t), cos(t));
    vec2 p = rot * (uv - 0.5);
    float d = length(p);
    fragColor = vec4(vec3(smoothstep(0.3, 0.35, d)), 1.0);
}
"""
```

### Step 1.6: Verify pytest runs

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest --co -q
```

**Expected output:** `no tests collected` (no errors — pytest config is valid).

### Step 1.7: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "chore: scaffold project structure and pytest config"
```

---

## Task 2: Entry Pattern (`mainImage` → `main`)

**Goal:** Convert the Shadertoy entry function `void mainImage(out vec4 fragColor, in vec2 fragCoord)` to the AGSL entry function `half4 main(float2 fragCoord)`, and replace all `fragColor` assignments with `return` statements inside that function body.

### Step 2.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/patterns/test_entry.py`

```python
"""Tests for the entry pattern: mainImage → main conversion."""
import pytest
from rules.patterns.entry import convert_entry


class TestConvertEntry:
    """Test suite for entry function conversion."""

    def test_converts_signature_single_line(self):
        """Single-line mainImage signature is converted to main."""
        glsl = "void mainImage(out vec4 fragColor, in vec2 fragCoord) {"
        result, applied = convert_entry(glsl)
        assert "half4 main(float2 fragCoord)" in result
        assert "void mainImage" not in result
        assert applied is True

    def test_converts_signature_multi_line(self):
        """Multi-line mainImage signature is converted to main."""
        glsl = (
            "void mainImage(\n"
            "    out vec4 fragColor,\n"
            "    in vec2 fragCoord\n"
            ")\n"
            "{"
        )
        result, applied = convert_entry(glsl)
        assert "half4 main(float2 fragCoord)" in result
        assert "void mainImage" not in result
        assert applied is True

    def test_replaces_fragColor_assignments(self):
        """All `fragColor = ...` assignments become `return ...`."""
        glsl = (
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    vec2 uv = fragCoord / iResolution.xy;\n"
            "    fragColor = vec4(uv, 0.0, 1.0);\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert "return vec4(uv, 0.0, 1.0);" in result
        assert "fragColor = " not in result
        assert applied is True

    def test_replaces_multiple_fragColor_assignments(self):
        """Shaders with multiple fragColor assignments (branches) all become return."""
        glsl = (
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    if (fragCoord.x < 100.0) {\n"
            "        fragColor = vec4(1.0, 0.0, 0.0, 1.0);\n"
            "    } else {\n"
            "        fragColor = vec4(0.0, 1.0, 0.0, 1.0);\n"
            "    }\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert result.count("return ") == 2
        assert "fragColor = " not in result
        assert applied is True

    def test_preserves_non_entry_code(self):
        """Code outside mainImage is left unchanged."""
        glsl = (
            "float helper(float x) {\n"
            "    return x * 2.0;\n"
            "}\n"
            "\n"
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    fragColor = vec4(1.0);\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert "float helper(float x)" in result
        assert "return x * 2.0;" in result
        assert applied is True

    def test_no_main_image_returns_unchanged(self):
        """If no mainImage function exists, input is returned unchanged."""
        glsl = "float foo(float x) { return x; }"
        result, applied = convert_entry(glsl)
        assert result == glsl
        assert applied is False

    def test_preserves_comments(self):
        """Comments in the shader are preserved."""
        glsl = (
            "// This is a test shader\n"
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    fragColor = vec4(1.0); // white\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        assert "// This is a test shader" in result
        assert "// white" in result
        assert applied is True

    def test_handles_fragColor_with_swizzle(self):
        """fragColor.rgb = ... becomes a block that needs return wrapping (marker or inline)."""
        glsl = (
            "void mainImage(out vec4 fragColor, in vec2 fragCoord)\n"
            "{\n"
            "    fragColor = vec4(0.0);\n"
            "    fragColor.rgb = vec3(1.0, 0.0, 0.0);\n"
            "}"
        )
        result, applied = convert_entry(glsl)
        # The direct assignment is converted
        assert "return vec4(0.0);" in result
        assert applied is True
        # The swizzle assignment cannot be a simple return — it's left for markers
        assert "fragColor.rgb" in result
```

### Step 2.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_entry.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.patterns.entry'` — all tests fail.

### Step 2.3: Implement `D:/AI/Shadertoy2AGSL/rules/patterns/entry.py`

```python
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
    # This only handles lines matching `fragColor = <expr>;`
    # Swizzle assignments like `fragColor.rgb = ...` are left for markers.
    converted = _FRAG_COLOR_ASSIGN_RE.sub(
        lambda m: m.group(0).replace("fragColor = ", "return ", 1),
        converted,
    )

    return converted, True
```

### Step 2.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_entry.py -v
```

**Expected output:** `8 passed`

### Step 2.5: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: entry pattern — mainImage → main conversion"
```

---

## Task 3: Uniforms Pattern (`iResolution`, `iTime`, `iMouse` Declarations)

**Goal:** Detect which Shadertoy built-in uniforms are used in the shader code and inject their AGSL declarations at the top of the source. In AGSL, uniforms must be explicitly declared.

### Step 3.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/patterns/test_uniforms.py`

```python
"""Tests for the uniforms pattern: inject AGSL uniform declarations."""
import pytest
from rules.patterns.uniforms import inject_uniforms


class TestInjectUniforms:
    """Test suite for uniform declaration injection."""

    def test_injects_iResolution(self):
        """iResolution usage triggers uniform float2 iResolution declaration."""
        glsl = "vec2 uv = fragCoord / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float2 iResolution;" in result
        assert injected == ["iResolution"]

    def test_injects_iTime(self):
        """iTime usage triggers uniform float iTime declaration."""
        glsl = "float t = iTime * 2.0;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float iTime;" in result
        assert injected == ["iTime"]

    def test_injects_iMouse(self):
        """iMouse usage triggers uniform float4 iMouse declaration."""
        glsl = "vec2 mouse = iMouse.xy / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float4 iMouse;" in result
        assert "iMouse" in injected

    def test_injects_iResolution_and_iTime(self):
        """Multiple uniforms are all injected."""
        glsl = "vec2 uv = fragCoord / iResolution.xy;\nfloat t = iTime;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float2 iResolution;" in result
        assert "uniform float iTime;" in result
        assert set(injected) == {"iResolution", "iTime"}

    def test_no_uniforms_injected_when_none_used(self):
        """If no built-in uniforms are used, nothing is injected."""
        glsl = "half4 main(float2 fragCoord) { return half4(1.0); }"
        result, injected = inject_uniforms(glsl)
        assert "uniform" not in result
        assert injected == []

    def test_does_not_duplicate_existing_declarations(self):
        """If uniform is already declared, it is not injected again."""
        glsl = "uniform float2 iResolution;\nvec2 uv = fragCoord / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        assert result.count("uniform float2 iResolution;") == 1

    def test_injects_iFrame(self):
        """iFrame usage triggers uniform float iFrame declaration."""
        glsl = "if (iFrame < 10) { }"
        result, injected = inject_uniforms(glsl)
        assert "uniform float iFrame;" in result
        assert "iFrame" in injected

    def test_injects_iDate(self):
        """iDate usage triggers uniform float4 iDate declaration."""
        glsl = "float day = iDate.x;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float4 iDate;" in result
        assert "iDate" in injected

    def test_injects_iSampleRate(self):
        """iSampleRate usage triggers uniform float iSampleRate declaration."""
        glsl = "float rate = iSampleRate;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float iSampleRate;" in result
        assert "iSampleRate" in injected

    def test_uniforms_injected_before_first_line(self):
        """Injected declarations appear at the very top of the source."""
        glsl = "// My shader\nvec2 uv = fragCoord / iResolution.xy;"
        result, injected = inject_uniforms(glsl)
        lines = result.strip().split("\n")
        assert lines[0] == "uniform float2 iResolution;"

    def test_does_not_false_match_partial_names(self):
        """Names like iResolutionScale should not trigger iResolution injection."""
        glsl = "float iResolutionScale = 2.0;"
        result, injected = inject_uniforms(glsl)
        assert "uniform float2 iResolution;" not in result
```

### Step 3.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_uniforms.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.patterns.uniforms'` — all tests fail.

### Step 3.3: Implement `D:/AI/Shadertoy2AGSL/rules/patterns/uniforms.py`

```python
"""Uniforms pattern: inject AGSL uniform declarations for Shadertoy built-ins.

Shadertoy auto-provides uniforms like iResolution, iTime, iMouse, etc.
AGSL requires explicit declarations. This module detects usage of these
uniforms and injects declarations at the top of the source.
"""
import re


# Map of uniform name → AGSL declaration.
# Only built-in Shadertoy uniforms that need injection.
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
_UNIFORM_WORD_RE = re.compile(r"\b(iResolution|iTime|iTimeDelta|iFrame|iMouse|iDate|iSampleRate)\b")

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
```

### Step 3.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_uniforms.py -v
```

**Expected output:** `11 passed`

### Step 3.5: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: uniforms pattern — inject AGSL uniform declarations"
```

---

## Task 4: Types Pattern (`vec` → `half`, `mat` → `half`)

**Goal:** Convert GLSL type names to AGSL type names. `vec2` → `half2`, `vec3` → `half3`, `vec4` → `half4`, `mat2` → `half2x2`, `mat3` → `half3x3`, `mat4` → `half4x4`, `float` → `half` (where it's a standalone type, not part of `float2` etc.).

### Step 4.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/patterns/test_types.py`

```python
"""Tests for the types pattern: GLSL → AGSL type conversion."""
import pytest
from rules.patterns.types import convert_types


class TestConvertTypes:
    """Test suite for type conversion."""

    def test_converts_vec2(self):
        """vec2 → half2."""
        glsl = "vec2 uv = fragCoord / iResolution.xy;"
        result, applied = convert_types(glsl)
        assert "half2 uv" in result
        assert "vec2" not in result
        assert applied is True

    def test_converts_vec3(self):
        """vec3 → half3."""
        glsl = "vec3 color = vec3(1.0, 0.0, 0.0);"
        result, applied = convert_types(glsl)
        assert "half3 color" in result
        assert "half3(" in result
        assert "vec3" not in result
        assert applied is True

    def test_converts_vec4(self):
        """vec4 → half4."""
        glsl = "return vec4(uv, 0.0, 1.0);"
        result, applied = convert_types(glsl)
        assert "half4(" in result
        assert "vec4" not in result
        assert applied is True

    def test_converts_mat2(self):
        """mat2 → half2x2."""
        glsl = "mat2 rot = mat2(cos(t), -sin(t), sin(t), cos(t));"
        result, applied = convert_types(glsl)
        assert "half2x2 rot" in result
        assert "half2x2(" in result
        assert "mat2" not in result
        assert applied is True

    def test_converts_mat3(self):
        """mat3 → half3x3."""
        glsl = "mat3 m = mat3(1.0);"
        result, applied = convert_types(glsl)
        assert "half3x3 m" in result
        assert "half3x3(" in result
        assert "mat3" not in result
        assert applied is True

    def test_converts_mat4(self):
        """mat4 → half4x4."""
        glsl = "mat4 m = mat4(1.0);"
        result, applied = convert_types(glsl)
        assert "half4x4 m" in result
        assert "half4x4(" in result
        assert "mat4" not in result
        assert applied is True

    def test_converts_standalone_float_to_half(self):
        """Standalone `float` type → `half` (not float2/float3/float4)."""
        glsl = "float t = iTime * 2.0;"
        result, applied = convert_types(glsl)
        assert "half t" in result
        assert "float " not in result
        assert applied is True

    def test_does_not_convert_float2(self):
        """float2 should NOT be converted (it's already AGSL-compatible)."""
        glsl = "float2 uv = fragCoord / iResolution;"
        result, applied = convert_types(glsl)
        assert "float2" in result
        # applied may be True if other types were converted, but float2 is untouched.

    def test_converts_ivec2(self):
        """ivec2 → int2."""
        glsl = "ivec2 p = ivec2(1, 2);"
        result, applied = convert_types(glsl)
        assert "int2 p" in result
        assert "int2(" in result
        assert "ivec2" not in result
        assert applied is True

    def test_converts_bvec2(self):
        """bvec2 → bool2."""
        glsl = "bvec2 mask = bvec2(true, false);"
        result, applied = convert_types(glsl)
        assert "bool2 mask" in result
        assert "bool2(" in result
        assert "bvec2" not in result
        assert applied is True

    def test_no_types_returns_unchanged(self):
        """If no GLSL types found, input is returned unchanged."""
        glsl = "return half4(1.0);"
        result, applied = convert_types(glsl)
        assert result == glsl
        assert applied is False

    def test_converts_multiple_types_on_one_line(self):
        """Multiple type conversions on the same line all succeed."""
        glsl = "vec4 color = vec4(vec3(1.0), 1.0);"
        result, applied = convert_types(glsl)
        assert "half4 color = half4(half3(1.0), 1.0);" in result
        assert applied is True

    def test_does_not_convert_inside_comments(self):
        """Type names inside comments are left alone."""
        glsl = "// vec4 test\nfloat x = 1.0;"
        result, applied = convert_types(glsl)
        assert "// vec4 test" in result
        assert "half x" in result
        assert applied is True

    def test_converts_void_parameter_out_vec4(self):
        """out vec4 in function parameters is converted."""
        glsl = "void foo(out vec4 color) { color = vec4(1.0); }"
        result, applied = convert_types(glsl)
        assert "out half4 color" in result
        assert "half4(1.0)" in result
        assert applied is True
```

### Step 4.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_types.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.patterns.types'` — all tests fail.

### Step 4.3: Implement `D:/AI/Shadertoy2AGSL/rules/patterns/types.py`

```python
"""Types pattern: convert GLSL type names to AGSL type names.

Conversion table:
    vec2 → half2, vec3 → half3, vec4 → half4
    mat2 → half2x2, mat3 → half3x3, mat4 → half4x4
    ivec2 → int2, ivec3 → int3, ivec4 → int4
    bvec2 → bool2, bvec3 → bool3, bvec4 → bool4
    float (standalone) → half
"""
import re


# Ordered longest-first to avoid partial matches (e.g., vec2 matching inside vec2x2).
# Each entry: (pattern, replacement).
# Patterns use word boundaries to avoid matching inside identifiers like "myvec2".
_TYPE_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\bvec4\b", "half4"),
    (r"\bvec3\b", "half3"),
    (r"\bvec2\b", "half2"),
    (r"\bmat4\b", "half4x4"),
    (r"\bmat3\b", "half3x3"),
    (r"\bmat2\b", "half2x2"),
    (r"\bivec4\b", "int4"),
    (r"\bivec3\b", "int3"),
    (r"\bivec2\b", "int2"),
    (r"\bbvec4\b", "bool4"),
    (r"\bbvec3\b", "bool3"),
    (r"\bbvec2\b", "bool2"),
]

# Standalone float → half. Negative lookbehind/ahead to avoid float2, float3, float4, float2x2 etc.
_FLOAT_RE = re.compile(r"\bfloat\b(?![234x])")


def convert_types(source: str) -> tuple[str, bool]:
    """Convert GLSL type names to AGSL type names.

    Args:
        source: GLSL source code string.

    Returns:
        Tuple of (converted source, whether any conversion was applied).
    """
    original = source
    result = source

    # Apply vec/mat/ivec/bvec replacements.
    for pattern, replacement in _TYPE_REPLACEMENTS:
        result = re.sub(pattern, replacement, result)

    # Apply standalone float → half.
    result = _FLOAT_RE.sub("half", result)

    applied = result != original
    return result, applied
```

### Step 4.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_types.py -v
```

**Expected output:** `13 passed`

### Step 4.5: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: types pattern — vec/mat/float → half type conversion"
```

---

## Task 5: Textures Pattern (`sampler2D` → `shader`, `texture()` → `.eval()`)

**Goal:** Convert GLSL texture sampling to AGSL shader evaluation. `uniform sampler2D iChannel0` → `uniform shader iChannel0`, and `texture(iChannel0, uv)` → `iChannel0.eval(uv)`.

### Step 5.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/patterns/test_textures.py`

```python
"""Tests for the textures pattern: sampler2D → shader, texture() → .eval()."""
import pytest
from rules.patterns.textures import convert_textures


class TestConvertTextures:
    """Test suite for texture sampling conversion."""

    def test_converts_sampler2D_declaration(self):
        """uniform sampler2D iChannel0 → uniform shader iChannel0."""
        glsl = "uniform sampler2D iChannel0;"
        result, applied = convert_textures(glsl)
        assert "uniform shader iChannel0;" in result
        assert "sampler2D" not in result
        assert applied is True

    def test_converts_texture_call_single_channel(self):
        """texture(iChannel0, uv) → iChannel0.eval(uv)."""
        glsl = "fragColor = texture(iChannel0, uv);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert "texture(iChannel0" not in result
        assert applied is True

    def test_converts_texture_call_with_lod(self):
        """texture(iChannel0, uv, lod) → iChannel0.eval(uv)."""
        glsl = "fragColor = texture(iChannel0, uv, 0.0);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert applied is True

    def test_converts_multiple_channels(self):
        """Multiple texture channels are all converted."""
        glsl = (
            "uniform sampler2D iChannel0;\n"
            "uniform sampler2D iChannel1;\n"
            "vec4 c0 = texture(iChannel0, uv);\n"
            "vec4 c1 = texture(iChannel1, uv);\n"
        )
        result, applied = convert_textures(glsl)
        assert "uniform shader iChannel0;" in result
        assert "uniform shader iChannel1;" in result
        assert "iChannel0.eval(uv)" in result
        assert "iChannel1.eval(uv)" in result
        assert "sampler2D" not in result
        assert "texture(" not in result
        assert applied is True

    def test_no_textures_returns_unchanged(self):
        """If no texture usage found, input is returned unchanged."""
        glsl = "half4 main(float2 fragCoord) { return half4(1.0); }"
        result, applied = convert_textures(glsl)
        assert result == glsl
        assert applied is False

    def test_converts_sampler2D_without_explicit_declaration(self):
        """Even without explicit uniform declaration, texture() calls are converted."""
        glsl = "fragColor = texture(iChannel0, uv);"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert applied is True

    def test_preserves_texture_in_comments(self):
        """Texture references inside comments are left alone."""
        glsl = "// texture(iChannel0, uv)\nfragColor = texture(iChannel1, uv);"
        result, applied = convert_textures(glsl)
        assert "// texture(iChannel0, uv)" in result
        assert "iChannel1.eval(uv)" in result
        assert applied is True

    def test_handles_whitespace_in_texture_call(self):
        """texture calls with extra whitespace are handled."""
        glsl = "fragColor = texture(  iChannel0 , uv );"
        result, applied = convert_textures(glsl)
        assert "iChannel0.eval(uv)" in result
        assert applied is True
```

### Step 5.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_textures.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.patterns.textures'` — all tests fail.

### Step 5.3: Implement `D:/AI/Shadertoy2AGSL/rules/patterns/textures.py`

```python
"""Textures pattern: convert GLSL texture sampling to AGSL shader evaluation.

Shadertoy:
    uniform sampler2D iChannel0;
    fragColor = texture(iChannel0, uv);

AGSL:
    uniform shader iChannel0;
    iChannel0.eval(uv);
"""
import re


# Match `uniform sampler2D <name>;` declarations.
_SAMPLER2D_DECL_RE = re.compile(r"\buniform\s+sampler2D\b")

# Match `texture(<channel>, <coord>[, <lod>])` calls.
# Group 1: channel name (iChannel0..3)
# Group 2: coordinate expression
# Group 3: optional LOD (ignored in AGSL)
_TEXTURE_CALL_RE = re.compile(
    r"\btexture\s*\(\s*(iChannel\d)\s*,\s*([^,)]+?)(?:\s*,\s*[^)]+?)?\s*\)"
)


def convert_textures(source: str) -> tuple[str, bool]:
    """Convert GLSL texture sampling to AGSL shader evaluation.

    Args:
        source: GLSL source code string.

    Returns:
        Tuple of (converted source, whether any conversion was applied).
    """
    original = source
    result = source

    # Convert declarations: sampler2D → shader.
    result = _SAMPLER2D_DECL_RE.sub("uniform shader", result)

    # Convert texture() calls → .eval().
    result = _TEXTURE_CALL_RE.sub(
        lambda m: f"{m.group(1)}.eval({m.group(2).strip()})",
        result,
    )

    applied = result != original
    return result, applied
```

### Step 5.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_textures.py -v
```

**Expected output:** `8 passed`

### Step 5.5: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: textures pattern — sampler2D → shader, texture() → .eval()"
```

---

## Task 6: Preprocessor Pattern (`#define` → `const`)

**Goal:** Convert GLSL `#define` macros to AGSL `const` variable declarations. `#define PI 3.14159` → `const half PI = 3.14159;`.

### Step 6.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/patterns/test_preprocessor.py`

```python
"""Tests for the preprocessor pattern: #define → const."""
import pytest
from rules.patterns.preprocessor import convert_preprocessor


class TestConvertPreprocessor:
    """Test suite for preprocessor conversion."""

    def test_converts_float_define(self):
        """#define PI 3.14159 → const half PI = 3.14159;"""
        glsl = "#define PI 3.14159"
        result, applied = convert_preprocessor(glsl)
        assert "const half PI = 3.14159;" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_integer_define(self):
        """#define MAX_STEPS 64 → const int MAX_STEPS = 64;"""
        glsl = "#define MAX_STEPS 64"
        result, applied = convert_preprocessor(glsl)
        assert "const int MAX_STEPS = 64;" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_expression_define(self):
        """#define SPEED (2.0 * 3.14) → const half SPEED = (2.0 * 3.14);"""
        glsl = "#define SPEED (2.0 * 3.14)"
        result, applied = convert_preprocessor(glsl)
        assert "const half SPEED = (2.0 * 3.14);" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_negative_define(self):
        """#define OFFSET -1.5 → const half OFFSET = -1.5;"""
        glsl = "#define OFFSET -1.5"
        result, applied = convert_preprocessor(glsl)
        assert "const half OFFSET = -1.5;" in result
        assert "#define" not in result
        assert applied is True

    def test_converts_multiple_defines(self):
        """Multiple #define lines are all converted."""
        glsl = (
            "#define PI 3.14159\n"
            "#define TWO_PI 6.28318\n"
            "#define MAX_STEPS 64\n"
        )
        result, applied = convert_preprocessor(glsl)
        assert "const half PI = 3.14159;" in result
        assert "const half TWO_PI = 6.28318;" in result
        assert "const int MAX_STEPS = 64;" in result
        assert "#define" not in result
        assert applied is True

    def test_no_defines_returns_unchanged(self):
        """If no #define found, input is returned unchanged."""
        glsl = "half4 main(float2 fragCoord) { return half4(1.0); }"
        result, applied = convert_preprocessor(glsl)
        assert result == glsl
        assert applied is False

    def test_leaves_ifdef_alone(self):
        """#ifdef / #ifndef / #endif are left unchanged (not handled by this pattern)."""
        glsl = "#ifdef FEATURE_ENABLED\nfloat x = 1.0;\n#endif"
        result, applied = convert_preprocessor(glsl)
        assert "#ifdef FEATURE_ENABLED" in result
        assert "#endif" in result

    def test_converts_define_with_vec_constructor(self):
        """#define COLOR vec3(1.0, 0.0, 0.0) → const half3 COLOR = half3(1.0, 0.0, 0.0);"""
        glsl = "#define COLOR vec3(1.0, 0.0, 0.0)"
        result, applied = convert_preprocessor(glsl)
        assert "const half3 COLOR = half3(1.0, 0.0, 0.0);" in result
        assert applied is True

    def test_leaves_multiline_macros_with_backslash(self):
        """Multi-line macros with backslash continuation are left for AI fallback."""
        glsl = "#define MACRO(a, b) \\\n    do_something(a, b)"
        result, applied = convert_preprocessor(glsl)
        # Multi-line macros are not handled — left for markers/AI fallback
        assert "#define" in result
```

### Step 6.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_preprocessor.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.patterns.preprocessor'` — all tests fail.

### Step 6.3: Implement `D:/AI/Shadertoy2AGSL/rules/patterns/preprocessor.py`

```python
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

# Match float literal (has a decimal point or is like 1e5).
_FLOAT_LITERAL_RE = re.compile(r"-?\d*\.?\d+(?:[eE][+-]?\d+)?")


def _infer_type(value: str) -> str:
    """Infer the AGSL type for a #define value.

    Rules:
        - Integer literal → int
        - Anything else → half (float, expressions, constructors)
    """
    stripped = value.strip()
    if _INT_LITERAL_RE.match(stripped):
        return "int"
    return "half"


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
        # The regex already excludes this by using \w+ for name, but be safe.
        if "(" in name:
            return match.group(0)

        type_name = _infer_type(value)
        return f"const {type_name} {name} = {value};"

    result = _SIMPLE_DEFINE_RE.sub(_replace_define, source)
    applied = result != original
    return result, applied
```

### Step 6.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_preprocessor.py -v
```

**Expected output:** `9 passed`

### Step 6.5: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: preprocessor pattern — #define → const conversion"
```

---

## Task 7: Coordinates Pattern (Y-axis Flip Injection)

**Goal:** Inject a Y-axis flip line at the start of the main function body. AGSL has Y=0 at top-left; Shadertoy has Y=0 at bottom-left. The flip: `fragCoord.y = iResolution.y - fragCoord.y;`

### Step 7.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/patterns/test_coordinates.py`

```python
"""Tests for the coordinates pattern: Y-axis flip injection."""
import pytest
from rules.patterns.coordinates import inject_y_flip


class TestInjectYFlip:
    """Test suite for Y-axis coordinate flip injection."""

    def test_injects_y_flip_at_main_opening_brace(self):
        """Y-flip is injected after the opening brace of main()."""
        agsl = (
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    half2 uv = fragCoord / iResolution;\n"
            "    return half4(uv, 0.0, 1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result
        # The flip should be the first statement in main.
        lines = result.split("\n")
        brace_line_idx = next(i for i, l in enumerate(lines) if "{" in l)
        flip_line_idx = next(
            i for i, l in enumerate(lines)
            if "fragCoord.y = iResolution.y - fragCoord.y" in l
        )
        assert flip_line_idx == brace_line_idx + 1
        assert applied is True

    def test_injects_y_flip_with_indented_brace(self):
        """Y-flip is injected even when opening brace is on the same line."""
        agsl = "half4 main(float2 fragCoord) {\n    return half4(1.0);\n}"
        result, applied = inject_y_flip(agsl)
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result
        assert applied is True

    def test_does_not_inject_if_already_present(self):
        """If Y-flip already exists, it is not injected again."""
        agsl = (
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    fragCoord.y = iResolution.y - fragCoord.y;\n"
            "    return half4(1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        assert result.count("fragCoord.y = iResolution.y - fragCoord.y;") == 1
        assert applied is False

    def test_no_main_function_returns_unchanged(self):
        """If no main() function found, input is returned unchanged."""
        agsl = "float helper(float x) { return x; }"
        result, applied = inject_y_flip(agsl)
        assert result == agsl
        assert applied is False

    def test_injects_with_existing_comments(self):
        """Y-flip is injected correctly even when main has a leading comment."""
        agsl = (
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    // begin shader\n"
            "    return half4(1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result
        assert applied is True

    def test_preserves_indentation(self):
        """Injected line uses 4-space indentation matching the function body."""
        agsl = (
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    return half4(1.0);\n"
            "}"
        )
        result, applied = inject_y_flip(agsl)
        lines = result.split("\n")
        flip_line = next(l for l in lines if "fragCoord.y = iResolution.y" in l)
        assert flip_line.startswith("    ")
```

### Step 7.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_coordinates.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.patterns.coordinates'` — all tests fail.

### Step 7.3: Implement `D:/AI/Shadertoy2AGSL/rules/patterns/coordinates.py`

```python
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
```

### Step 7.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/patterns/test_coordinates.py -v
```

**Expected output:** `6 passed`

### Step 7.5: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: coordinates pattern — Y-axis flip injection"
```

---

## Task 8: Markers (Detect Unhandled Patterns)

**Goal:** Scan the source for patterns that the rule engine cannot handle (discard, multi-dimensional arrays, recursion) and produce a list of unhandled fragments with location info for AI fallback.

### Step 8.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/test_markers.py`

```python
"""Tests for the markers module: detect unhandled patterns for AI fallback."""
import pytest
from rules.markers import scan_markers, Marker


class TestScanMarkers:
    """Test suite for unhandled pattern detection."""

    def test_detects_discard_statement(self):
        """'discard' statements are detected as unhandled."""
        source = (
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    if (fragCoord.x < 0.0) discard;\n"
            "    return half4(1.0);\n"
            "}"
        )
        markers = scan_markers(source)
        assert len(markers) == 1
        assert markers[0].kind == "discard"
        assert markers[0].line == 3

    def test_detects_multi_dimensional_array(self):
        """Multi-dimensional array declarations are detected as unhandled."""
        source = "float arr[4][4];"
        markers = scan_markers(source)
        assert len(markers) == 1
        assert markers[0].kind == "multi_dim_array"

    def test_detects_2d_array(self):
        """2D array like float data[3][3] is detected."""
        source = "half data[3][3];"
        markers = scan_markers(source)
        assert len(markers) == 1
        assert markers[0].kind == "multi_dim_array"

    def test_detects_recursive_function(self):
        """Functions that call themselves are detected as recursive."""
        source = (
            "float fib(float n) {\n"
            "    if (n <= 1.0) return n;\n"
            "    return fib(n - 1.0) + fib(n - 2.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        recursion_markers = [m for m in markers if m.kind == "recursion"]
        assert len(recursion_markers) >= 1

    def test_no_markers_for_clean_code(self):
        """Clean AGSL code produces no markers."""
        source = (
            "uniform float2 iResolution;\n"
            "uniform float iTime;\n"
            "\n"
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    fragCoord.y = iResolution.y - fragCoord.y;\n"
            "    half2 uv = fragCoord / iResolution;\n"
            "    return half4(uv, 0.0, 1.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        assert len(markers) == 0

    def test_detects_discard_in_nested_block(self):
        """discard inside nested if/for is detected."""
        source = (
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    for (int i = 0; i < 10; i++) {\n"
            "        if (i > 5) discard;\n"
            "    }\n"
            "    return half4(1.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        discard_markers = [m for m in markers if m.kind == "discard"]
        assert len(discard_markers) == 1

    def test_detects_multiple_issues(self):
        """Multiple unhandled patterns in one shader are all detected."""
        source = (
            "float matrix[4][4];\n"
            "\n"
            "half4 main(float2 fragCoord)\n"
            "{\n"
            "    if (fragCoord.x < 0.0) discard;\n"
            "    return half4(1.0);\n"
            "}\n"
        )
        markers = scan_markers(source)
        kinds = {m.kind for m in markers}
        assert "discard" in kinds
        assert "multi_dim_array" in kinds

    def test_marker_has_source_snippet(self):
        """Each marker includes the relevant source snippet."""
        source = "if (x < 0.0) discard;\n"
        markers = scan_markers(source)
        assert len(markers) == 1
        assert "discard" in markers[0].snippet

    def test_ignores_discard_in_comments(self):
        """'discard' inside comments is not flagged."""
        source = "// this shader uses discard\nreturn half4(1.0);\n"
        markers = scan_markers(source)
        discard_markers = [m for m in markers if m.kind == "discard"]
        assert len(discard_markers) == 0

    def test_ignores_discard_in_strings(self):
        """'discard' inside string literals is not flagged."""
        source = 'return half4(1.0); // "discard"\n'
        markers = scan_markers(source)
        discard_markers = [m for m in markers if m.kind == "discard"]
        assert len(discard_markers) == 0
```

### Step 8.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_markers.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.markers'` — all tests fail.

### Step 8.3: Implement `D:/AI/Shadertoy2AGSL/rules/markers.py`

```python
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
    snippet: string  # The relevant source line(s)
    description: str # Human-readable description of the issue


# Match `discard` as a standalone statement, not inside comments or strings.
# Strategy: strip comment and string content first, then search.
_DISCARD_RE = re.compile(r"\bdiscard\b")

# Match multi-dimensional array declarations: type name[dim1][dim2]
_MULTI_DIM_ARRAY_RE = re.compile(r"\w+\s+\w+\s*\[\s*\d+\s*\]\s*\[\s*\d+\s*\]")

# Match function definition: type name(params) {
_FUNC_DEF_RE = re.compile(r"(\w+)\s*\(")

# Match single-line comments.
_SINGLE_LINE_COMMENT_RE = re.compile(r"//.*$")

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
    # Simple heuristic: find function name, then look for calls to same name.
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
```

### Step 8.4: Fix the type annotation bug

Note: The `Marker` dataclass has `snippet: string` — this should be `snippet: str`. Fix it:

```python
# In rules/markers.py, change:
#     snippet: string
# to:
#     snippet: str
```

### Step 8.5: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_markers.py -v
```

**Expected output:** `10 passed`

### Step 8.6: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: markers — detect unhandled patterns (discard, arrays, recursion)"
```

---

## Task 9: Engine (Orchestrates All Patterns + Markers)

**Goal:** Build the main rule engine that runs all patterns in sequence, collects the conversion report, and scans for markers. The engine is the core of the rule-based conversion.

### Step 9.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/test_engine.py`

```python
"""Tests for the rule engine: orchestrates all patterns and markers."""
import pytest
from rules.engine import ConversionResult, convert_shader


class TestConvertShader:
    """Test suite for the main rule engine."""

    def test_simple_shader_full_pipeline(self):
        """A simple Shadertoy shader is fully converted to AGSL."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv.x, uv.y, 0.0, 1.0);
}
"""
        result = convert_shader(glsl)
        assert isinstance(result, ConversionResult)
        # Entry converted.
        assert "half4 main(float2 fragCoord)" in result.code
        assert "void mainImage" not in result.code
        # Types converted.
        assert "half2 uv" in result.code
        assert "half4(" in result.code
        # Coordinates flipped.
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in result.code
        # Uniforms injected.
        assert "uniform float2 iResolution;" in result.code
        # FragColor replaced.
        assert "return " in result.code
        assert "fragColor = " not in result.code

    def test_texture_shader_full_pipeline(self):
        """A texture shader is fully converted."""
        glsl = """
uniform sampler2D iChannel0;

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);
}
"""
        result = convert_shader(glsl)
        assert "uniform shader iChannel0;" in result.code
        assert "iChannel0.eval(uv)" in result.code
        assert "sampler2D" not in result.code
        assert "texture(" not in result.code

    def test_complex_shader_full_pipeline(self):
        """A complex shader with defines, types, time is fully converted."""
        glsl = """
#define PI 3.14159

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float t = iTime * PI;
    mat2 rot = mat2(cos(t), -sin(t), sin(t), cos(t));
    vec2 p = rot * (uv - 0.5);
    float d = length(p);
    fragColor = vec4(vec3(smoothstep(0.3, 0.35, d)), 1.0);
}
"""
        result = convert_shader(glsl)
        assert "const half PI = 3.14159;" in result.code
        assert "uniform float iTime;" in result.code
        assert "uniform float2 iResolution;" in result.code
        assert "half2 uv" in result.code
        assert "half t" in result.code
        assert "half2x2 rot" in result.code
        assert "half4(" in result.code
        assert "half3(" in result.code

    def test_report_contains_applied_rules(self):
        """The conversion report lists which rules were applied."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv, 0.0, 1.0);
}
"""
        result = convert_shader(glsl)
        assert "entry" in result.report.applied_rules
        assert "types" in result.report.applied_rules
        assert "uniforms" in result.report.applied_rules
        assert "coordinates" in result.report.applied_rules

    def test_report_contains_markers_when_discard_found(self):
        """When discard is present, the report lists it as a marker."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    if (fragCoord.x < 100.0) discard;
    fragColor = vec4(1.0);
}
"""
        result = convert_shader(glsl)
        assert len(result.markers) > 0
        assert any(m.kind == "discard" for m in result.markers)

    def test_empty_input(self):
        """Empty input returns empty result."""
        result = convert_shader("")
        assert result.code == ""
        assert result.markers == []
        assert result.report.applied_rules == []

    def test_no_main_image_shader(self):
        """A shader without mainImage is still processed for types etc."""
        glsl = "float helper(float x) { return x * 2.0; }"
        result = convert_shader(glsl)
        assert "half helper(half x)" in result.code
        assert "entry" not in result.report.applied_rules
        assert "types" in result.report.applied_rules
```

### Step 9.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_engine.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'rules.engine'` — all tests fail.

### Step 9.3: Implement `D:/AI/Shadertoy2AGSL/rules/engine.py`

```python
"""Rule engine: orchestrates all conversion patterns and marker scanning.

Runs the conversion pipeline in this fixed order:
    1. Preprocessor (#define → const)
    2. Entry (mainImage → main)
    3. Types (vec/mat → half)
    4. Textures (sampler2D → shader, texture() → .eval())
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

    # 1. Preprocessor: #define → const
    code, applied = convert_preprocessor(code)
    if applied:
        report.applied_rules.append("preprocessor")

    # 2. Entry: mainImage → main
    code, applied = convert_entry(code)
    if applied:
        report.applied_rules.append("entry")

    # 3. Types: vec/mat → half
    code, applied = convert_types(code)
    if applied:
        report.applied_rules.append("types")

    # 4. Textures: sampler2D → shader, texture() → .eval()
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
```

### Step 9.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_engine.py -v
```

**Expected output:** `7 passed`

### Step 9.5: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: engine — orchestrates all conversion patterns and markers"
```

---

## Task 10: Converter (Engine + AI Fallback Orchestration)

**Goal:** Build the top-level converter that runs the rule engine, detects if AI fallback is needed, and provides a structured output for the Claude Code skill to consume. The converter is the entry point called by the skill.

### Step 10.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/test_converter.py`

```python
"""Tests for the top-level converter: engine + AI fallback orchestration."""
import pytest
from converter import ConverterOutput, convert, needs_ai_fallback


class TestConvert:
    """Test suite for the top-level converter."""

    def test_simple_shader_no_ai_needed(self):
        """A simple shader converts fully without AI fallback."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv, 0.0, 1.0);
}
"""
        output = convert(glsl)
        assert isinstance(output, ConverterOutput)
        assert output.agsl_code != ""
        assert output.needs_ai_fallback is False
        assert output.unhandled_fragments == []

    def test_discard_shader_needs_ai_fallback(self):
        """A shader with discard needs AI fallback."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    if (fragCoord.x < 100.0) discard;
    fragColor = vec4(1.0);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is True
        assert len(output.unhandled_fragments) > 0
        assert any(f["kind"] == "discard" for f in output.unhandled_fragments)

    def test_multi_dim_array_needs_ai_fallback(self):
        """A shader with multi-dimensional arrays needs AI fallback."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    float data[4][4];
    fragColor = vec4(1.0);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is True
        assert any(f["kind"] == "multi_dim_array" for f in output.unhandled_fragments)

    def test_output_contains_report(self):
        """The output includes the conversion report."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    fragColor = vec4(1.0);
}
"""
        output = convert(glsl)
        assert isinstance(output.report, dict)
        assert "applied_rules" in output.report

    def test_output_contains_original_source(self):
        """The output includes the original source for AI context."""
        glsl = "void mainImage(out vec4 fragColor, in vec2 fragCoord) { fragColor = vec4(1.0); }"
        output = convert(glsl)
        assert output.original_source == glsl


class TestNeedsAiFallback:
    """Test suite for the needs_ai_fallback helper."""

    def test_returns_false_for_clean_code(self):
        """Clean code does not need AI fallback."""
        glsl = "half4 main(float2 fragCoord) { return half4(1.0); }"
        assert needs_ai_fallback(glsl) is False

    def test_returns_true_for_discard(self):
        """Code with discard needs AI fallback."""
        glsl = "if (x < 0.0) discard;"
        assert needs_ai_fallback(glsl) is True

    def test_returns_true_for_multi_dim_array(self):
        """Code with multi-dimensional arrays needs AI fallback."""
        glsl = "float arr[4][4];"
        assert needs_ai_fallback(glsl) is True
```

### Step 10.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_converter.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'converter'` — all tests fail.

### Step 10.3: Implement `D:/AI/Shadertoy2AGSL/converter.py`

```python
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

from rules.engine import convert_shader


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
    from rules.markers import scan_markers
    return len(scan_markers(source)) > 0
```

### Step 10.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_converter.py -v
```

**Expected output:** `8 passed`

### Step 10.5: Run all tests to verify nothing is broken

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest -v
```

**Expected output:** All tests pass (approximately 70+ tests).

### Step 10.6: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: converter — top-level entry point with AI fallback detection"
```

---

## Task 11: Android Project Templates (All `.tmpl` Files)

**Goal:** Create all template files for the generated Android project. Each template uses `{{variable_name}}` placeholders.

### Step 11.1: Create `D:/AI/Shadertoy2AGSL/templates/app/build.gradle.kts.tmpl`

```kotlin
plugins {
    id("com.android.application")
}

android {
    namespace = "com.example.shadertoy"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.shadertoy"
        minSdk = 34
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.viewpager2:viewpager2:1.1.0")
}
```

### Step 11.2: Create `D:/AI/Shadertoy2AGSL/templates/build.gradle.kts.tmpl`

```kotlin
// Top-level build file
plugins {
    id("com.android.application") version "8.7.3" apply false
}
```

### Step 11.3: Create `D:/AI/Shadertoy2AGSL/templates/settings.gradle.kts.tmpl`

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolution {
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "ShadertoyApp"
include(":app")
```

### Step 11.4: Create `D:/AI/Shadertoy2AGSL/templates/gradle/wrapper/gradle-wrapper.properties.tmpl`

```properties
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.11.1-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

### Step 11.5: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/AndroidManifest.xml.tmpl`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/Theme.Material3.DayNight.NoActionBar">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

    </application>

</manifest>
```

### Step 11.6: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/java/com/example/shadertoy/ShaderData.java.tmpl`

```java
package com.example.shadertoy;

/**
 * Data class holding shader information.
 */
public class ShaderData {
    private final String name;
    private final String agslCode;

    public ShaderData(String name, String agslCode) {
        this.name = name;
        this.agslCode = agslCode;
    }

    public String getName() {
        return name;
    }

    public String getAgslCode() {
        return agslCode;
    }
}
```

### Step 11.7: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/java/com/example/shadertoy/ShaderView.java.tmpl`

```java
package com.example.shadertoy;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RuntimeShader;
import android.view.MotionEvent;
import android.view.View;

import android.view.animation.LinearInterpolator;

/**
 * Custom View that renders an AGSL shader with animation support.
 */
public class ShaderView extends View {

    private RuntimeShader shader;
    private final Paint paint = new Paint();
    private ValueAnimator timeAnimator;
    private float elapsedTime = 0f;
    private boolean isPlaying = true;
    private float speedMultiplier = 1.0f;
    private float lastTimestamp = 0f;
    private float iMouseX = 0f;
    private float iMouseY = 0f;
    private float iMouseZ = 0f;
    private float iMouseW = 0f;

    public ShaderView(Context context, String agslCode) {
        super(context);
        initShader(agslCode);
    }

    private void initShader(String agslCode) {
        try {
            shader = new RuntimeShader(agslCode);
            paint.setShader(shader);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        startTimeAnimation();
    }

    @Override
    protected void onDetachedFromWindow() {
        super.onDetachedFromWindow();
        stopTimeAnimation();
    }

    private void startTimeAnimation() {
        timeAnimator = ValueAnimator.ofFloat(0f, 1f);
        timeAnimator.setDuration(Long.MAX_VALUE);
        timeAnimator.setRepeatCount(ValueAnimator.INFINITE);
        timeAnimator.setInterpolator(new LinearInterpolator());
        timeAnimator.addUpdateListener(animation -> {
            float currentTimestamp = (float) animation.getAnimatedValue() * 1000f;
            float delta = (currentTimestamp - lastTimestamp) * speedMultiplier;
            if (delta > 0 && delta < 100f) {
                elapsedTime += delta / 1000f;
            }
            lastTimestamp = currentTimestamp;
            invalidate();
        });
        timeAnimator.start();
    }

    private void stopTimeAnimation() {
        if (timeAnimator != null) {
            timeAnimator.cancel();
            timeAnimator = null;
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (shader == null) return;

        int w = getWidth();
        int h = getHeight();
        if (w == 0 || h == 0) return;

        shader.setFloatUniform("iResolution", (float) w, (float) h, 1.0f);
        shader.setFloatUniform("iTime", elapsedTime);
        shader.setFloatUniform("iMouse", iMouseX, iMouseY, iMouseZ, iMouseW);

        canvas.drawPaint(paint);
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        float x = event.getX();
        float y = event.getY();

        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                iMouseX = x;
                iMouseY = y;
                iMouseZ = x;
                iMouseW = y;
                break;
            case MotionEvent.ACTION_MOVE:
                iMouseX = x;
                iMouseY = y;
                break;
            case MotionEvent.ACTION_UP:
                iMouseZ = -Math.abs(iMouseZ);
                iMouseW = -Math.abs(iMouseW);
                break;
        }
        return true;
    }

    public void togglePlayPause() {
        isPlaying = !isPlaying;
        if (isPlaying) {
            startTimeAnimation();
        } else {
            stopTimeAnimation();
        }
    }

    public boolean isPlaying() {
        return isPlaying;
    }

    public void setSpeed(float multiplier) {
        this.speedMultiplier = multiplier;
    }

    public float getSpeed() {
        return speedMultiplier;
    }

    public void reset() {
        elapsedTime = 0f;
        lastTimestamp = 0f;
        invalidate();
    }
}
```

### Step 11.8: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/java/com/example/shadertoy/ShaderControls.java.tmpl`

```java
package com.example.shadertoy;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.ImageButton;
import android.widget.SeekBar;
import android.widget.TextView;

/**
 * Control panel for shader playback: play/pause, speed slider, screenshot.
 */
public class ShaderControls {

    public interface ControlListener {
        void onPlayPauseToggle();
        void onSpeedChanged(float speed);
        void onScreenshot();
    }

    private final View rootView;
    private final ImageButton playPauseButton;
    private final SeekBar speedSeekBar;
    private final TextView speedLabel;
    private final ImageButton screenshotButton;
    private final TextView shaderNameLabel;
    private ControlListener listener;

    public ShaderControls(Context context, View rootView) {
        this.rootView = rootView;
        this.playPauseButton = rootView.findViewById(R.id.btn_play_pause);
        this.speedSeekBar = rootView.findViewById(R.id.seek_speed);
        this.speedLabel = rootView.findViewById(R.id.label_speed);
        this.screenshotButton = rootView.findViewById(R.id.btn_screenshot);
        this.shaderNameLabel = rootView.findViewById(R.id.label_shader_name);

        setupListeners();
    }

    private void setupListeners() {
        playPauseButton.setOnClickListener(v -> {
            if (listener != null) listener.onPlayPauseToggle();
            updatePlayPauseIcon(true);
        });

        speedSeekBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                float speed = progressToSpeed(progress);
                speedLabel.setText(String.format("%.2fx", speed));
                if (listener != null) listener.onSpeedChanged(speed);
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {}

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {}
        });

        screenshotButton.setOnClickListener(v -> {
            if (listener != null) listener.onScreenshot();
        });
    }

    public void setListener(ControlListener listener) {
        this.listener = listener;
    }

    public void setShaderName(String name) {
        if (shaderNameLabel != null) {
            shaderNameLabel.setText(name);
        }
    }

    public void updatePlayPauseIcon(boolean isPlaying) {
        playPauseButton.setImageResource(
            isPlaying ? android.R.drawable.ic_media_pause : android.R.drawable.ic_media_play
        );
    }

    /**
     * Convert seek bar progress (0-100) to speed multiplier (0.25x - 4.0x).
     * Uses exponential mapping: speed = 0.25 * 2^(progress/25).
     */
    private float progressToSpeed(int progress) {
        return 0.25f * (float) Math.pow(2.0, progress / 25.0);
    }

    /**
     * Convert speed multiplier back to seek bar progress.
     */
    private int speedToProgress(float speed) {
        return (int) (25.0 * Math.log(speed / 0.25) / Math.log(2.0));
    }

    public void setSpeed(float speed) {
        speedSeekBar.setProgress(speedToProgress(speed));
        speedLabel.setText(String.format("%.2fx", speed));
    }
}
```

### Step 11.9: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/java/com/example/shadertoy/MainActivity.java.tmpl`

```java
package com.example.shadertoy;

import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.Environment;
import android.view.View;
import android.view.WindowManager;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.viewpager2.widget.ViewPager2;

import java.io.File;
import java.io.FileOutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * Main activity with ViewPager2 for multi-shader support and control panel.
 */
public class MainActivity extends AppCompatActivity implements ShaderControls.ControlListener {

    private ViewPager2 viewPager;
    private ShaderControls controls;
    private final List<ShaderView> shaderViews = new ArrayList<>();
    private int currentPosition = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        viewPager = findViewById(R.id.view_pager);
        controls = new ShaderControls(this, findViewById(R.id.controls_container));

        loadShaders();
        setupViewPager();
    }

    private void loadShaders() {
        {{shader_loading_code}}
    }

    private void setupViewPager() {
        ShaderPagerAdapter adapter = new ShaderPagerAdapter(shaderViews);
        viewPager.setAdapter(adapter);

        viewPager.registerOnPageChangeCallback(new ViewPager2.OnPageChangeCallback() {
            @Override
            public void onPageSelected(int position) {
                currentPosition = position;
                controls.setShaderName(getShaderName(position));
                controls.updatePlayPauseIcon(shaderViews.get(position).isPlaying());
            }
        });

        if (!shaderViews.isEmpty()) {
            controls.setShaderName(getShaderName(0));
        }
    }

    private String getShaderName(int position) {
        return "Shader " + (position + 1);
    }

    @Override
    public void onPlayPauseToggle() {
        if (currentPosition < shaderViews.size()) {
            shaderViews.get(currentPosition).togglePlayPause();
        }
    }

    @Override
    public void onSpeedChanged(float speed) {
        for (ShaderView view : shaderViews) {
            view.setSpeed(speed);
        }
    }

    @Override
    public void onScreenshot() {
        if (currentPosition >= shaderViews.size()) return;

        ShaderView currentView = shaderViews.get(currentPosition);
        currentView.setDrawingCacheEnabled(true);
        Bitmap cache = currentView.getDrawingCache();
        if (cache == null) {
            currentView.setDrawingCacheEnabled(false);
            Toast.makeText(this, "Screenshot failed", Toast.LENGTH_SHORT).show();
            return;
        }
        Bitmap bitmap = Bitmap.createBitmap(cache);
        currentView.setDrawingCacheEnabled(false);

        try {
            String timestamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date());
            String filename = "shader_" + timestamp + ".png";
            File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES);
            if (!dir.exists()) dir.mkdirs();
            File file = new File(dir, filename);
            FileOutputStream fos = new FileOutputStream(file);
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos);
            fos.flush();
            fos.close();
            Toast.makeText(this, "Saved: " + file.getAbsolutePath(), Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Screenshot failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    /**
     * ViewPager2 adapter for ShaderView pages.
     */
    private static class ShaderPagerAdapter extends androidx.recyclerview.widget.RecyclerView.Adapter<ShaderPagerAdapter.ShaderViewHolder> {
        private final List<ShaderView> views;

        ShaderPagerAdapter(List<ShaderView> views) {
            this.views = views;
        }

        @Override
        public ShaderViewHolder onCreateViewHolder(android.view.ViewGroup parent, int viewType) {
            ShaderView view = views.get(0);
            // Create a new container for each page.
            android.widget.FrameLayout container = new android.widget.FrameLayout(parent.getContext());
            container.setLayoutParams(new android.view.ViewGroup.LayoutParams(
                android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                android.view.ViewGroup.LayoutParams.MATCH_PARENT
            ));
            return new ShaderViewHolder(container);
        }

        @Override
        public void onBindViewHolder(ShaderViewHolder holder, int position) {
            android.widget.FrameLayout container = (android.widget.FrameLayout) holder.itemView;
            container.removeAllViews();
            ShaderView shaderView = views.get(position);
            if (shaderView.getParent() != null) {
                ((android.view.ViewGroup) shaderView.getParent()).removeView(shaderView);
            }
            container.addView(shaderView);
        }

        @Override
        public int getItemCount() {
            return views.size();
        }

        static class ShaderViewHolder extends androidx.recyclerview.widget.RecyclerView.ViewHolder {
            ShaderViewHolder(View itemView) {
                super(itemView);
            }
        }
    }
}
```

### Step 11.10: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/res/layout/activity_main.xml.tmpl`

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="#000000">

    <androidx.viewpager2.widget.ViewPager2
        android:id="@+id/view_pager"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1" />

    <View
        android:id="@+id/controls_container"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:background="#CC000000" />

</LinearLayout>
```

### Step 11.11: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/res/layout/view_shader_controls.xml.tmpl`

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:padding="8dp"
    android:background="#CC000000">

    <TextView
        android:id="@+id/label_shader_name"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:textColor="#FFFFFF"
        android:textSize="16sp"
        android:gravity="center"
        android:paddingBottom="4dp" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:gravity="center_vertical">

        <ImageButton
            android:id="@+id/btn_play_pause"
            android:layout_width="48dp"
            android:layout_height="48dp"
            android:src="@android:drawable/ic_media_pause"
            android:background="?attr/selectableItemBackgroundBorderless"
            android:contentDescription="Play/Pause" />

        <SeekBar
            android:id="@+id/seek_speed"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:max="100"
            android:progress="25"
            android:paddingStart="8dp"
            android:paddingEnd="8dp" />

        <TextView
            android:id="@+id/label_speed"
            android:layout_width="50dp"
            android:layout_height="wrap_content"
            android:textColor="#FFFFFF"
            android:textSize="12sp"
            android:gravity="center"
            android:text="1.00x" />

        <ImageButton
            android:id="@+id/btn_screenshot"
            android:layout_width="48dp"
            android:layout_height="48dp"
            android:src="@android:drawable/ic_menu_camera"
            android:background="?attr/selectableItemBackgroundBorderless"
            android:contentDescription="Screenshot" />

    </LinearLayout>

</LinearLayout>
```

### Step 11.12: Create `D:/AI/Shadertoy2AGSL/templates/app/src/main/res/values/strings.xml.tmpl`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{{app_name}}</string>
</resources>
```

### Step 11.13: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: Android project templates (all .tmpl files)"
```

---

## Task 12: Project Generator (Fills Templates)

**Goal:** Build the project generator that reads template files, fills placeholders with converted shader code and configuration, and writes out a complete Android project.

### Step 12.1: Write failing test — `D:/AI/Shadertoy2AGSL/tests/test_project_generator.py`

```python
"""Tests for the project generator: template filling and project output."""
import os
import tempfile
import pytest
from project_generator import generate_project, GenerationConfig


class TestGenerateProject:
    """Test suite for Android project generation."""

    def test_generates_project_structure(self, tmp_path):
        """generate_project creates the expected directory structure."""
        config = GenerationConfig(
            app_name="TestShader",
            shaders=[{"name": "gradient", "code": "half4 main(float2 fc) { return half4(1.0); }"}],
            output_dir=str(tmp_path / "ShadertoyApp"),
        )
        generate_project(config)

        base = tmp_path / "ShadertoyApp"
        assert (base / "app" / "build.gradle.kts").exists()
        assert (base / "build.gradle.kts").exists()
        assert (base / "settings.gradle.kts").exists()
        assert (base / "gradle" / "wrapper" / "gradle-wrapper.properties").exists()
        assert (base / "app" / "src" / "main" / "AndroidManifest.xml").exists()
        assert (base / "app" / "src" / "main" / "java" / "com" / "example" / "shadertoy" / "MainActivity.java").exists()
        assert (base / "app" / "src" / "main" / "java" / "com" / "example" / "shadertoy" / "ShaderView.java").exists()
        assert (base / "app" / "src" / "main" / "java" / "com" / "example" / "shadertoy" / "ShaderControls.java").exists()
        assert (base / "app" / "src" / "main" / "java" / "com" / "example" / "shadertoy" / "ShaderData.java").exists()
        assert (base / "app" / "src" / "main" / "res" / "layout" / "activity_main.xml").exists()
        assert (base / "app" / "src" / "main" / "res" / "layout" / "view_shader_controls.xml").exists()
        assert (base / "app" / "src" / "main" / "res" / "values" / "strings.xml").exists()

    def test_shader_code_in_main_activity(self, tmp_path):
        """The generated MainActivity.java contains the shader loading code."""
        shader_code = "half4 main(float2 fragCoord) { return half4(1.0); }"
        config = GenerationConfig(
            app_name="TestShader",
            shaders=[{"name": "test_shader", "code": shader_code}],
            output_dir=str(tmp_path / "ShadertoyApp"),
        )
        generate_project(config)

        main_activity_path = (
            tmp_path / "ShadertoyApp" / "app" / "src" / "main" / "java"
            / "com" / "example" / "shadertoy" / "MainActivity.java"
        )
        content = main_activity_path.read_text(encoding="utf-8")
        assert "ShaderData" in content
        assert "test_shader" in content or "Shader" in content

    def test_multiple_shaders(self, tmp_path):
        """Multiple shaders are all included in the generated project."""
        config = GenerationConfig(
            app_name="MultiShader",
            shaders=[
                {"name": "shader1", "code": "half4 main(float2 fc) { return half4(1,0,0,1); }"},
                {"name": "shader2", "code": "half4 main(float2 fc) { return half4(0,1,0,1); }"},
            ],
            output_dir=str(tmp_path / "ShadertoyApp"),
        )
        generate_project(config)

        main_activity_path = (
            tmp_path / "ShadertoyApp" / "app" / "src" / "main" / "java"
            / "com" / "example" / "shadertoy" / "MainActivity.java"
        )
        content = main_activity_path.read_text(encoding="utf-8")
        assert "shader1" in content or "ShaderData" in content
        assert "shader2" in content or "ShaderData" in content

    def test_strings_xml_has_app_name(self, tmp_path):
        """The generated strings.xml contains the app name."""
        config = GenerationConfig(
            app_name="MyShaderApp",
            shaders=[{"name": "s1", "code": "half4 main(float2 fc) { return half4(1.0); }"}],
            output_dir=str(tmp_path / "ShadertoyApp"),
        )
        generate_project(config)

        strings_path = (
            tmp_path / "ShadertoyApp" / "app" / "src" / "main" / "res" / "values" / "strings.xml"
        )
        content = strings_path.read_text(encoding="utf-8")
        assert "MyShaderApp" in content
```

### Step 12.2: Run tests — expect all to fail

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_project_generator.py -v
```

**Expected output:** `ModuleNotFoundError: No module named 'project_generator'` — all tests fail.

### Step 12.3: Implement `D:/AI/Shadertoy2AGSL/project_generator.py`

```python
"""Project generator: fills Android project templates with converted shader code.

Reads .tmpl files from the templates/ directory, replaces {{placeholders}}
with actual values, and writes the complete Android project to disk.
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


# Root of the templates directory (relative to this file).
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class GenerationConfig:
    """Configuration for Android project generation."""
    app_name: str
    shaders: list[dict]  # [{"name": str, "code": str}, ...]
    output_dir: str


def _read_template(relative_path: str) -> str:
    """Read a template file and return its content."""
    full_path = _TEMPLATES_DIR / relative_path
    return full_path.read_text(encoding="utf-8")


def _fill_template(template: str, variables: dict[str, str]) -> str:
    """Replace {{key}} placeholders in a template with values from variables."""
    result = template
    for key, value in variables.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def _write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _generate_shader_loading_code(shaders: list[dict]) -> str:
    """Generate Java code that loads shader data into the shader list."""
    lines = []
    for shader in shaders:
        name = shader["name"]
        code = shader["code"]
        # Escape the AGSL code for a Java string literal.
        escaped = code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        lines.append(
            f'        shaderViews.add(new ShaderView(this, "{escaped}"));'
        )
    return "\n".join(lines)


def generate_project(config: GenerationConfig) -> None:
    """Generate a complete Android project from templates and shader code.

    Args:
        config: GenerationConfig with app name, shaders, and output directory.
    """
    base = Path(config.output_dir)

    # Template variables.
    variables = {
        "app_name": config.app_name,
        "shader_loading_code": _generate_shader_loading_code(config.shaders),
    }

    # List of (template relative path, output relative path).
    # Files without placeholders are listed directly.
    file_mappings = [
        ("app/build.gradle.kts.tmpl", "app/build.gradle.kts"),
        ("build.gradle.kts.tmpl", "build.gradle.kts"),
        ("settings.gradle.kts.tmpl", "settings.gradle.kts"),
        ("gradle/wrapper/gradle-wrapper.properties.tmpl", "gradle/wrapper/gradle-wrapper.properties"),
        ("app/src/main/AndroidManifest.xml.tmpl", "app/src/main/AndroidManifest.xml"),
        ("app/src/main/java/com/example/shadertoy/ShaderData.java.tmpl",
         "app/src/main/java/com/example/shadertoy/ShaderData.java"),
        ("app/src/main/java/com/example/shadertoy/ShaderView.java.tmpl",
         "app/src/main/java/com/example/shadertoy/ShaderView.java"),
        ("app/src/main/java/com/example/shadertoy/ShaderControls.java.tmpl",
         "app/src/main/java/com/example/shadertoy/ShaderControls.java"),
        ("app/src/main/java/com/example/shadertoy/MainActivity.java.tmpl",
         "app/src/main/java/com/example/shadertoy/MainActivity.java"),
        ("app/src/main/res/layout/activity_main.xml.tmpl",
         "app/src/main/res/layout/activity_main.xml"),
        ("app/src/main/res/layout/view_shader_controls.xml.tmpl",
         "app/src/main/res/layout/view_shader_controls.xml"),
        ("app/src/main/res/values/strings.xml.tmpl",
         "app/src/main/res/values/strings.xml"),
    ]

    for template_rel, output_rel in file_mappings:
        template_content = _read_template(template_rel)
        filled_content = _fill_template(template_content, variables)
        _write_file(base / output_rel, filled_content)
```

### Step 12.4: Run tests — expect all to pass

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_project_generator.py -v
```

**Expected output:** `4 passed`

### Step 12.5: Run all tests to verify nothing is broken

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest -v
```

**Expected output:** All tests pass.

### Step 12.6: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: project generator — fills templates and writes Android project"
```

---

## Task 13: Integration Tests

**Goal:** Write end-to-end integration tests that verify the full pipeline: GLSL input → rule engine → converter → project generation. These tests use real Shadertoy-style shaders.

### Step 13.1: Write integration test — `D:/AI/Shadertoy2AGSL/tests/test_integration.py`

```python
"""Integration tests: end-to-end GLSL → AGSL → Android project pipeline."""
import os
import pytest
from converter import convert
from project_generator import generate_project, GenerationConfig


class TestFullPipeline:
    """End-to-end integration tests."""

    def test_gradient_shader_full_pipeline(self, tmp_path):
        """A gradient shader converts and generates a valid project."""
        glsl = """
// Simple gradient shader
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv.x, uv.y, 0.0, 1.0);
}
"""
        # Step 1: Convert.
        output = convert(glsl)
        assert output.needs_ai_fallback is False
        assert "half4 main(float2 fragCoord)" in output.agsl_code
        assert "uniform float2 iResolution;" in output.agsl_code
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in output.agsl_code
        assert "half2 uv" in output.agsl_code
        assert "return half4(" in output.agsl_code
        assert "entry" in output.report["applied_rules"]
        assert "types" in output.report["applied_rules"]
        assert "uniforms" in output.report["applied_rules"]
        assert "coordinates" in output.report["applied_rules"]

        # Step 2: Generate project.
        config = GenerationConfig(
            app_name="GradientShader",
            shaders=[{"name": "gradient", "code": output.agsl_code}],
            output_dir=str(tmp_path / "GradientApp"),
        )
        generate_project(config)

        # Verify project structure.
        base = tmp_path / "GradientApp"
        assert (base / "app" / "build.gradle.kts").exists()
        assert (base / "app" / "src" / "main" / "AndroidManifest.xml").exists()
        assert (base / "app" / "src" / "main" / "java" / "com" / "example" / "shadertoy" / "MainActivity.java").exists()

    def test_animated_shader_full_pipeline(self, tmp_path):
        """An animated shader with iTime converts correctly."""
        glsl = """
#define SPEED 2.0

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float t = iTime * SPEED;
    vec3 color = vec3(0.5 + 0.5 * sin(t + uv.x * 6.28),
                       0.5 + 0.5 * sin(t + uv.y * 6.28),
                       0.5 + 0.5 * cos(t));
    fragColor = vec4(color, 1.0);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is False
        assert "const half SPEED = 2.0;" in output.agsl_code
        assert "uniform float iTime;" in output.agsl_code
        assert "uniform float2 iResolution;" in output.agsl_code
        assert "half2 uv" in output.agsl_code
        assert "half t" in output.agsl_code
        assert "half3 color" in output.agsl_code

        config = GenerationConfig(
            app_name="AnimatedShader",
            shaders=[{"name": "animated", "code": output.agsl_code}],
            output_dir=str(tmp_path / "AnimatedApp"),
        )
        generate_project(config)
        assert (tmp_path / "AnimatedApp" / "app" / "build.gradle.kts").exists()

    def test_texture_shader_full_pipeline(self, tmp_path):
        """A texture shader converts correctly."""
        glsl = """
uniform sampler2D iChannel0;

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is False
        assert "uniform shader iChannel0;" in output.agsl_code
        assert "iChannel0.eval(uv)" in output.agsl_code
        assert "sampler2D" not in output.agsl_code

        config = GenerationConfig(
            app_name="TextureShader",
            shaders=[{"name": "texture", "code": output.agsl_code}],
            output_dir=str(tmp_path / "TextureApp"),
        )
        generate_project(config)
        assert (tmp_path / "TextureApp" / "app" / "build.gradle.kts").exists()

    def test_discard_shader_marks_for_ai_fallback(self):
        """A shader with discard is flagged for AI fallback."""
        glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    if (length(uv - 0.5) > 0.4) discard;
    fragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is True
        assert len(output.unhandled_fragments) > 0
        assert any(f["kind"] == "discard" for f in output.unhandled_fragments)

    def test_complex_shader_full_pipeline(self, tmp_path):
        """A complex shader with all patterns converts correctly."""
        glsl = """
#define PI 3.14159
#define TAU 6.28318

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float t = iTime;

    mat2 rot = mat2(cos(t), -sin(t), sin(t), cos(t));
    vec2 p = rot * (uv - 0.5);
    float d = length(p);

    vec3 col = vec3(smoothstep(0.3, 0.35, d));
    col *= vec3(1.0, 0.8, 0.6);

    fragColor = vec4(col, 1.0);
}
"""
        output = convert(glsl)
        assert output.needs_ai_fallback is False
        assert "const half PI = 3.14159;" in output.agsl_code
        assert "const half TAU = 6.28318;" in output.agsl_code
        assert "uniform float2 iResolution;" in output.agsl_code
        assert "uniform float iTime;" in output.agsl_code
        assert "half4 main(float2 fragCoord)" in output.agsl_code
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in output.agsl_code
        assert "half2x2 rot" in output.agsl_code
        assert "half4(" in output.agsl_code
        assert "half3(" in output.agsl_code

        config = GenerationConfig(
            app_name="ComplexShader",
            shaders=[{"name": "complex", "code": output.agsl_code}],
            output_dir=str(tmp_path / "ComplexApp"),
        )
        generate_project(config)
        assert (tmp_path / "ComplexApp" / "app" / "build.gradle.kts").exists()

    def test_multi_shader_project(self, tmp_path):
        """A project with multiple shaders is generated correctly."""
        shader1_glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(uv, 0.0, 1.0);
}
"""
        shader2_glsl = """
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float d = length(uv - 0.5);
    fragColor = vec4(vec3(d), 1.0);
}
"""
        output1 = convert(shader1_glsl)
        output2 = convert(shader2_glsl)

        config = GenerationConfig(
            app_name="MultiShader",
            shaders=[
                {"name": "gradient", "code": output1.agsl_code},
                {"name": "circle", "code": output2.agsl_code},
            ],
            output_dir=str(tmp_path / "MultiApp"),
        )
        generate_project(config)

        main_activity = (
            tmp_path / "MultiApp" / "app" / "src" / "main" / "java"
            / "com" / "example" / "shadertoy" / "MainActivity.java"
        ).read_text(encoding="utf-8")
        assert "ShaderData" in main_activity or "shaderViews.add" in main_activity

    def test_report_is_complete(self):
        """The conversion report contains all expected fields."""
        glsl = """
#define PI 3.14159

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    float t = iTime;
    fragColor = vec4(uv, t, 1.0);
}
"""
        output = convert(glsl)
        report = output.report
        assert "applied_rules" in report
        assert "injected_uniforms" in report
        assert "warnings" in report
        assert set(report["applied_rules"]) == {
            "preprocessor", "entry", "types", "uniforms", "coordinates"
        }
```

### Step 13.2: Run integration tests

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest tests/test_integration.py -v
```

**Expected output:** `7 passed`

### Step 13.3: Run all tests

```bash
cd D:/AI/Shadertoy2AGSL && python -m pytest -v
```

**Expected output:** All tests pass (approximately 80+ tests total).

### Step 13.4: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "test: integration tests for full GLSL → AGSL → Android pipeline"
```

---

## Task 14: Claude Code Skill Definition File

**Goal:** Create the Claude Code skill definition file that defines how the skill is triggered, what it does, and how it orchestrates the conversion pipeline with AI fallback.

### Step 14.1: Create `D:/AI/Shadertoy2AGSL/.claude/skills/shadertoy2agsl.md`

```markdown
# Shadertoy → AGSL Converter

## Description
Converts Shadertoy GLSL shaders to Android AGSL and generates a complete runnable Android project.

## Trigger
When the user asks to convert a Shadertoy shader (by URL or pasted code) to Android/AGSL.

## Workflow

### Step 1: Obtain GLSL source
- If user provided a URL: fetch the shader from `https://www.shadertoy.com/api/v1/shaders/{ID}?key={KEY}` (use env var `SHADERTOY_API_KEY` or the built-in key). Extract the GLSL code from the JSON response.
- If user pasted code: use it directly.

### Step 2: Run the rule engine
Run the Python converter:
```bash
cd D:/AI/Shadertoy2AGSL && python -c "
from converter import convert
import json, sys
glsl = sys.stdin.read()
output = convert(glsl)
print(json.dumps({
    'agsl_code': output.agsl_code,
    'needs_ai_fallback': output.needs_ai_fallback,
    'unhandled_fragments': output.unhandled_fragments,
    'report': output.report,
}, indent=2))
" << 'SHADER_EOF'
{PASTE_GLSL_HERE}
SHADER_EOF
```

### Step 3: AI fallback (if needed)
If `needs_ai_fallback` is true, examine the `unhandled_fragments` list. For each fragment:
- **discard**: Rewrite as conditional return. E.g., `if (x < 0.0) discard;` → wrap the remaining code in `if (x >= 0.0) { ... }` or use early return with a default color.
- **multi_dim_array**: Flatten to 1D array with manual indexing. E.g., `float arr[4][4]` → `float arr[16]` with `arr[y * 4 + x]` indexing.
- **recursion**: Convert recursion to iteration using a stack or loop.

Apply these fixes directly to the AGSL code string.

### Step 4: Generate Android project
Run the project generator:
```bash
cd D:/AI/Shadertoy2AGSL && python -c "
from project_generator import generate_project, GenerationConfig
import sys, json
config_data = json.loads(sys.stdin.read())
config = GenerationConfig(**config_data)
generate_project(config)
print('Project generated at: ' + config.output_dir)
" << 'CONFIG_EOF'
{
    "app_name": "ShadertoyApp",
    "shaders": [{"name": "shader1", "code": "{AGSL_CODE}"}],
    "output_dir": "./ShadertoyApp"
}
CONFIG_EOF
```

### Step 5: Report to user
Show the user:
1. **Conversion report**: Which rules were applied, which needed AI fallback.
2. **AGSL code**: The converted shader code with comments explaining changes.
3. **Project location**: Where the Android project was generated.
4. **Build instructions**: `cd ShadertoyApp && ./gradlew installDebug`

## Notes
- The rule engine handles: entry function, types, textures, uniforms, preprocessor, coordinates.
- AI fallback handles: discard, multi-dimensional arrays, recursion.
- The generated project uses ViewPager2 for multi-shader support, ValueAnimator for time, and touch events for iMouse.
```

### Step 14.2: Create `D:/AI/Shadertoy2AGSL/.claude/settings.json` (if not exists)

```json
{
  "skills": {
    "shadertoy2agsl": {
      "path": ".claude/skills/shadertoy2agsl.md",
      "trigger": "shadertoy2agsl"
    }
  }
}
```

### Step 14.3: Commit

```bash
cd D:/AI/Shadertoy2AGSL && git add -A && git commit -m "feat: Claude Code skill definition for shadertoy2agsl"
```

---

## Task Summary

| Task | Description | Key Files | Tests |
|------|-------------|-----------|-------|
| 1 | Project scaffolding + pytest | `conftest.py`, `pytest.ini`, `__init__.py` | 0 |
| 2 | Entry pattern | `rules/patterns/entry.py` | 8 |
| 3 | Uniforms pattern | `rules/patterns/uniforms.py` | 11 |
| 4 | Types pattern | `rules/patterns/types.py` | 13 |
| 5 | Textures pattern | `rules/patterns/textures.py` | 8 |
| 6 | Preprocessor pattern | `rules/patterns/preprocessor.py` | 9 |
| 7 | Coordinates pattern | `rules/patterns/coordinates.py` | 6 |
| 8 | Markers | `rules/markers.py` | 10 |
| 9 | Engine | `rules/engine.py` | 7 |
| 10 | Converter | `converter.py` | 8 |
| 11 | Templates | `templates/**/*.tmpl` | 0 |
| 12 | Project generator | `project_generator.py` | 4 |
| 13 | Integration tests | `tests/test_integration.py` | 7 |
| 14 | Skill definition | `.claude/skills/shadertoy2agsl.md` | 0 |

**Total: ~91 tests across 14 tasks.**

## Spec Coverage Verification

| Design Doc Requirement | Covered By |
|------------------------|------------|
| Entry function conversion (`mainImage` → `main`) | Task 2 |
| Coordinate system (Y-axis flip) | Task 7 |
| Precision types (`vec` → `half`) | Task 4 |
| Texture sampling (`texture()` → `.eval()`) | Task 5 |
| Texture declaration (`sampler2D` → `shader`) | Task 5 |
| Preprocessor (`#define` → `const`) | Task 6 |
| Built-in uniform injection | Task 3 |
| `discard` detection (AI fallback) | Task 8 |
| Multi-dimensional arrays detection | Task 8 |
| Recursion detection | Task 8 |
| Rule engine orchestration | Task 9 |
| AI fallback orchestration | Task 10 |
| Android project structure (all components) | Task 11 |
| `ShaderView` (RuntimeShader + animation) | Task 11 |
| `ShaderControls` (play/pause/speed/screenshot) | Task 11 |
| `MainActivity` (ViewPager2) | Task 11 |
| `ShaderData` (data class) | Task 11 |
| Gradle build files | Task 11 |
| Project generator (template filling) | Task 12 |
| Claude Code skill trigger | Task 14 |
| Conversion report output | Task 9, 10 |
| Multi-shader support | Task 11, 13 |
| API 34+ (minSdk) | Task 11 |
| Java language | Task 11 |
| `iMouse` touch support | Task 11 |
| Speed slider (0.25x–4x) | Task 11 |
| Screenshot functionality | Task 11 |
