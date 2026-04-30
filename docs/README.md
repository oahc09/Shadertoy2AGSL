# Shadertoy → AGSL 转换器

## 1. 项目概述

构建一个 Claude Code 技能，实现 Shadertoy 着色器到 Android AGSL 的自动转换，生成完整可运行的 Android 项目。

### 1.1 需求摘要

| 项目 | 决策 |
|------|------|
| 工具形态 | Claude Code 技能 |
| 支持范围 | 基础 fragment shader 优先，逐步扩展 |
| 输出内容 | 完整可运行 Android 组件 |
| UI 框架 | 传统 View 系统 |
| 转换机制 | 规则引擎 + AI 兜底（混合方案） |
| 项目结构 | 完整 Android 项目 |
| 输入方式 | 支持粘贴代码和 Shadertoy URL |
| 交互功能 | 完整控制面板（播放/暂停/速度/截图） |
| API 等级 | API 34+（Android 14+） |
| 批量处理 | 多着色器支持 |
| 开发语言 | Java |

### 1.2 整体架构

```
用户输入（URL / 代码）
        │
        ▼
┌─────────────────┐
│   输入解析器     │  ← Shadertoy URL 抓取 / 代码直接解析
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   规则引擎       │  ← GLSL → AGSL 已知模式转换
│  (确定性转换)    │     uniform 映射、函数签名、纹理采样等
└────────┬────────┘
         │
    ┌────┴────┐
    │ 全部转换 │─── 是 ──▶ 生成 Android 项目
    │  成功？  │
    └────┬────┘
         │ 否
         ▼
┌─────────────────┐
│   AI 兜底        │  ← Claude 处理未识别的复杂模式
│  (语义转换)      │     自定义函数、算法逻辑等
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   项目生成器     │  ← 输出完整 Android 项目
│  (模板填充)      │     Gradle + Activity + View + 多 shader
└─────────────────┘
```

### 1.3 目录结构

```
D:/AI/Shadertoy2AGSL/
├── .claude/skills/shadertoy2agsl.md   # 技能定义
├── scripts/                            # 所有脚本
│   ├── __init__.py
│   ├── converter.py                    # 顶层转换入口
│   ├── project_generator.py            # 项目生成器
│   └── rules/                          # 转换规则引擎
│       ├── __init__.py
│       ├── engine.py
│       ├── markers.py
│       └── patterns/                   # 各转换模式
│           ├── coordinates.py
│           ├── entry.py
│           ├── preprocessor.py
│           ├── textures.py
│           ├── types.py
│           └── uniforms.py
├── references/                         # Android 项目模板
│   ├── app/
│   ├── build.gradle.kts.tmpl
│   ├── settings.gradle.kts.tmpl
│   ├── gradle.properties.tmpl
│   └── gradle/wrapper/
├── tests/                              # 测试
│   ├── conftest.py
│   ├── pytest.ini
│   └── ...
└── docs/
    └── README.md                       # 本文档
```

---

## 2. AGSL 语言参考

Android Graphics Shading Language (AGSL) is used by Android 13 and above to define the behavior of programmable `RuntimeShader` objects. AGSL shares much of its syntax with GLSL fragment shaders, but works within the Android graphics rendering system to both customize painting within `Canvas` and filter `View` content.

### 2.1 Theory of operation

AGSL effects exist as part of the larger Android graphics pipeline. When Android issues a GPU accelerated drawing operation, it assembles a single GPU fragment shader to do the required work. This shader typically includes several pieces:

- Evaluating whether a pixel falls inside or outside of the shape being drawn (or on the border, where it might apply anti-aliasing).
- Evaluating whether a pixel falls inside or outside of the clipping region.
- Logic for the `Shader` on the `Paint`. The Shader can actually be a tree of objects (due to `ComposeShader` and other features).
- Similar logic for the `ColorFilter`.
- Blending code (for certain types of `BlendMode`).
- Color space conversion code, as part of Android's color management.

Your AGSL effect contributes a function (or functions) to the GPU's fragment shader.

### 2.2 Basic syntax

AGSL (and GLSL) are C-style domain specific languages. Types such as `bool` and `int` closely track their C equivalents; there are additional types to support vectors and matrices.

