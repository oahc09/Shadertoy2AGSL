# Shadertoy -> AGSL Converter

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
- **discard**: Rewrite as conditional return. E.g., `if (x < 0.0) discard;` -> wrap the remaining code in `if (x >= 0.0) { ... }` or use early return with a default color.
- **multi_dim_array**: Flatten to 1D array with manual indexing. E.g., `float arr[4][4]` -> `float arr[16]` with `arr[y * 4 + x]` indexing.
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
