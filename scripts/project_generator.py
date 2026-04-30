"""Project generator: fills Android project templates with converted shader code.

Reads .tmpl files from the templates/ directory, replaces {{placeholders}}
with actual values, and writes the complete Android project to disk.
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


# Root of the templates directory (relative to this file).
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "references"


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
    """Generate Java code that creates ShaderData objects for each shader."""
    lines = []
    for shader in shaders:
        name = shader["name"]
        code = shader["code"]
        # Escape the AGSL code for a Java string literal.
        escaped = code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        lines.append(
            f'        shaderDataList.add(new ShaderData("{name}", "{escaped}"));'
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
    file_mappings = [
        ("app/build.gradle.kts.tmpl", "app/build.gradle.kts"),
        ("build.gradle.kts.tmpl", "build.gradle.kts"),
        ("settings.gradle.kts.tmpl", "settings.gradle.kts"),
        ("gradle.properties.tmpl", "gradle.properties"),
        ("gradle/wrapper/gradle-wrapper.properties.tmpl", "gradle/wrapper/gradle-wrapper.properties"),
        ("app/proguard-rules.pro.tmpl", "app/proguard-rules.pro"),
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
