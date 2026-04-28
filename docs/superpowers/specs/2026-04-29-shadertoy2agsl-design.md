# Shadertoy → AGSL 一键转换技能设计

## 概述

构建一个 Claude Code 技能，实现 Shadertoy 着色器到 Android AGSL 的自动转换，生成完整可运行的 Android 项目。

## 需求摘要

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

## 整体架构

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

## 模块设计

### 1. 输入解析器

**功能**：
- Shadertoy URL 解析：提取 shader ID，调用 Shadertoy API 获取 GLSL 代码
- 代码直接解析：用户粘贴的 GLSL 代码直接使用

**Shadertoy API 调用**：
```
GET https://www.shadertoy.com/api/v1/shaders/{shaderID}?key={API_KEY}
```

返回 JSON 包含 shader 代码和输入资源（纹理、音频等）。

**API Key 处理**：
- 技能配置中存储默认 API Key（由技能维护者提供）
- 用户可通过环境变量 `SHADERTOY_API_KEY` 覆盖
- 若 API 调用失败，提示用户手动粘贴代码作为备选方案

### 2. 规则引擎

Python 脚本实现，处理确定性转换模式。

**核心转换规则**：

| 类别 | Shadertoy (GLSL) | AGSL | 处理方式 |
|------|------------------|------|----------|
| 入口函数 | `void mainImage(out vec4 fragColor, in vec2 fragCoord)` | `half4 main(float2 fragCoord)` | 正则替换 |
| 坐标系 | Y 轴从左下开始 | Y 轴从左上开始 | 注入 `fragCoord.y = iResolution.y - fragCoord.y` |
| 精度类型 | 默认 `float` | 推荐 `half` 系列 | `vec` → `half` 系列 |
| 纹理采样 | `texture(iChannel0, uv)` | `iChannel0.eval(uv)` | 正则替换 |
| 纹理声明 | `uniform sampler2D iChannel0` | `uniform shader iChannel0` | 正则替换 |
| 预处理器 | `#define X 1.0` | 不支持 | 转为 `const float X = 1.0` |
| 内置 Uniform | 自动可用 | 需手动声明 | 自动注入声明 |
| 数组 | 完整支持 | 仅 1D | 标记供 AI 兜底 |
| discard | 支持 | 不支持 | 标记供 AI 兜底 |

**规则引擎架构**：
```
rules/
├── engine.py          # 主引擎：逐行扫描 + 模式匹配
├── patterns/
│   ├── entry.py       # mainImage → main 转换
│   ├── uniforms.py    # uniform 声明转换
│   ├── types.py       # vec → half 类型转换
│   ├── textures.py    # sampler2D → shader + eval
│   ├── preprocessor.py # #define → const
│   └── coordinates.py # Y 轴翻转注入
└── markers.py         # 标记无法处理的片段供 AI 兜底
```

**输出**：
- 转换后的 AGSL 代码
- 未处理片段列表
- 转换报告（应用了哪些规则，跳过了哪些）

### 3. AI 兜底机制

当规则引擎遇到无法处理的代码片段时，交给 Claude 进行语义转换。

**触发条件**：
- 规则引擎输出的"未处理片段"列表不为空
- 检测到 `discard` 语句（需重写为条件返回）
- 检测到多维数组或数组返回
- 检测到递归函数调用
- 检测到不支持的 GLSL 特性

**流程**：
1. 接收规则引擎输出的未处理片段
2. 提供上下文：原始 GLSL 代码 + 已转换的 AGSL 代码
3. Claude 将未处理片段转换为 AGSL 兼容写法
4. 合并到规则引擎输出的正确位置
5. 检查合并后的代码语法

### 4. Android 项目生成

**项目结构**：
```
ShadertoyApp/
├── app/
│   ├── build.gradle.kts          # minSdk 34, targetSdk 35
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── java/com/example/shadertoy/
│   │   │   ├── MainActivity.java       # 主界面：ViewPager 切换 shader
│   │   │   ├── ShaderView.java         # 自定义 View：RuntimeShader + 动画
│   │   │   ├── ShaderControls.java     # 控制面板：播放/暂停/速度/截图
│   │   │   └── ShaderData.java         # 数据类：shader 名称 + 代码 + 元信息
│   │   ├── assets/
│   │   │   └── shaders/              # AGSL 着色器文件
│   │   │       ├── shader1.agsl
│   │   │       └── shader2.agsl
│   │   ├── res/
│   │   │   ├── layout/
│   │   │   │   ├── activity_main.xml
│   │   │   │   └── view_shader_controls.xml
│   │   │   └── values/
│   │   │       └── strings.xml
│   └── proguard-rules.pro
├── build.gradle.kts              # 项目级 Gradle
├── settings.gradle.kts
└── gradle/
    └── wrapper/
```

**核心组件**：

**ShaderView.java** - 自定义 View：
- 加载 AGSL 着色器
- 通过 ValueAnimator 驱动 iTime
- 处理触摸事件映射到 iMouse
- 支持暂停/恢复
- 支持截图保存

**ShaderControls.java** - 控制面板：
- 播放/暂停按钮
- 速度滑块（0.25x ~ 4x）
- 截图按钮
- Shader 名称显示

**MainActivity.java** - 主界面：
- ViewPager2 支持多 shader 滑动切换
- 底部控制面板
- 支持全屏模式

## 技能工作流程

```
用户输入："转换这个 Shadertoy" + URL 或代码
        │
        ▼
┌─────────────────────────────────────────┐
│  步骤 1：输入解析                        │
│  - URL → 调用 Shadertoy API 获取代码    │
│  - 代码 → 直接使用                       │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  步骤 2：规则引擎转换                    │
│  - 运行 Python 脚本                     │
│  - 输出：AGSL 代码 + 未处理片段          │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  步骤 3：AI 兜底（如需要）               │
│  - Claude 处理未识别的复杂模式           │
│  - 合并到最终 AGSL 代码                  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  步骤 4：项目生成                        │
│  - 填充 Java 模板                       │
│  - 生成完整 Android 项目                 │
│  - 打包为 zip 或直接写入目录             │
└─────────────────────────────────────────┘
```

## 触发方式

```
用户：/shadertoy2agsl https://www.shadertoy.com/view/XsXXD
用户：/shadertoy2agsl [粘贴 GLSL 代码]
用户：转换 Shadertoy [URL 或代码]
```

## 输出物

1. **转换报告**：哪些规则应用了，哪些需要 AI 兜底
2. **AGSL 着色器代码**：带注释说明改动
3. **完整 Android 项目**：可直接编译运行
4. **使用说明**：如何集成到现有项目

## 未来扩展

- 多 buffer 支持（A/B/C/D）
- 音频输入支持
- CubeMap 支持
- VR 着色器支持
- Jetpack Compose 版本
