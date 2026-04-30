"""Add a test shader to MainActivity for UI verification."""
import pathlib

p = pathlib.Path('output/StarNestApp/app/src/main/java/com/example/shadertoy/MainActivity.java')
content = p.read_text(encoding='utf-8')

# Simple test shader that's guaranteed to work in AGSL
test_shader_code = (
    'uniform float3 iResolution;'
    '\\nuniform float iTime;'
    '\\nfloat4 main(float2 fragCoord) {'
    '\\n    float2 uv = fragCoord / iResolution.xy;'
    '\\n    float3 col = float3(uv.x, uv.y, 0.5 + 0.5 * sin(iTime));'
    '\\n    return float4(col, 1.0);'
    '\\n}'
)

test_line = f'        shaderDataList.add(new ShaderData("Test Gradient", "{test_shader_code}"));'

old = '    private void void loadShaders() {\n'
# Try without double void
old2 = '    private void loadShaders() {\n'

if old in content:
    new = old + '        // Test shader - guaranteed to work in AGSL\n' + test_line + '\n'
    content = content.replace(old, new, 1)
    p.write_text(content, encoding='utf-8')
    print('OK: Added test shader')
elif old2 in content:
    new = old2 + '        // Test shader - guaranteed to work in AGSL\n' + test_line + '\n'
    content = content.replace(old2, new, 1)
    p.write_text(content, encoding='utf-8')
    print('OK: Added test shader')
else:
    print('ERROR: Could not find loadShaders')
    # Show context
    for i, line in enumerate(content.split('\n')):
        if 'loadShaders' in line:
            print(f'  Line {i+1}: {line}')
