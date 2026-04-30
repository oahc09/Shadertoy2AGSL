"""Generate a standalone Android project with converted AGSL shaders.

Usage:
    # Generate project with specific shaders:
    python scripts/generate_android_project.py --output output/MyShaderApp --shaders shader_name

    # Generate project with all shaders from JSON:
    python scripts/generate_android_project.py --output output/AllShadersApp
"""
import argparse
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKELETON_DIR = PROJECT_ROOT / "output/StarNestApp"

# Files to copy from skeleton to new project (relative paths)
_SKELETON_FILES = [
    "build.gradle.kts",
    "settings.gradle.kts",
    "gradle.properties",
    "gradlew",
    "gradlew.bat",
    "gradle/wrapper/gradle-wrapper.jar",
    "gradle/wrapper/gradle-wrapper.properties",
    "app/build.gradle.kts",
    "app/proguard-rules.pro",
    "app/src/main/AndroidManifest.xml",
]

_SKELETON_DIRS = [
    "app/src/main/res/layout",
    "app/src/main/res/values",
]

# Java support files (always the same regardless of shaders)
_SUPPORT_JAVA = [
    "app/src/main/java/com/example/shadertoy/ShaderControls.java",
    "app/src/main/java/com/example/shadertoy/ShaderData.java",
]


def _copy_skeleton(output_dir: Path) -> bool:
    """Copy Gradle build files, wrapper, and support Java from skeleton project."""
    if not SKELETON_DIR.exists():
        print(f"  WARNING: Skeleton project not found at {SKELETON_DIR}")
        return False

    for rel in _SKELETON_FILES + _SUPPORT_JAVA:
        src = SKELETON_DIR / rel
        dst = output_dir / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for rel in _SKELETON_DIRS:
        src = SKELETON_DIR / rel
        dst = output_dir / rel
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)

    print("  Copied skeleton project files")
    return True


def escape_java(s: str) -> str:
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    s = s.replace("\r", "\\r")
    return s


def shader_name(raw: str) -> str:
    """Convert '001_chrome_chibi_guardian' to 'Chrome Chibi Guardian'."""
    name = raw.replace("_", " ").title()
    parts = name.split(" ", 1)
    if len(parts) > 1 and parts[0].isdigit():
        name = parts[1]
    return name


def generate_shader_loading(shaders: list[dict]) -> str:
    lines = []
    for d in shaders:
        name = shader_name(d["name"])
        code = escape_java(d["agsl_code"])
        lines.append(f'        shaderDataList.add(new ShaderData("{name}", "{code}"));')
    return "\n".join(lines)


