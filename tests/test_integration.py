"""Integration tests: end-to-end GLSL -> AGSL -> Android project pipeline."""
import os
import pytest
from scripts.converter import convert
from scripts.project_generator import generate_project, GenerationConfig


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
        assert "float4 main(float2 fragCoord)" in output.agsl_code
        assert "uniform float3 iResolution;" in output.agsl_code
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in output.agsl_code
        assert "float2 uv" in output.agsl_code
        assert "return float4(" in output.agsl_code
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
        assert "const float SPEED = 2.0;" in output.agsl_code
        assert "uniform float iTime;" in output.agsl_code
        assert "uniform float3 iResolution;" in output.agsl_code
        assert "float2 uv" in output.agsl_code
        assert "float t" in output.agsl_code
        assert "float3 color" in output.agsl_code

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
        assert "const float PI = 3.14159;" in output.agsl_code
        assert "const float TAU = 6.28318;" in output.agsl_code
        assert "uniform float3 iResolution;" in output.agsl_code
        assert "uniform float iTime;" in output.agsl_code
        assert "float4 main(float2 fragCoord)" in output.agsl_code
        assert "fragCoord.y = iResolution.y - fragCoord.y;" in output.agsl_code
        assert "float2x2 rot" in output.agsl_code
        assert "float4(" in output.agsl_code
        assert "float3(" in output.agsl_code

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
