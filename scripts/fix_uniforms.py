"""Fix uniform declarations in generated MainActivity.java."""
import re
from pathlib import Path

p = Path("D:/AI/Shadertoy2AGSL/output/StarNestApp/app/src/main/java/com/example/shadertoy/MainActivity.java")
content = p.read_text(encoding="utf-8")

# Strip 'uniform ' from all uniform declarations in the Java string literals
# The Java strings use \n for newlines, so we match 'uniform ' at line starts
content = re.sub(r'\\nuniform ', r'\\n', content)
# Also handle the start of string (after the opening quote)
content = re.sub(r'"uniform ', r'"', content)

p.write_text(content, encoding="utf-8")
print("OK: Stripped 'uniform' from all shader declarations in MainActivity.java")