def generate_project(output_dir: Path, shaders: list[dict], converted_file: Path | None = None):
    """Generate an Android project at output_dir with the given shaders.

    Args:
        output_dir: Target directory for the Android project.
        shaders: List of shader dicts with 'name' and 'agsl_code' keys.
        converted_file: Optional path to converted_shaders.json for test assets.
    """
    ok = [d for d in shaders if d.get("agsl_code") and not d.get("needs_ai_fallback")]
    print(f"Generating project at {output_dir} with {len(ok)} shaders")

    # Copy skeleton (Gradle, wrapper, manifest, support Java)
    _copy_skeleton(output_dir)

    java_dir = output_dir / "app/src/main/java/com/example/shadertoy"
    res_dir = output_dir / "app/src/main/res"
    java_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "layout").mkdir(parents=True, exist_ok=True)

    shader_loading = generate_shader_loading(ok)

    main_activity = f'''package com.example.shadertoy;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Bundle;
import android.os.Environment;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.io.File;
import java.io.FileOutputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class MainActivity extends AppCompatActivity implements ShaderControls.ControlListener {{

    private Spinner spinner;
    private ShaderView shaderView;
    private ShaderControls controls;
    private final List<ShaderData> shaderDataList = new ArrayList<>();
    private int currentIndex = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        spinner = findViewById(R.id.spinner_shader);
        shaderView = findViewById(R.id.shader_view);
        controls = new ShaderControls(findViewById(android.R.id.content));
        controls.setListener(this);

        loadShaders();
        setupSpinner();
        switchShader(0);
    }}

    private void loadShaders() {{
{shader_loading}
    }}

    private void setupSpinner() {{
        List<String> names = new ArrayList<>();
        for (ShaderData d : shaderDataList) {{
            names.add(d.getName());
        }}

        ArrayAdapter<String> adapter = new ArrayAdapter<String>(
            this, android.R.layout.simple_spinner_item, names) {{
            @Override
            public View getView(int position, View convertView, android.view.ViewGroup parent) {{
                View view = super.getView(position, convertView, parent);
                TextView tv = view.findViewById(android.R.id.text1);
                if (tv != null) {{
                    tv.setTextColor(0xFFFFFFFF);
                    tv.setTextSize(14f);
                }}
                return view;
            }}
            @Override
            public View getDropDownView(int position, View convertView, android.view.ViewGroup parent) {{
                View view = super.getDropDownView(position, convertView, parent);
                TextView tv = view.findViewById(android.R.id.text1);
                if (tv != null) {{
                    tv.setTextColor(0xFFFFFFFF);
                    tv.setTextSize(14f);
                }}
                view.setBackgroundColor(0xFF1A1A2E);
                return view;
            }}
        }};
        spinner.setAdapter(adapter);

        spinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {{
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {{
                if (position != currentIndex) {{
                    currentIndex = position;
                    switchShader(position);
                }}
            }}

            @Override
            public void onNothingSelected(AdapterView<?> parent) {{}}
        }});
    }}

    private void switchShader(int position) {{
        try {{
            ShaderData data = shaderDataList.get(position);
            shaderView.loadShader(data.getAgslCode());
            controls.setShaderName(data.getName());
            controls.updatePlayPauseIcon(true);
        }} catch (Exception e) {{
            android.util.Log.e("ShaderView", "switchShader failed: " + e.getMessage(), e);
            Toast.makeText(this, "Shader error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }}
    }}

    @Override
    public void onPlayPauseToggle() {{
        shaderView.togglePlayPause();
    }}

    @Override
    public void onSpeedChanged(float speed) {{
        shaderView.setSpeed(speed);
    }}

    @Override
    public void onScreenshot() {{
        Bitmap bitmap = Bitmap.createBitmap(shaderView.getWidth(), shaderView.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        shaderView.draw(canvas);

        try {{
            String timestamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date());
            String filename = "shader_" + timestamp + ".png";
            File dir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
            if (dir != null && !dir.exists()) dir.mkdirs();
            File file = new File(dir, filename);
            FileOutputStream fos = new FileOutputStream(file);
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos);
            fos.flush();
            fos.close();
            Toast.makeText(this, "Saved: " + file.getAbsolutePath(), Toast.LENGTH_LONG).show();
        }} catch (Exception e) {{
            Toast.makeText(this, "Screenshot failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }} finally {{
            bitmap.recycle();
        }}
    }}
}}
'''
    (java_dir / "MainActivity.java").write_text(main_activity, encoding="utf-8")
    print("  Written MainActivity.java")

    shader_view = '''package com.example.shadertoy;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RuntimeShader;
import android.os.SystemClock;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

public class ShaderView extends View {

    private RuntimeShader shader;
    private final Paint paint = new Paint();
    private ValueAnimator frameAnimator;
    private float elapsedTime = 0f;
    private boolean isPlaying = true;
    private float speedMultiplier = 1.0f;
    private long lastFrameTime = 0L;
    private float iMouseX = 0f;
    private float iMouseY = 0f;
    private float iMouseZ = 0f;
    private float iMouseW = 0f;

    // FPS tracking
    private int frameCount = 0;
    private long fpsStartTime = 0L;
    private float currentFps = 0f;
    private final Paint fpsPaint = new Paint();

    public ShaderView(Context context) {
        super(context);
        initFpsPaint();
    }

    public ShaderView(Context context, AttributeSet attrs) {
        super(context, attrs);
        initFpsPaint();
    }

    public ShaderView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        initFpsPaint();
    }

    private void initFpsPaint() {
        fpsPaint.setColor(0xCC00FF00);
        fpsPaint.setTextSize(32f);
        fpsPaint.setAntiAlias(true);
        fpsPaint.setTypeface(android.graphics.Typeface.MONOSPACE);
    }

    public void loadShader(String agslCode) {
        stopAnimation();
        elapsedTime = 0f;
        try {
            shader = new RuntimeShader(agslCode);
            paint.setShader(shader);
        } catch (Exception e) {
            e.printStackTrace();
            shader = null;
        }
        if (isPlaying) {
            startAnimation();
        }
        invalidate();
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        if (isPlaying && shader != null) startAnimation();
    }

    @Override
    protected void onDetachedFromWindow() {
        super.onDetachedFromWindow();
        stopAnimation();
    }

    private void startAnimation() {
        lastFrameTime = SystemClock.uptimeMillis();
        frameAnimator = ValueAnimator.ofFloat(0f, 1f);
        frameAnimator.setDuration(20);
        frameAnimator.setRepeatCount(ValueAnimator.INFINITE);
        frameAnimator.addUpdateListener(animation -> {
            long now = SystemClock.uptimeMillis();
            float deltaSeconds = (now - lastFrameTime) / 1000f;
            lastFrameTime = now;
            if (deltaSeconds > 0 && deltaSeconds < 0.1f) {
                elapsedTime += deltaSeconds * speedMultiplier;
            }
            invalidate();
        });
        frameAnimator.start();
    }

    private void stopAnimation() {
        if (frameAnimator != null) {
            frameAnimator.cancel();
            frameAnimator = null;
        }
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (shader == null) return;

        int w = getWidth();
        int h = getHeight();
        if (w == 0 || h == 0) return;

        try { shader.setFloatUniform("iResolution", (float) w, (float) h, 1.0f); } catch (Exception ignored) {}
        try { shader.setFloatUniform("iTime", elapsedTime); } catch (Exception ignored) {}
        try { shader.setFloatUniform("iMouse", iMouseX, iMouseY, iMouseZ, iMouseW); } catch (Exception ignored) {}

        canvas.drawPaint(paint);

        // FPS overlay — right side, vertically centered
        frameCount++;
        long now = SystemClock.uptimeMillis();
        if (fpsStartTime == 0L) fpsStartTime = now;
        long elapsed = now - fpsStartTime;
        if (elapsed >= 1000) {
            currentFps = frameCount * 1000f / elapsed;
            frameCount = 0;
            fpsStartTime = now;
        }
        String fpsText = String.format(java.util.Locale.US, "%.0f FPS", currentFps);
        float textWidth = fpsPaint.measureText(fpsText);
        float x = w - textWidth - 16f;
        float y = h / 2f;
        canvas.drawText(fpsText, x, y, fpsPaint);
    }

    @Override
    public boolean performClick() {
        return super.performClick();
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        float x = event.getX();
        float y = getHeight() - event.getY();

        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                iMouseX = x;
                iMouseY = y;
                iMouseZ = x;
                iMouseW = y;
                break;
            case MotionEvent.ACTION_MOVE:
                iMouseX = x;
                iMouseY = y;
                break;
            case MotionEvent.ACTION_UP:
                iMouseZ = -Math.abs(iMouseZ);
                iMouseW = -Math.abs(iMouseW);
                performClick();
                break;
        }
        return true;
    }

    public void togglePlayPause() {
        isPlaying = !isPlaying;
        if (isPlaying) {
            startAnimation();
        } else {
            stopAnimation();
        }
    }

    public boolean isPlaying() {
        return isPlaying;
    }

    public void setSpeed(float multiplier) {
        this.speedMultiplier = multiplier;
    }

    public float getSpeed() {
        return speedMultiplier;
    }

    public void reset() {
        elapsedTime = 0f;
        lastFrameTime = SystemClock.uptimeMillis();
        invalidate();
    }
}
'''
    (java_dir / "ShaderView.java").write_text(shader_view, encoding="utf-8")
    print("  Written ShaderView.java")

    activity_main = '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="#000000"
    android:fitsSystemWindows="true">

    <Spinner
        android:id="@+id/spinner_shader"
        android:layout_width="match_parent"
        android:layout_height="48dp"
        android:background="#FF1A1A2E"
        android:paddingStart="12dp"
        android:paddingEnd="12dp"
        android:popupBackground="#FF1A1A2E" />

    <com.example.shadertoy.ShaderView
        android:id="@+id/shader_view"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1" />

    <include layout="@layout/view_shader_controls" />