Qualifiers can be applied to types for precision hints. Control structures such as `if-else` statements work much like they do in C; the language also provides support for `switch` statements and `for` loops with limitations.

AGSL supports functions; every shader program begins with the `main` function. User defined functions are supported, without support for recursion. Functions use a "value-return" calling convention; values passed to functions are copied into parameters when the function is called, and outputs are copied back; this is determined by the `in`, `out`, and `inout` qualifiers.

AGSL fixes its GLSL feature set at GLSL ES 1.0 (the shading language used by OpenGL ES 2.0) to provide for maximum device reach.

### 2.3 Shader execution

An AGSL shader begins execution in a main function. Unlike GLSL, the function takes the shader position in "local" coordinates as a parameter. Your shader then returns the pixel color as a `vec4` in medium or high precision.

```glsl
mediump vec4 main(in vec2 fragCoord)
```

### 2.4 Coordinate space

AGSL and GLSL use different coordinate spaces by default. In GLSL, the fragment coordinate (fragCoord) is relative to the lower left. AGSL matches the screen coordinate system of Canvas, which means that the Y axis begins from the upper left corner. To convert between these two spaces:

```glsl
// AGSL to GLSL coordinate space transformation matrix
val localMatrix = Matrix()
localMatrix.postScale(1.0f, -1.0f)
localMatrix.postTranslate(0.0f, viewHeight)
gridShader.setLocalMatrix(localMatrix)
```

Or inject `fragCoord.y = iResolution.y - fragCoord.y;` at the start of main.

### 2.5 Precision and types

GLSL compatible precision modifiers are supported, but AGSL introduces `half` and `short` types which also represent medium precision.

Vector types: `float2` instead of `vec2`, `bool4` instead of `bvec4`.
Matrix types: `float3x3` instead of `mat3`. AGSL also allows GLSL-style declarations for `mat` and `vec`.

#### Basic types

| Type | Description |
|---|---|
| `void` | No function return value or empty parameter list. |
| `bool, bvec2, bvec3, bvec4` / `bool2, bool3, bool4` | Boolean scalar/vector |
| `int, ivec2, ivec3, ivec4` / `int2, int3, int4` | `highp` signed integer/vector |
| `float, vec2, vec3, vec4` / `float2, float3, float4` | `highp` floating point scalar/vector |
| `short, short2, short3, short4` | `mediump int` signed integer/vector |
| `half, half2, half3, half4` | `mediump float` scalar/vector |
| `mat2, mat3, mat4` / `float2x2, float3x3, float4x4` | Float matrix |
| `half2x2, half3x3, half4x4` | `mediump float` matrix types |

#### Precision and range minimums

| Modifier | 'float' range | 'float' magnitude range | 'float' precision | 'int' range |
|---|---|---|---|---|
| highp | {-2^62, 2^62} | {2^-62, 2^62} | Relative: 2^-16 | {-2^16, 2^16} |
| mediump | {-2^14, 2^14} | {2^-14, 2^14} | Relative: 2^-10 | {-2^10, 2^10} |
| lowp | {-2, 2} | {2^-8, 2} | Absolute: 2^-8 | {-2^8, 2^8} |

### 2.6 Preprocessor

AGSL doesn't support GLSL style preprocessor directives. Convert `#define` statements to `const` variables. AGSL's compiler supports constant folding and branch elimination for const variables.

### 2.7 Color spaces

Android applications are color managed. For certain effects, such as physically accurate lighting, math should be done in a linear color space. AGSL provides:

```glsl
half3 toLinearSrgb(half3 color)
half3 fromLinearSrgb(half3 color)
```

#### Uniforms and color

You can label `half4`/`float4`/`vec4` with `layout(color)` to let Android know that the uniform will be used as a color:

```glsl
layout(color) uniform half4 iColor;  // Input color
uniform float2 iResolution;          // Viewport resolution (pixels)
```

### 2.8 Qualifiers

| Type | Description |
|---|---|
| `const` | Compile-time constant, or read-only function parameter. |
| `uniform` | Value does not change across the primitive being processed. |
| `in` | For passed-in function parameters. This is the default. |
| `out` | For passed-out function parameters. |
| `inout` | For parameters that are both passed in and out of a function. |

> **Note:** `attribute`, `varying`, and `invariant` are not supported. `discard` is not allowed.

