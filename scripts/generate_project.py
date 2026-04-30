"""Generate the StarNestApp project with all 100 shaders."""
import json
from pathlib import Path

CONVERTED_FILE = Path("D:/AI/Shadertoy2AGSL/output/converted_shaders.json")
OUTPUT_DIR = Path("D:/AI/Shadertoy2AGSL/output/StarNestApp")


def escape_java_string(s: str) -> str:
    """Escape a string for use in a Java string literal."""
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    s = s.replace("\r", "\\r")
    return s


def generate_shader_loading_code(shaders: list[dict]) -> str:
    lines = []
    for d in shaders:
        name = d["name"].replace("_", " ").title()
        # Remove the numeric prefix for cleaner display
        parts = name.split(" ", 1)
        if len(parts) > 1 and parts[0].isdigit():
            name = parts[1]
        code = escape_java_string(d["agsl_code"])
        lines.append(f'        shaderDataList.add(new ShaderData("{name}", "{code}"));')
    return "\n".join(lines)


def main():
    data = json.loads(CONVERTED_FILE.read_text(encoding="utf-8"))

    # Only use successfully converted shaders (not AI-needed ones for now)
    ok_shaders = [d for d in data if d.get("agsl_code") and not d.get("needs_ai_fallback")]
    print(f"Using {len(ok_shaders)} shaders (excluding {len(data) - len(ok_shaders)} needing AI fallback)")

    shader_loading_code = generate_shader_loading_code(ok_shaders)

    # Write the shader loading code to a file for reference
    (OUTPUT_DIR / "shader_loading_code.txt").write_text(shader_loading_code, encoding="utf-8")
    print(f"Shader loading code written to {OUTPUT_DIR / 'shader_loading_code.txt'}")
    print(f"Total shaders: {len(ok_shaders)}")


if __name__ == "__main__":
    main()