</LinearLayout>
'''
    (res_dir / "layout/activity_main.xml").write_text(activity_main, encoding="utf-8")
    print("  Written activity_main.xml")

    spinner_item = '''<?xml version="1.0" encoding="utf-8"?>
<TextView xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@android:id/text1"
    android:layout_width="match_parent"
    android:layout_height="48dp"
    android:gravity="center_vertical"
    android:paddingStart="12dp"
    android:paddingEnd="12dp"
    android:textColor="#FFFFFFFF"
    android:textSize="14sp"
    android:background="#FF1A1A2E" />
'''
    (res_dir / "layout/spinner_item.xml").write_text(spinner_item, encoding="utf-8")
    print("  Written spinner_item.xml")

    gradle_path = output_dir / "app/build.gradle.kts"
    if gradle_path.exists():
        gradle = gradle_path.read_text(encoding="utf-8")
        gradle = gradle.replace('    implementation("androidx.viewpager2:viewpager2:1.1.0")\n', '')
        if "androidTestImplementation" not in gradle:
            gradle = gradle.replace(
                '    implementation("com.google.android.material:material:1.12.0")',
                '    implementation("com.google.android.material:material:1.12.0")\n'
                '\n    androidTestImplementation("androidx.test.ext:junit:1.2.1")\n'
                '    androidTestImplementation("androidx.test:runner:1.6.2")'
            )
        gradle_path.write_text(gradle, encoding="utf-8")
        print("  Updated build.gradle.kts")

    android_test_dir = output_dir / "app/src/androidTest/java/com/example/shadertoy"
    android_test_dir.mkdir(parents=True, exist_ok=True)

    test_code = (
        "package com.example.shadertoy;\n"
        "\n"
        "import android.content.Context;\n"
        "import android.graphics.RuntimeShader;\n"
        "\n"
        "import androidx.test.ext.junit.runners.AndroidJUnit4;\n"
        "import androidx.test.platform.app.InstrumentationRegistry;\n"
        "\n"
        "import org.json.JSONArray;\n"
        "import org.json.JSONObject;\n"
        "import org.junit.Before;\n"
        "import org.junit.Test;\n"
        "import org.junit.runner.RunWith;\n"
        "\n"
        "import java.io.InputStream;\n"
        "import java.nio.charset.StandardCharsets;\n"
        "import java.util.ArrayList;\n"
        "import java.util.List;\n"
        "\n"
        "import static org.junit.Assert.assertTrue;\n"
        "\n"
        "@RunWith(AndroidJUnit4.class)\n"
        "public class ShaderCompilationTest {\n"
        "\n"
        "    private Context context;\n"
        "    private JSONArray shaderData;\n"
        "\n"
        "    @Before\n"
        "    public void setUp() throws Exception {\n"
        "        context = InstrumentationRegistry.getInstrumentation().getTargetContext();\n"
        "        InputStream is = context.getAssets().open(\"converted_shaders.json\");\n"
        "        byte[] buffer = new byte[is.available()];\n"
        "        is.read(buffer);\n"
        "        is.close();\n"
        "        shaderData = new JSONArray(new String(buffer, StandardCharsets.UTF_8));\n"
        "    }\n"
        "\n"
        "    @Test\n"
        "    public void allConvertedShadersCompile() throws Exception {\n"
        "        List<String> failures = new ArrayList<>();\n"
        "        int total = 0;\n"
        "        int ok = 0;\n"
        "        int aiNeeded = 0;\n"
        "\n"
        "        for (int i = 0; i < shaderData.length(); i++) {\n"
        "            JSONObject shader = shaderData.getJSONObject(i);\n"
        "            String name = shader.getString(\"name\");\n"
        "            boolean needsAi = shader.optBoolean(\"needs_ai_fallback\", false);\n"
        "\n"
        "            if (needsAi) {\n"
        "                aiNeeded++;\n"
        "                continue;\n"
        "            }\n"
        "\n"
        "            String agslCode = shader.optString(\"agsl_code\", null);\n"
        "            if (agslCode == null || agslCode.isEmpty()) {\n"
        "                continue;\n"
        "            }\n"
        "\n"
        "            total++;\n"
        "            try {\n"
        "                new RuntimeShader(agslCode);\n"
        "                ok++;\n"
        "            } catch (Exception e) {\n"
        "                failures.add(name + \": \" + e.getMessage());\n"
        "            }\n"
        "        }\n"
        "\n"
        "        StringBuilder report = new StringBuilder();\n"
        "        report.append(String.format(\"\\nShader compilation: %d total, %d OK, %d AI-needed, %d failed\\n\",\n"
        "                total, ok, aiNeeded, failures.size()));\n"
        "        for (String f : failures) {\n"
        "            report.append(\"  FAIL: \").append(f).append(\"\\n\");\n"
        "        }\n"
        "        System.out.println(report);\n"
        "\n"
        "        assertTrue(\n"
        "                failures.size() + \" shaders failed to compile:\\n\" + report,\n"
        "                failures.isEmpty()\n"
        "        );\n"
        "    }\n"
        "}\n"
    )
    (android_test_dir / "ShaderCompilationTest.java").write_text(test_code, encoding="utf-8")
    print("  Written ShaderCompilationTest.java")

    # Copy converted_shaders.json to test assets
    if converted_file and converted_file.exists():
        test_assets = output_dir / "app/src/androidTest/assets"
        test_assets.mkdir(parents=True, exist_ok=True)
        # Write only the filtered shaders for the test
        test_data = json.dumps(ok, indent=2, ensure_ascii=False)
        (test_assets / "converted_shaders.json").write_text(test_data, encoding="utf-8")
        print("  Written test assets/converted_shaders.json")

    print(f"\nDone! {len(ok)} shaders embedded. Project at: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate standalone Android project with AGSL shaders")
    parser.add_argument("--output", required=True, help="Output directory for the Android project")
    parser.add_argument("--shaders", default=None, help="Comma-separated shader names to include (default: all)")
    parser.add_argument("--json", default=str(PROJECT_ROOT / "output/converted_shaders.json"),
                        help="Path to converted_shaders.json")
    args = parser.parse_args()

    output_dir = Path(args.output)
    converted_file = Path(args.json)

    all_data = json.loads(converted_file.read_text(encoding="utf-8"))

    if args.shaders:
        names = [n.strip() for n in args.shaders.split(",")]
        data = [d for d in all_data if d.get("name") in names]
        if not data:
            print(f"ERROR: No matching shaders found for: {names}")
            print(f"Available: {[d.get('name') for d in all_data]}")
            return
    else:
        data = all_data

    generate_project(output_dir, data, converted_file)


if __name__ == "__main__":
    main()