### 2.9 Structures and arrays

Only 1-dimensional arrays are supported with an explicit array size:

```glsl
half[10] x;
half x[10];
```

Arrays cannot be returned from a function, copied, assigned or compared. Arrays can only be indexed using a constant or a loop variable.

### 2.10 Program control

| Function call | Call by value-return |
|---|---|
| Iteration | `for (<init>;<test>;<next>)` `{ break, continue }` |
| Selection | `if ( ) { }` `if ( ) { } else { }` `switch () { break, case }` |
| Jump | `break, continue, return` (discard is not allowed) |
| Entry | `half4 main(float2 fragCoord)` |

**For loop limitations:** Similar to GLSL ES 1.0, 'for' loops are limited; the compiler must be able to unroll the loop. The initializer, test condition, and `next` statement must use constants. The `next` statement is limited to `++, --, +=, or -=`.

### 2.11 Shader sampling (evaluation)

Sampler types aren't supported, but you can evaluate other shaders:

```glsl
uniform shader image;
image.eval(coord).a   // The alpha channel from the evaluated image shader
```

### 2.12 Built-in functions

**GT** (generic type) is `float`, `float2`, `float3`, `float4` or `half`, `half2`, `half3`, `half4`.

#### Angle & trigonometric functions

| Function | Description |
|---|---|
| `GT radians(GT degrees)` | Converts degrees to radians |
| `GT degrees(GT radians)` | Converts radians to degrees |
| `GT sin(GT angle)` | Standard sine |
| `GT cos(GT angle)` | Standard cosine |
| `GT tan(GT angle)` | Standard tangent |
| `GT asin(GT x)` | Returns angle whose sine is x |
| `GT acos(GT x)` | Returns angle whose cosine is x |
| `GT atan(GT y, GT x)` | Returns angle whose arctangent is y/x |
| `GT atan(GT y_over_x)` | Returns angle whose arctangent is y_over_x |

#### Exponential functions

| Function | Description |
|---|---|
| `GT pow(GT x, GT y)` | Returns x^y |
| `GT exp(GT x)` | Returns e^x |
| `GT log(GT x)` | Returns ln(x) |
| `GT exp2(GT x)` | Returns 2^x |
| `GT log2(GT x)` | Returns log2(x) |
| `GT sqrt(GT x)` | Returns sqrt(x) |
| `GT inversesqrt(GT x)` | Returns 1/sqrt(x) |

#### Common functions

| Function | Description |
|---|---|
| `GT abs(GT x)` | Absolute value |
| `GT sign(GT x)` | Returns -1.0, 0.0, or 1.0 |
| `GT floor(GT x)` | Nearest integer <= x |
| `GT ceil(GT x)` | Nearest integer >= x |
| `GT fract(GT x)` | Fractional part of x |
| `GT mod(GT x, GT y)` | Value of x modulo y |
| `GT min(GT x, GT y)` | Minimum value |
| `GT max(GT x, GT y)` | Maximum value |
| `GT clamp(GT x, GT minVal, GT maxVal)` | x clamped between min and max |
| `GT saturate(GT x)` | x clamped between 0.0 and 1.0 |
| `GT mix(GT x, GT y, GT a)` | Linear blend of x and y |
| `GT step(GT edge, GT x)` | 0.0 if x < edge, else 1.0 |
| `GT smoothstep(GT edge0, GT edge1, GT x)` | Hermite interpolation between 0 and 1 |

#### Geometric functions

| Function | Description |
|---|---|
| `float/half length(GT x)` | Length of vector |
| `float/half distance(GT p0, GT p1)` | Distance between points |
| `float/half dot(GT x, GT y)` | Dot product |
| `float3/half3 cross(float3/half3 x, float3/half3 y)` | Cross product |
| `GT normalize(GT x)` | Normalize vector to length 1 |
| `GT faceforward(GT N, GT I, GT Nref)` | Returns N if dot(Nref, I) < 0, else -N |
| `GT reflect(GT I, GT N)` | Reflection direction |
| `GT refract(GT I, GT N, float/half eta)` | Refraction vector |

#### Matrix functions

| Function | Description |
|---|---|
| `mat matrixCompMult(mat x, mat y)` | Component-wise multiply |
| `mat inverse(mat m)` | Inverse of m |

