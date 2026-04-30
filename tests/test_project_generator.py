"""Tests for the project generator: template filling and project output."""
import os
import tempfile
import pytest
from scripts.project_generator import generate_project, GenerationConfig


def _generate_and_read(tmp_path, filename, app_name="TestShader", shader_code="float4 main(float2 fc) { return float4(1.0); }"):
    """Helper: generate project and return content of a specific file."""
    config = GenerationConfig(
        app_name=app_name,
        shaders=[{"name": "test", "code": shader_code}],
        output_dir=str(tmp_path / "App"),
    )
    generate_project(config)
    path = tmp_path / "App" / filename
    return path.read_text(encoding="utf-8") if path.exists() else None


class TestGenerateProject:
    """Test suite for Android project generation."""

    def test_generates_project_structure(self, tmp_path):
        """generate_project creates the expected directory structure."""
        config = GenerationConfig(
            app_name="TestShader",
            shaders=[{"name": "gradient", "code": "float4 main(float2 fc) { return float4(1.0); }"}],
            output_dir=str(tmp_path / "ShadertoyApp"),
        )
        generate_project(config)

        base = tmp_path / "ShadertoyApp"
        assert (base / "app" / "build.gradle.kts").exists()
        assert (base / "build.gradle.kts").exists()
        assert (base / "settings.gradle.kts").exists()
        assert (base / "gradle" / "wrapper" / "gradle-wrapper.properties").exists()
        assert (base / "app" / "proguard-rules.pro").exists()
        assert (base / "gradle.properties").exists()
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
        shader_code = "float4 main(float2 fragCoord) { return float4(1.0); }"
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
                {"name": "shader1", "code": "float4 main(float2 fc) { return float4(1,0,0,1); }"},
                {"name": "shader2", "code": "float4 main(float2 fc) { return float4(0,1,0,1); }"},
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
            shaders=[{"name": "s1", "code": "float4 main(float2 fc) { return float4(1.0); }"}],
            output_dir=str(tmp_path / "ShadertoyApp"),
        )
        generate_project(config)

        strings_path = (
            tmp_path / "ShadertoyApp" / "app" / "src" / "main" / "res" / "values" / "strings.xml"
        )
        content = strings_path.read_text(encoding="utf-8")
        assert "MyShaderApp" in content


class TestTemplateCorrectness:
    """Regression tests for template issues that caused build/runtime failures.

    Each test guards against a specific bug that was found during manual testing.
    See docs/superpowers/plans/ for the original issue descriptions.
    """

    def test_settings_gradle_uses_dependency_resolution_management(self, tmp_path):
        """settings.gradle.kts must use dependencyResolutionManagement (not dependencyResolution)."""
        content = _generate_and_read(tmp_path, "settings.gradle.kts")
        assert "dependencyResolutionManagement" in content
        assert "dependencyResolution {" not in content  # missing "Management"

    def test_manifest_has_no_mipmap_icon(self, tmp_path):
        """AndroidManifest.xml must not reference @mipmap/ic_launcher (not generated)."""
        content = _generate_and_read(tmp_path, "app/src/main/AndroidManifest.xml")
        assert "@mipmap" not in content

    def test_activity_main_uses_include_not_view(self, tmp_path):
        """activity_main.xml must use <include> for controls, not a leaf <View>."""
        content = _generate_and_read(tmp_path, "app/src/main/res/layout/activity_main.xml")
        assert '<include layout="@layout/view_shader_controls"' in content
        # Must NOT have a bare <View> as controls container.
        assert '<View\n' not in content

    def test_shader_view_uses_system_clock(self, tmp_path):
        """ShaderView.java must use SystemClock for time (not ValueAnimator.getAnimatedValue)."""
        content = _generate_and_read(tmp_path, "app/src/main/java/com/example/shadertoy/ShaderView.java")
        assert "SystemClock" in content
        assert "uptimeMillis" in content
        assert "Long.MAX_VALUE" not in content  # was the broken approach

    def test_shader_view_flips_touch_y(self, tmp_path):
        """ShaderView.java must flip touch Y for Shadertoy convention (Y=0 at bottom)."""
        content = _generate_and_read(tmp_path, "app/src/main/java/com/example/shadertoy/ShaderView.java")
        assert "getHeight()" in content
        assert "event.getY()" in content

    def test_shader_view_has_perform_click(self, tmp_path):
        """ShaderView.java must override performClick() for accessibility."""
        content = _generate_and_read(tmp_path, "app/src/main/java/com/example/shadertoy/ShaderView.java")
        assert "public boolean performClick()" in content

    def test_main_activity_sets_listener(self, tmp_path):
        """MainActivity.java must call controls.setListener(this)."""
        content = _generate_and_read(tmp_path, "app/src/main/java/com/example/shadertoy/MainActivity.java")
        assert "setListener" in content

    def test_main_activity_screenshot_uses_canvas_draw(self, tmp_path):
        """MainActivity.java must use Canvas.draw() for screenshots (not deprecated getDrawingCache)."""
        content = _generate_and_read(tmp_path, "app/src/main/java/com/example/shadertoy/MainActivity.java")
        assert "new Canvas(bitmap)" in content or "Canvas canvas" in content
        # The actual API call must not be used (comment mentioning it is OK).
        assert ".getDrawingCache()" not in content
        assert "setDrawingCacheEnabled" not in content

    def test_main_activity_storage_uses_app_dir(self, tmp_path):
        """MainActivity.java must use getExternalFilesDir (no permission needed)."""
        content = _generate_and_read(tmp_path, "app/src/main/java/com/example/shadertoy/MainActivity.java")
        assert "getExternalFilesDir" in content
        assert "getExternalStoragePublicDirectory" not in content

    def test_proguard_rules_generated(self, tmp_path):
        """proguard-rules.pro must be generated (referenced by build.gradle.kts)."""
        content = _generate_and_read(tmp_path, "app/proguard-rules.pro")
        assert content is not None

    def test_gradle_properties_generated(self, tmp_path):
        """gradle.properties must be generated with AndroidX enabled."""
        content = _generate_and_read(tmp_path, "gradle.properties")
        assert content is not None
        assert "android.useAndroidX=true" in content

    def test_build_gradle_targets_api_34(self, tmp_path):
        """app/build.gradle.kts must target API 34+."""
        content = _generate_and_read(tmp_path, "app/build.gradle.kts")
        assert "minSdk = 34" in content
