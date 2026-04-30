"""Batch convert GLSL shaders from a directory to AGSL."""
import json
import os
import sys
from pathlib import Path

from scripts.converter import convert


def batch_convert(input_dir: str, output_file: str | None = None) -> list[dict]:
    """Convert all .glsl files in a directory to AGSL.

    Args:
        input_dir: Directory containing .glsl files.
        output_file: Optional path to write JSON results.

    Returns:
        List of dicts with name, original_glsl, agsl_code, needs_ai_fallback, markers.
    """
    input_path = Path(input_dir)
    results = []

    for glsl_file in sorted(input_path.glob("*.glsl")):
        name = glsl_file.stem
        glsl_code = glsl_file.read_text(encoding="utf-8")

        try:
            output = convert(glsl_code)
            results.append({
                "name": name,
                "original_glsl": glsl_code,
                "agsl_code": output.agsl_code,
                "needs_ai_fallback": output.needs_ai_fallback,
                "markers": output.unhandled_fragments,
                "report": output.report,
            })
            status = "AI" if output.needs_ai_fallback else "OK"
            print(f"  [{status}] {name}")
        except Exception as e:
            print(f"  [ERR] {name}: {e}")
            results.append({
                "name": name,
                "original_glsl": glsl_code,
                "agsl_code": None,
                "error": str(e),
            })

    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nResults written to {output_file}")

    ok_count = sum(1 for r in results if r.get("agsl_code") and not r.get("needs_ai_fallback"))
    ai_count = sum(1 for r in results if r.get("needs_ai_fallback"))
    err_count = sum(1 for r in results if r.get("error"))
    print(f"\nTotal: {len(results)} | OK: {ok_count} | AI needed: {ai_count} | Errors: {err_count}")

    return results


if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "D:/AI/Shadertoy/generated_shaders_100"
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    batch_convert(input_dir, output_file)