#### Vector relational functions

| Function | Description |
|---|---|
| `BV lessThan(T x, T y)` | x < y |
| `BV lessThanEqual(T x, T y)` | x <= y |
| `BV greaterThan(T x, T y)` | x > y |
| `BV greaterThanEqual(T x, T y)` | x >= y |
| `BV equal(T x, T y)` | x == y |
| `BV notEqual(T x, T y)` | x != y |
| `bool any(BV x)` | true if any component is true |
| `bool all(BV x)` | true if all components are true |
| `BV not(BV x)` | Logical complement |

#### Color functions

| Function | Description |
|---|---|
| `vec4 unpremul(vec4 color)` | Converts to non-premultiplied alpha |
| `half3 toLinearSrgb(half3 color)` | Color space transformation to linear SRGB |
| `half3 fromLinearSrgb(half3 color)` | Color space transformation from linear SRGB |

---

## 3. Shadertoy 参考

### 3.1 图像着色器

通过计算每个像素的颜色来生成过程图像，着色器需要执行 `mainImage()` 函数：

```glsl
void mainImage( out vec4 fragColor, in vec2 fragCoord );
```

- `fragCoord`：像素坐标，范围从 0.5 到 resolution-0.5
- `fragColor`：输出颜色（四位向量）
- `iResolution`：渲染分辨率

### 3.2 声音着色器

```glsl
vec2 mainSound( float time )
```

`time` 是以秒为单位的声音样本时间，以 `iSampleRate`（通常 44100 或 48000）采样率采样。返回立体声波幅。

### 3.3 虚拟现实着色器

```glsl
void mainVR( out vec4 fragColor, in vec2 fragCoord, in vec3 fragRayOri, in vec3 fragRayDir )
```

### 3.4 统一变量输入

```glsl
uniform vec3 iResolution;        // 视口分辨率
uniform float iTime;             // 播放时间（秒）
uniform float iTimeDelta;        // 帧间隔时间
uniform float iFrame;            // 当前帧数
uniform float iChannelTime[4];   // 通道时间
uniform vec4 iMouse;             // 鼠标坐标
uniform vec4 iDate;              // 日期 (年,月,日,秒)
uniform float iSampleRate;       // 采样率
uniform vec3 iChannelResolution[4]; // 通道分辨率
uniform samplerXX iChanneli;     // 纹理通道
```

### 3.5 Shadertoy API

**查询着色器：**
```
GET https://www.shadertoy.com/api/v1/shaders/query/string?key=appkey
```

**获取单个着色器：**
```
GET https://www.shadertoy.com/api/v1/shaders/shaderID?key=appkey
```

**获取所有着色器：**
```
GET https://www.shadertoy.com/api/v1/shaders?key=appkey
```

**高级查询参数：**
- `sort=name|love|popular|newest|hot`
- `from=N&num=M`（分页）
- `filter=vr|soundoutput|soundinput|webcam|multipass|musicstream`

---

## 4. 设计规格

### 4.1 模块设计

#### 输入解析器

- Shadertoy URL 解析：提取 shader ID，调用 API 获取 GLSL 代码
- 代码直接解析：用户粘贴的 GLSL 代码直接使用
- API Key：配置中存储默认 Key，用户可通过 `SHADERTOY_API_KEY` 环境变量覆盖

#### 规则引擎

Python 脚本实现，处理确定性转换模式：

| 类别 | Shadertoy (GLSL) | AGSL | 处理方式 |
|------|------------------|------|----------|
| 入口函数 | `void mainImage(out vec4 fragColor, in vec2 fragCoord)` | `float4 main(float2 fragCoord)` | 正则替换 |
| 坐标系 | Y 轴从左下开始 | Y 轴从左上开始 | 注入 Y 翻转 |
| 精度类型 | 默认 `float` | 使用 `float` 系列 | `vec` → `float` 系列 |
| 纹理采样 | `texture(iChannel0, uv)` | `iChannel0.eval(uv)` | 正则替换 |
| 纹理声明 | `uniform sampler2D iChannel0` | `uniform shader iChannel0` | 正则替换 |
| 预处理器 | `#define X 1.0` | 不支持 | 转为 `const float X = 1.0` |
| 内置 Uniform | 自动可用 | 需手动声明 | 自动注入声明 |
| 数组 | 完整支持 | 仅 1D | 标记供 AI 兜底 |
| discard | 支持 | 不支持 | 标记供 AI 兜底 |

