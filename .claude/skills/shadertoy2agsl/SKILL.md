---
name: shadertoy2agsl
description: Use when the user asks to convert a Shadertoy shader (by URL or pasted code) to Android/AGSL. Converts Shadertoy GLSL shaders to Android AGSL and generates a complete runnable Android project.
description_en: Use when the user asks to convert a Shadertoy shader (by URL or pasted code) to Android/AGSL. Converts Shadertoy GLSL shaders to Android AGSL and generates a complete runnable Android project.
description_zh: 当用户要求将 Shadertoy 着色器（通过 URL 或粘贴代码）转换为 Android/AGSL 时使用。将 Shadertoy GLSL 着色器转换为 Android AGSL 并生成完整可运行的 Android 项目。
license: MIT
metadata:
  author: oahc09
  version: 1.0.0
---

# Shadertoy -> AGSL Converter

## Description
Converts Shadertoy GLSL shaders to Android AGSL, generates a complete runnable Android project, compiles it, and produces an installable APK.

## Trigger
When the user asks to convert a Shadertoy shader (by URL or pasted code) to Android/AGSL.

## Project Root

The skill file is located at `{PROJECT_ROOT}/.claude/skills/shadertoy2agsl/SKILL.md`.
To resolve `{PROJECT_ROOT}`, navigate three directories up from the skill file's directory.

## Workflow

### Step 1: Obtain GLSL source
- If user provided a URL: fetch the shader from `https://www.shadertoy.com/api/v1/shaders/{ID}?key={KEY}` (use env var `SHADERTOY_API_KEY` or the built-in key). Extract the GLSL code from the JSON response.
- If user pasted code: use it directly.

### Step 2: GLSL to AGSL conversion
Run the Python converter:
```bash
cd {PROJECT_ROOT} && python -c "
from scripts.converter import convert
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

### Step 4: Add shader to converted_shaders.json
Append the converted shader to the shared JSON file:
```python
import json
data = json.loads(open('{PROJECT_ROOT}/output/converted_shaders.json', encoding='utf-8').read())
data.append({
    'name': '{SHADER_NAME}',
    'original_glsl': glsl,
    'agsl_code': output.agsl_code,
    'needs_ai_fallback': output.needs_ai_fallback,
    'markers': output.unhandled_fragments,
    'report': output.report,
})
with open('{PROJECT_ROOT}/output/converted_shaders.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

### Step 5: Generate standalone Android project
Generate a **standalone project** with only this shader (not all accumulated shaders):
```bash
cd {PROJECT_ROOT} && python scripts/generate_android_project.py \
  --output output/{SHADER_NAME}App \
  --shaders {SHADER_NAME}
```
Each conversion produces its own independent Android project under `output/{SHADER_NAME}App/`.

### Step 6: Ensure Gradle wrapper exists
If the generated project lacks `gradlew`, generate the wrapper using any installed Gradle:
```bash
cd {PROJECT_ROOT}/output/{SHADER_NAME}App
gradle wrapper --gradle-version 8.11.1
```
Or copy from the skeleton project at `{PROJECT_ROOT}/output/StarNestApp/`.

### Step 7: Compile APK
Build the debug APK:
```bash
cd {PROJECT_ROOT}/output/{SHADER_NAME}App && ./gradlew assembleDebug
```
Verify the APK exists at `app/build/outputs/apk/debug/app-debug.apk`.

### Step 8: Report to user
Show the user:
1. **Conversion report**: Which rules were applied, which needed AI fallback.
2. **AGSL code**: The converted shader code with comments explaining changes.
3. **Project location**: `output/{SHADER_NAME}App`
4. **APK location**: `output/{SHADER_NAME}App/app/build/outputs/apk/debug/app-debug.apk`
5. **Install command**: `adb install output/{SHADER_NAME}App/app/build/outputs/apk/debug/app-debug.apk`

## Notes
- The rule engine handles: entry function, types, textures, uniforms, preprocessor, coordinates.
- AI fallback handles: discard, multi-dimensional arrays, recursion.
- The generated project uses Spinner dropdown for shader selection.
- Shaders are embedded inline in `loadShaders()` — no runtime assets needed for the app itself.
- Each conversion generates an independent standalone Android project under `output/{SHADER_NAME}App/`.

## Compilation & Visual Fidelity Guarantees

### Compilation (build-time)
The templates are designed to compile out-of-the-box on Android Studio with Gradle 8.11+ and AGP 8.7+. Key design decisions:
- **No mipmap icons**: `AndroidManifest.xml` omits `android:icon` to avoid missing resource errors.
- **`ShaderControls` constructor**: Accepts the root view directly; no layout inflation needed.
- **`settings.gradle.kts`**: Uses `dependencyResolutionManagement` (not `dependencyResolution`).
- **Missing files generated**: `proguard-rules.pro` and `gradle.properties` are included in the template set.
- **`iResolution` is `float3`**: Shadertoy's `iResolution` is `vec3` (width, height, aspect ratio). The AGSL declaration must be `uniform float3 iResolution;` to match the 3-float `setFloatUniform` call in `ShaderView`.

### Visual Fidelity (runtime)
- **Use `float` not `half`**: AGSL's `half` type is 16-bit and causes color banding in iterative shaders (e.g., raymarching). The type converter uses `float`/`float2`/`float3`/`float4` for all types. Standalone `float` literals are NOT converted.
- **Animation via `SystemClock.uptimeMillis()`**: The template uses wall-clock millis with a 20ms ValueAnimator as a frame ticker. Previous approaches using `ValueAnimator.getAnimatedValue()` or `Long.MAX_VALUE` duration caused precision issues.
- **Touch Y-flip**: Android's Y=0 is at top; Shadertoy's Y=0 is at bottom. `ShaderView.onTouchEvent` does `y = getHeight() - event.getY()` to match Shadertoy convention.
- **`performClick()` override**: Required for accessibility when overriding `onTouchEvent`.
- **Screenshot**: Uses `Canvas.draw()` instead of deprecated `getDrawingCache()`.
- **Storage**: Uses `getExternalFilesDir()` (no permission needed) instead of external public storage.

## Environment Requirements

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Type union syntax (`Path \| None`) |
| Python packages | stdlib only | No third-party packages needed |
| Gradle | 8.11+ | Building Android project (`gradle wrapper` or pre-existing `output/StarNestApp/gradlew`) |
| Android SDK | AGP 8.7+, compileSdk 34 | Required by Gradle build |
| `adb` | any | Installing APK to device |

### Skeleton project
`generate_android_project.py` copies base files from `output/StarNestApp/`. This directory **must exist** with:
- `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties`
- `gradlew`, `gradlew.bat`, `gradle/wrapper/`
- `app/build.gradle.kts`, `app/proguard-rules.pro`, `app/src/main/AndroidManifest.xml`
- `ShaderControls.java`, `ShaderData.java` (support classes)
- Layout and value resources under `app/src/main/res/`
