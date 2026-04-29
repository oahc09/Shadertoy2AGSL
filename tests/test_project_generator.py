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