#### AI 兜底机制

触发条件：
- 规则引擎输出的"未处理片段"列表不为空
- 检测到 `discard` 语句（需重写为条件返回）
- 检测到多维数组或数组返回
- 检测到递归函数调用

### 4.2 Android 项目生成

**项目结构：**
```
ShadertoyApp/
├── app/
│   ├── build.gradle.kts          # minSdk 34, targetSdk 35
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── java/com/example/shadertoy/
│   │   │   ├── MainActivity.java
│   │   │   ├── ShaderView.java
│   │   │   ├── ShaderControls.java
│   │   │   └── ShaderData.java
│   │   └── res/
│   │       ├── layout/
│   │       │   ├── activity_main.xml
│   │       │   └── view_shader_controls.xml
│   │       └── values/strings.xml
│   └── proguard-rules.pro
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
└── gradle/wrapper/
```

**核心组件：**

- **ShaderView.java** — RuntimeShader + SystemClock 动画 + 触摸 Y 翻转
- **ShaderControls.java** — 播放/暂停、速度滑块、截图按钮
- **MainActivity.java** — ViewPager2 多 shader 切换

### 4.3 编译与视觉保真度保证

#### 编译（构建时）
- `AndroidManifest.xml` 省略 `android:icon` 避免缺少资源错误
- `activity_main.xml` 使用 `<include>` 引入控制面板
- `settings.gradle.kts` 使用 `dependencyResolutionManagement`
- `iResolution` 声明为 `uniform float3` 匹配 3-float `setFloatUniform` 调用
- 包含 `proguard-rules.pro` 和 `gradle.properties`

#### 视觉保真度（运行时）
- 使用 `float` 而非 `half`：16-bit half 在迭代着色器中产生色带
- 动画使用 `SystemClock.uptimeMillis()` + 20ms ValueAnimator 帧tick
- 触摸 Y 翻转：`y = getHeight() - event.getY()`
- 截图使用 `Canvas.draw()` 替代废弃的 `getDrawingCache()`
- 存储使用 `getExternalFilesDir()` 无需权限

---

## 5. 实现计划

> 实际代码已按 TDD 方式实现，以下为原始计划记录。

### Task 1: 项目脚手架

创建目录结构、`__init__.py` 文件和 pytest 配置。

### Task 2: Entry Pattern（mainImage → main）

将 `void mainImage(out vec4 fragColor, in vec2 fragCoord)` 转换为 `float4 main(float2 fragCoord)`，将 `fragColor = ...` 替换为 `return ...`。

### Task 3: Uniforms Pattern

检测 Shadertoy 内置 uniform 使用，注入 AGSL 声明（`uniform float3 iResolution;` 等）。

### Task 4: Types Pattern

将 `vec2/vec3/vec4/mat2/mat3/mat4` 转换为 `float2/float3/float4/float2x2/float3x3/float4x4`。

### Task 5: Textures Pattern

将 `sampler2D` 声明转换为 `shader`，将 `texture(iChannel0, uv)` 转换为 `iChannel0.eval(uv)`。

### Task 6: Preprocessor Pattern

将 `#define X 1.0` 转换为 `const float X = 1.0;`。

### Task 7: Coordinates Pattern

在 main 函数体开头注入 `fragCoord.y = iResolution.y - fragCoord.y;`。

### Task 8: Markers 模块

检测需要 AI 兜底的模式（discard、多维数组、递归）。

### Task 9: Rule Engine

串联所有 pattern，按序执行管道，输出 ConversionResult。

### Task 10: Converter 顶层入口

封装规则引擎 + AI 兜底判断，输出 ConverterOutput。

### Task 11: Android 模板

创建 14 个 .tmpl 模板文件覆盖完整 Android 项目。

### Task 12: Project Generator

模板填充引擎，替换 `{{placeholders}}` 并写入文件。

### Task 13: 集成测试

端到端测试：GLSL → AGSL → Android 项目生成。

### Task 14: 技能定义

编写 `.claude/skills/shadertoy2agsl.md` 定义技能触发条件和工作流。
