Android Graphics Shading Language (AGSL) is used by Android 13 and above to
define the behavior of programmable
[`RuntimeShader`](https://developer.android.com/reference/android/graphics/RuntimeShader) objects. AGSL
shares much of its syntax with GLSL fragment shaders, but works within the
Android graphics rendering system to both customize painting within `Canvas`
and filter `View` content.

## Theory of operation

AGSL effects exist as part of the larger Android graphics pipeline. When Android
issues a GPU accelerated drawing operation, it assembles a single GPU fragment
shader to do the required work. This shader typically includes several pieces.
For example, it might include:

- Evaluating whether a pixel falls inside or outside of the shape being drawn (or on the border, where it might apply anti-aliasing).
- Evaluating whether a pixel falls inside or outside of the clipping region (again, with possible anti-aliasing logic for border pixels).
- Logic for the [`Shader`](https://developer.android.com/reference/android/graphics/Shader) on the [`Paint`](https://developer.android.com/reference/android/graphics/Paint). The Shader can actually be a tree of objects (due to [`ComposeShader`](https://developer.android.com/reference/android/graphics/ComposeShader) and other features described below).
- Similar logic for the [`ColorFilter`](https://developer.android.com/reference/android/graphics/ColorFilter).
- Blending code (for certain types of [`BlendMode`](https://developer.android.com/reference/android/graphics/BlendMode)).
- Color space conversion code, as part of Android's color management.
- When the `Paint` has a complex tree of objects in the `Shader`, `ColorFilter`, or `BlendMode` fields, there is still only a single GPU fragment shader. Each node in that tree creates a single function. The clipping code and geometry code each create a function. The blending code might create a function. The overall fragment shader then calls all of these functions (which may call other functions, e.g. in the case of a shader tree).

Your AGSL effect contributes a function (or functions) to the GPU's fragment shader.

## Basic syntax

AGSL (and GLSL) are C-style domain specific languages. Types such as `bool` and
`int` closely track their C equivalents; there are additional types to
support vectors and matrices that support domain functionality.

Qualifiers can be applied to types for precision hints in a way that's unique to shading languages. Control structures such as `if-else` statements work much
like they do in C; the language also provides support for `switch` statements
and `for` loops with limitations. Some control structures require constant expressions that can be evaluated at compile time.

AGSL supports functions; every shader program begins with the `main` function.
User defined functions are supported, without support for recursion of any kind.
Functions use a "value-return" calling convention; values passed to functions are
copied into parameters when the function is called, and outputs are copied
back; this is determined by the `in`, `out`, and `inout` qualifiers.


AGSL and GLSL are very similar in syntax, allowing many GLSL fragment shader
effects to be brought over to Android with minimal changes. AGSL fixes its GLSL
feature set at GLSL ES 1.0 (the shading language used by OpenGL ES 2.0) to
provide for maximum device reach.

A GLSL fragment shader controls the entire behavior of the GPU between the
rasterizer and the blending hardware. That shader does all the work to compute a
color, and the color it generates is exactly what is fed to the blending stage
of the pipeline. When you write a shader in AGSL, you are programming a stage of
the Android graphics pipeline. Many of the language differences stem from this.

## Shader execution

Just like in a GLSL shader, an AGSL shader begins execution in a main function.
Unlike GLSL, the function takes the shader position in "local" coordinates as a
parameter. This is similar to `gl_FragCoord`, but rather than framebuffer
coordinates, these coordinates may have been translated prior to calling your
shader. Your shader then returns the pixel color as a `vec4` in medium or
high precision (similar to `out vec4 color` or `gl_FragColor` in GLSL).

    mediump vec4 main(in vec2 fragCoord)

## Coordinate space

![GLSL vs AGSL coordinate spaces](https://developer.android.com/static/images/guide/topics/graphics/agsl/agsl-coordinate-glsl-vs-agsl.png)

*Shader drawn using GLSL vs [Near identical shader drawn using AGSL](https://shaders.skia.org/?id=9dc5c7170e82d49c47a3ee20d679ad5bef45b5ca7e23c4327dd93b8d3101256f)*

AGSL and GLSL use different coordinate spaces by default. In GLSL, the fragment
coordinate (fragCoord) is relative to the lower left. AGSL matches the screen
coordinate system of [Canvas](https://developer.android.com/reference/android/graphics/Canvas),
which means that the Y axis begins from the upper left corner. If needed, you
can convert between these two spaces by passing in the resolution as a uniform
and using `resolution.y - fragCoord.y` for the Y axis value. Alternatively, you
can apply a local transformation matrix to your shader.

    // AGSL to GLSL coordinate space transformation matrix
    val localMatrix = Matrix()
    localMatrix.postScale(1.0f, -1.0f)
    localMatrix.postTranslate(0.0f, viewHeight)
    gridShader.setLocalMatrix(localMatrix)

## Precision and types

GLSL compatible precision modifiers are supported, but AGSL introduces
`half` and `short` types which also represent medium precision.

Vector types can be declared as named \<base type\>\<columns\>. You can use
`float2` instead of `vec2` and `bool4` instead of `bvec4`.
Matrix types can be declared as named \<base type\>\<columns\>x\<rows\>, so
`float3x3` instead of `mat3`. AGSL also allows GLSL-style declarations
for `mat` and `vec` and these types are mapped to their float
equivalents.

## Preprocessor

AGSL doesn't support GLSL style
[preprocessor](https://www.khronos.org/opengl/wiki/Core_Language_(GLSL)#Preprocessor_directives)
directives. Convert #define statements to const variables. AGSL's compiler
supports constant folding and branch elimination for const variables, so these
will be efficient.

## Color spaces

Android Applications are color managed. The color space of a Canvas determines
the working color space for drawing. Source content (like shaders, including
[BitmapShader](https://developer.android.com/reference/android/graphics/BitmapShader))
also have color spaces.

For certain effects, such as physically accurate lighting, math should be done
in a linear color space. To help with this, AGSL provides these intrinsic
functions:

    half3 toLinearSrgb(half3 color)
    half3 fromLinearSrgb(half3 color)

These convert colors between the working color space and Android's
[`LINEAR_EXTENDED_SRGB`](https://developer.android.com/reference/android/graphics/ColorSpace.Named#LINEAR_EXTENDED_SRGB)
color space. That space uses the sRGB color primaries (gamut), and a linear
transfer function. It represents values outside of the sRGB gamut using extended
range values (below 0.0 and above 1.0).

### Uniforms

Since AGSL doesn't know if uniforms contain colors, it won't automatically apply
a color conversion to them. You can label `half4`/`float4`/`vec4` with
`layout(color)`, which lets Android know that the uniform will be used as a
color, allowing Android to transform the uniform value to the working color
space.

In AGSL, declare the uniform like this:

    layout(color) uniform half4 iColor;  // Input color
    uniform float2 iResolution;          // Viewport resolution (pixels)

In Android code, you can then set the uniform like this:

    shader.setColorUniform("iColor", Color.GREEN)
    shader.setFloatUniform("iResolution", canvas.width.toFloat(), canvas.height.toFloat())



This page covers AGSL basics, and different ways to use AGSL in your Android
app.

## A simple AGSL shader

Your shader code is called for each drawn pixel, and returns the color the pixel
should be painted with. An extremely simple shader is one that always returns
a single color; this example uses red. The shader is defined inside of a `String`.

### Kotlin

```kotlin
private const val COLOR_SHADER_SRC =
   """half4 main(float2 fragCoord) {
      return half4(1,0,0,1);
   }"""
```

### Java

```java
private static final String COLOR_SHADER_SRC =
   "half4 main(float2 fragCoord) {\n" +
      "return half4(1,0,0,1);\n" +
   "}";
```

The next step is to create a [`RuntimeShader`](https://developer.android.com/reference/android/graphics/RuntimeShader)
object initialized with your shader string. This also compiles the shader.

### Kotlin

```kotlin
val fixedColorShader = RuntimeShader(COLOR_SHADER_SRC)
```

### Java

```java
RuntimeShader fixedColorShader = new RuntimeShader(COLOR_SHADER_SRC);
```

Your `RuntimeShader` can be used anywhere a standard Android shader can. As an
example, you can use it to draw into a custom `View` using a
[`Canvas`](https://developer.android.com/reference/android/graphics/Canvas).

### Kotlin

```kotlin
val paint = Paint()
paint.shader = fixedColorShader
override fun onDrawForeground(canvas: Canvas?) {
   canvas?.let {
      canvas.drawPaint(paint) // fill the Canvas with the shader
   }
}
```

### Java

```java
Paint paint = new Paint();
paint.setShader(fixedColorShader);
public void onDrawForeground(@Nullable Canvas canvas) {
   if (canvas != null) {
      canvas.drawPaint(paint); // fill the Canvas with the shader
   }
}
```

This draws a red `View`. You can use a `uniform` to pass a color parameter into
the shader to be drawn. First, add the color `uniform` to the shader:

### Kotlin

```kotlin
private const val COLOR_SHADER_SRC =
"""layout(color) uniform half4 iColor;
   half4 main(float2 fragCoord) {
      return iColor;
   }"""
```

### Java

```java
private static final String COLOR_SHADER_SRC =
   "layout(color) uniform half4 iColor;\n"+
      "half4 main(float2 fragCoord) {\n" +
      "return iColor;\n" +
   "}";
```

Then, call `setColorUniform` from your custom `View` to pass the desired color
into the AGSL shader.

### Kotlin

```kotlin
fixedColorShader.setColorUniform("iColor", Color.GREEN )
```

### Java

```java
fixedColorShader.setColorUniform("iColor", Color.GREEN );
```

Now, you get a green `View`; the `View` color is controlled using a
parameter from code in your custom `View` instead of being embedded in the
shader.

You can create a color gradient effect instead. You'll first need to change
the shader to accept the `View` resolution as input:

### Kotlin

```kotlin
private const val COLOR_SHADER_SRC =
"""uniform float2 iResolution;
   half4 main(float2 fragCoord) {
      float2 scaled = fragCoord/iResolution.xy;
      return half4(scaled, 0, 1);
   }"""
```

### Java

```java
private static final String COLOR_SHADER_SRC =
   "uniform float2 iResolution;\n" +
      "half4 main(float2 fragCoord) {\n" +
      "float2 scaled = fragCoord/iResolution.xy;\n" +
      "return half4(scaled, 0, 1);\n" +
   "}";
```

## Drawing the gradient

This shader does something slightly fancy. For each pixel, it creates a `float2`
vector that contains the x and y coordinates divided by the resolution, which
will create a value between zero and one. It then uses that scaled vector to
construct the red and green components of the return color.

You pass the resolution of the `View` into an AGSL shader `uniform` by calling
`setFloatUniform`.

### Kotlin

```kotlin
val paint = Paint()
paint.shader = fixedColorShader
override fun onDrawForeground(canvas: Canvas?) {
   canvas?.let {
      fixedColorShader.setFloatUniform("iResolution", width.toFloat(), height.toFloat())
      canvas.drawPaint(paint)
   }
}
```

### Java

```java
Paint paint = new Paint();
paint.setShader(fixedColorShader);
public void onDrawForeground(@Nullable Canvas canvas) {
   if (canvas != null) {
      fixedColorShader.setFloatUniform("iResolution", (float)getWidth(), (float()getHeight()));
      canvas.drawPaint(paint);
   }
}
```
![Red and Green gradient](https://developer.android.com/static/images/guide/topics/graphics/agsl/agsl-gradient.png) Red and green gradient

## Animating the shader

You can use a similar technique to animate the shader by modifying it to receive `iTime` and `iDuration` uniforms. The shader will use these values to create a
triangular wave for the colors, causing them to cycle back and forth across their gradient values.

### Kotlin

```kotlin
private const val DURATION = 4000f
private const val COLOR_SHADER_SRC = """
   uniform float2 iResolution;
   uniform float iTime;
   uniform float iDuration;
   half4 main(in float2 fragCoord) {
      float2 scaled = abs(1.0-mod(fragCoord/iResolution.xy+iTime/(iDuration/2.0),2.0));
      return half4(scaled, 0, 1.0);
   }
"""
```

### Java

```java
private static final float DURATION = 4000f;
private static final String COLOR_SHADER_SRC =
   "uniform float2 iResolution;\n"+
   "uniform float iTime;\n"+
   "uniform float iDuration;\n"+
   "half4 main(in float2 fragCoord) {\n"+
      "float2 scaled = abs(1.0-mod(fragCoord/iResolution.xy+iTime/(iDuration/2.0),2.0));\n"+
      "return half4(scaled, 0, 1.0);\n"+
   "}";
```

From the custom view source code, a
[`ValueAnimator`](https://developer.android.com/reference/android/animation/ValueAnimator) updates the
`iTime` uniform.

### Kotlin

```kotlin
// declare the ValueAnimator
private val shaderAnimator = ValueAnimator.ofFloat(0f, DURATION)

// use it to animate the time uniform
shaderAnimator.duration = DURATION.toLong()
shaderAnimator.repeatCount = ValueAnimator.INFINITE
shaderAnimator.repeatMode = ValueAnimator.RESTART
shaderAnimator.interpolator = LinearInterpolator()

animatedShader.setFloatUniform("iDuration", DURATION )
shaderAnimator.addUpdateListener { animation ->
    animatedShader.setFloatUniform("iTime", animation.animatedValue as Float )
}
shaderAnimator.start()
```

### Java

```java
// declare the ValueAnimator
private final ValueAnimator shaderAnimator = ValueAnimator.ofFloat(0f, DURATION);

// use it to animate the time uniform
shaderAnimator.setDuration((long)DURATION);
shaderAnimator.setRepeatCount(ValueAnimator.INFINITE);
shaderAnimator.setRepeatMode(ValueAnimator.RESTART);
shaderAnimator.setInterpolator(new LinearInterpolator());

animatedShader.setFloatUniform("iDuration", DURATION );
shaderAnimator.addUpdateListener(new ValueAnimator.AnimatorUpdateListener() {
   public final void onAnimationUpdate(ValueAnimator animation) {
      animatedShader.setFloatUniform("iTime", (float)animation.getAnimatedValue());
   }
});
```
![Red and Green animated gradient](https://developer.android.com/static/images/guide/topics/graphics/agsl/agsl-animated-gradient.gif) Red and Green animated gradient

## Painting complex objects

You don't have to draw the shader to fill the background; it can be
used in any place that accepts a
[`Paint`](https://developer.android.com/reference/android/graphics/Paint) object, such as
[`drawText`](https://developer.android.com/reference/android/graphics/Canvas#drawText(java.lang.String,%20float,%20float,%20android.graphics.Paint)).

### Kotlin

```kotlin
canvas.drawText(ANIMATED_TEXT, TEXT_MARGIN_DP, TEXT_MARGIN_DP + bounds.height(),
   paint)
```

### Java

```java
canvas.drawText(ANIMATED_TEXT, TEXT_MARGIN_DP, TEXT_MARGIN_DP + bounds.height(),
   paint);
```
![Red and Green animated gradient text](https://developer.android.com/static/images/guide/topics/graphics/agsl/agsl-animated-gradient-text.gif) Red and Green animated gradient text

## Shading and Canvas transformations

You can apply additional `Canvas` transformations on your shaded text, such as
rotation. In the `ValueAnimator`, you can update a matrix for 3D rotations
using the built-in
[`android.graphics.Camera`](https://developer.android.com/reference/android/graphics/Camera) class.

### Kotlin

```kotlin
// in the ValueAnimator
camera.rotate(0.0f, animation.animatedValue as Float / DURATION * 360f, 0.0f)
```

### Java

```java
// in the ValueAnimator
camera.rotate(0.0f, (Float)animation.getAnimatedValue() / DURATION * 360f, 0.0f);
```

Since you want to rotate the text from the center axis rather than from the corner,
get the text bounds and then use `preTranslate` and `postTranslate` to alter the
matrix to translate the text so that 0,0 is the center of the rotation without
changing the position the text is drawn on the screen.

### Kotlin

```kotlin
linearColorPaint.getTextBounds(ANIMATED_TEXT, 0, ANIMATED_TEXT.length, bounds)
camera.getMatrix(rotationMatrix)
val centerX = (bounds.width().toFloat())/2
val centerY = (bounds.height().toFloat())/2
rotationMatrix.preTranslate(-centerX, -centerY)
rotationMatrix.postTranslate(centerX, centerY)
canvas.save()
canvas.concat(rotationMatrix)
canvas.drawText(ANIMATED_TEXT, 0f, 0f + bounds.height(), paint)
canvas.restore()
```

### Java

```java
linearColorPaint.getTextBounds(ANIMATED_TEXT, 0, ANIMATED_TEXT.length(), bounds);
camera.getMatrix(rotationMatrix);
float centerX = (float)bounds.width()/2.0f;
float centerY = (float)bounds.height()/2.0f;
rotationMatrix.preTranslate(-centerX, -centerY);
rotationMatrix.postTranslate(centerX, centerY);
canvas.save();
canvas.concat(rotationMatrix);
canvas.drawText(ANIMATED_TEXT, 0f, 0f + bounds.height(), paint);
canvas.restore();
```
![Red and Green rotating animated gradient text](https://developer.android.com/static/images/guide/topics/graphics/agsl/agsl-rotating-animated-gradient-text.gif) Red and Green rotating animated gradient text

## Using RuntimeShader with Jetpack Compose

It's even easier to use `RuntimeShader` if you're rendering your UI using
[Jetpack Compose](https://developer.android.com/jetpack/compose). Starting with the same gradient shader from
before:

    private const val COLOR_SHADER_SRC =
        """uniform float2 iResolution;
       half4 main(float2 fragCoord) {
       float2 scaled = fragCoord/iResolution.xy;
       return half4(scaled, 0, 1);
    }"""

You can apply that shader to a
[`ShaderBrush`](https://developer.android.com/reference/kotlin/androidx/compose/ui/graphics/ShaderBrush). You
then use the `ShaderBrush` as a parameter to the drawing commands within your
`Canvas`'s draw scope.

    // created as top level constants
    val colorShader = RuntimeShader(COLOR_SHADER_SRC)
    val shaderBrush = ShaderBrush(colorShader)

    Canvas(
       modifier = Modifier.fillMaxSize()
    ) {
       colorShader.setFloatUniform("iResolution",
       size.width, size.height)
       drawCircle(brush = shaderBrush)
    }

![AGSL Compose gradient circle](https://developer.android.com/static/images/guide/topics/graphics/agsl/agsl-compose-gradient-circle.png) Red and green gradient circle

## Using RuntimeShader with RenderEffect

You can use
[`RenderEffect`](https://developer.android.com/reference/android/graphics/RenderEffect) to apply a
[`RuntimeShader`](https://developer.android.com/reference/android/graphics/RuntimeShader) to a parent `View`
*and* all child views. This is more expensive than drawing a custom `View`. but
it allows you to easily create an effect that incorporates what would have
originally been drawn using
[`createRuntimeShaderEffect`](https://developer.android.com/reference/android/graphics/RenderEffect#createRuntimeShaderEffect(android.graphics.RuntimeShader,%20java.lang.String)).

### Kotlin

```kotlin
view.setRenderEffect(RenderEffect.createRuntimeShaderEffect(myShader, "background"))
```

### Java

```java
view.setRenderEffect(RenderEffect.createRuntimeShaderEffect(myShader, "background"));
```

The second parameter is the name of a shader uniform that you can `eval` with a
coordinate parameter (such as the passed in fragCoord) to get the original color
of the
[`RenderNode`](https://developer.android.com/reference/android/graphics/RenderNode) (the View and its child
views), allowing you to perform all sorts of effects.

    uniform shader background;       // Root node of View tree to be altered
    return mix(returnColor, background.eval(fragCoord), 0.5);

![Grid blended over button](https://developer.android.com/static/images/guide/topics/graphics/agsl/agsl-grid-blend.png) AGSL grid blended over button

A grid effect mixed over a button, but underneath a floating action button
(since it's in a different `View` hierarchy).


AGSL is designed to be largely compatible with GLSL ES 1.0. For more information,
see the equivalent function in the
[OpenGL ES Shading Language documentation](https://www.khronos.org/files/opengles_shading_language.pdf).
When possible, this documentation attempts to call out differences between AGSL
and GLSL.

## Types

AGSL supports GLSL ES 1.0 types along with an additional way to represent vector
and matrix types. AGSL supports additional `short` and `half` types to represent
medium precision.

### Basic types

| Type | Description |
|---|---|
| **`void`** | No function return value or empty parameter list. *Unlike in GLSL, functions without a void return type must return a value.* |
| **`bool, bvec2, bvec3, bvec4`** **`(bool2, bool3, bool4)`**. | Boolean scalar/vector |
| **`int, ivec2, ivec3, ivec4`** **`(int2, int3, int4)`** | `highp` signed integer/vector |
| **`float, vec2, vec3, vec4`** **`(float2, float3, float4)`** | `highp` (single precision) floating point scalar/vector |
| **`short, short2, short3, short4`** | equivalent to `mediump int` signed integer/vector |
| **`half, half2, half3, half4`** | equivalent to `mediump float` scalar/vector |
| **`mat2, mat3, mat4`** **`(float2x2, float3x3, float4x4)`** | 2x2, 3x3, 4x4 `float` matrix |
| **`half2x2, half3x3, half4x4`** | Equivalent to `mediump float` matrix types |

### Precision and range minimums

These are the minimum guaranteed precision and range associated with each
modifier based upon the OpenGL ES 2.0 specification. Since most devices
support ES 3.0, they will have more guaranteed `highp` precision/range and
`int mediump` range. Precision modifiers can be applied to scalar, vector, and
matrix variables and parameters. Only the minimums listed below are guaranteed;
`lowp` is not necessarily actually lower precision than `mediump`, and `mediump`
is not necessarily lower precision than `highp`. AGSL currently converts `lowp`
to `mediump` in the final output.

| Modifier | 'float' range | 'float' magnitude range | 'float' precision | 'int' range |
|---|---|---|---|---|
| highp | \\(\\left\\{-2\^{62},2\^{62}\\right\\}\\) | \\(\\left\\{2\^{-62},2\^{62}\\right\\}\\) | Relative: \\(2\^{-16}\\) | \\(\\left\\{-2\^{16},2\^{16}\\right\\}\\) |
| mediump | \\(\\left\\{-2\^{14},2\^{14}\\right\\}\\) | \\(\\left\\{2\^{-14},2\^{14}\\right\\}\\) | Relative: \\(2\^{-10}\\) | \\(\\left\\{-2\^{10},2\^{10}\\right\\}\\) |
| lowp | \\(\\left\\{-2,2\\right\\}\\) | \\(\\left\\{2\^{-8},2\\right\\}\\) | Absolute: \\(2\^{-8}\\) | \\(\\left\\{-2\^{8},2\^{8}\\right\\}\\) |

In addition to array numeric subscript syntax ex: `var[num]`, names of vector
components for vectors of length 2 - 4 are denoted by a single letter. Components
can be swizzled and replicated. ex: `vect.yx`, `vect.yy`

**`vect.xyzw`** - Use when accessing vectors that represent points/normals

**`vect.rgba`** - Use when accessing vectors that represent colors

**`vect.LTRB`** - Use when the vector represents a rectangle (not in GLSL)

In AGSL, 0 and 1 can be used to produce a constant 0 or 1 in that channel.
Ex: `vect.rgb1 == vec4(vect.rgb,1)`

### Structures and arrays

Structures are declared with the same syntax as GLSL, but AGSL only supports
structures at global scope.

    struct type-name {
     members
    } struct-name; // optional variable declaration.

Only 1-dimensional arrays are supported with an explicit array size, using
either C-style or GLSL style syntax:

\<base type\>\[\<array size\>\] variable name - ex: `half[10] x;`

\<base type\> variable name\[\<array size\>\] - ex: `half x[10];`

Arrays cannot be returned from a function, copied, assigned or compared.
Array restrictions propagate out to structures containing arrays. Arrays can
only be indexed using a constant or a loop variable.

## Qualifiers

> [!NOTE]
> **Note:** `attribute`, `varying`, and `invariant` are not supported.

| Type | Description |
|---|---|
| **`const`** | Compile-time constant, or read-only function parameter. |
| **`uniform`** | Value does not change across the primitive being processed. Uniforms are passed from Android using [RuntimeShader](https://developer.android.com/reference/android/graphics/RuntimeShader) methods for `setColorUniform`, `setFloatUniform`, `setIntUniform`, `setInputBuffer`, and `setInputShader`. |
| **`in`** | For passed-in function parameters. This is the default. |
| **`out`** | For passed-out function parameters. Must use the same precision as the function definition. |
| **`inout`** | For parameters that are both passed in and out of a function. Must use the same precision as the function definition. |

## Variable declaration

Declarations must be in an explicit braced scope. The declaration of **`y`** in
the following sample is disallowed:

    if (condition)
        int y = 0;

## Matrix/structure/array basics

### Matrix constructor examples

When a matrix is constructed with a single value, all values along
the diagonal are given that value, while the rest are given zeros. `float2x2(1.0)` would
therefore create a 2x2 identity matrix.

When a matrix is constructed with multiple values, columns are filled first
(column-major order).

Note that, unlike GLSL, constructors that reduce the number of components of a
passed-in vector are not supported, but you can use swizzling to have the same
effect. To construct a `vec3` from a `vec4` in AGSL with the same behavior as
GLSL, specify `vec3 nv = quadVec.xyz`.

### Structure constructor example

    struct light { float intensity; float3 pos; };
    // literal integer constants auto-converted to floating point
    light lightVar = light(3, float3(1, 2, 3.0));

### Matrix components

Access components of a matrix with array subscripting syntax.

    float4x4 m; // represents a matrix
    m[1] = float4(2.0); // sets second column to all 2.0
    m[0][0] = 1.0; // sets upper left element to 1.0
    m[2][3] = 2.0; // sets 4th element of 3rd column to 2.0

### Structure fields

Select structure fields using the period **`.`** operator. Operators include:

| Operator | Description |
|---|---|
| **`.`** | field selector |
| **`==, !=`** | equality |
| **`=`** | assignment |

### Array elements

Array elements are accessed using the array subscript operator `[ ]`. For example:

    diffuseColor += lightIntensity[3] * NdotL;

## Operators

Numbered in order of precedence. The relational and equality
operators \> \< \<= \>= == != evaluate to a Boolean. To compare vectors
component-wise, use functions such as `lessThan()`, `equal()`, etc.

|   | Operator | Description | Associativity |
|---|---|---|---|
| 1 | **`()`** | parenthetical grouping | N/A |
| 2 | **`[] () . ++ --`** | array subscript function call \& constructor structure field or method selector, swizzle postfix increment and decrement | Left to Right |
| 3 | **`++ -- + - !`** | prefix increment and decrement unary | Right to Left |
| 4 | **`* /`** | multiply and divide | Left to Right |
| 5 | **`+ -`** | add and subtract | Left to Right |
| 7 | **`< > <= >=`** | relational | Left to Right |
| 8 | **`== !=`** | equality/inequality | Left to Right |
| 12 | **`&&`** | logical AND | Left to Right |
| 13 | **`^^`** | logical XOR | Left to Right |
| 14 | **`||`** | logical OR | Left to Right |
| 15 | **`?\:`** | selection (one entire operand) | Left to Right |
| 16 | **`= += -= *= /=`** | assignment arithmetic assignment arithmetic assignment | Left to Right |
| 17 | **`,`** | sequence | Left to Right |

### Matrix and vector operations

When applied to scalar values, the arithmetic operators result in a scalar. For
operators other than modulo, if one operand is a scalar and the other is a
vector or matrix, the operation is performed componentwise and results in the
same vector or matrix type. If both operations are vectors of the same size, the
operation is performed componentwise (and returns the same vector type).

| Operation | Description |
|---|---|
| `m = f * m` | Component-wise matrix multiplication by a scalar value |
| `v = f * v` | Component-wise vector multiplication by a scalar value |
| `v = v * v` | Component-wise vector multiplication by a vector value |
| `m = m + m` | Matrix component-wise addition |
| `m = m - m` | Matrix component-wise subtraction |
| `m = m * m` | Linear algebraic multiply |

If one operand is a vector matching the row or column size of our matrix, the
multiplication operator can be used to do algebraic row and column multiplication.

| Operation | Description |
|---|---|
| `m = v * m` | Row vector \* matrix linear algebraic multiply |
| `m = m * v` | Matrix \* column vector linear algebraic multiply |

Use the built-in functions for vector dot product, cross product, and
component-wise multiplication:

| Function | Description |
|---|---|
| `f = dot(v, v)` | Vector dot product |
| `v = cross(v, v)` | Vector cross product |
| `m = matrixCompMult(m, m)` | Component-wise multiply |

## Program control

| Function call | Call by value-return |
|---|---|
| Iteration | `for (<init>;<test>;<next>)` `{ break, continue }` |
| Selection | `if ( ) { }` `if ( ) { } else { }` `switch () { break, case }` - default case last |
| Jump | `break, continue, return` (discard is not allowed) |
| Entry | `half4 main(float2 fragCoord)` |

### For loop limitations

Similar to GLSL ES 1.0, 'for' loops are quite limited; the compiler must be able
to unroll the loop. This means that the initializer, the test condition, and the
`next` statement must use constants so that everything can be computed at compile
time. The `next` statement is further limited to using `++, --, +=, or -=`.

## Built-in functions

**`GT`** (generic type) is **`float`** , **`float2`** , **`float3`** , **`float4`** or
**`half`** , **`half2`** , **`half3`** , **`half4`**.

Most of these functions operate component-wise (the function is applied
per-component). It's noted when that is not the case.

### Angle \& trigonometric functions

Function parameters specified as an angle are assumed to be in units of radians.
In no case will any of these functions result in a divide by zero error. If the
divisor of a ratio is 0, then results will be undefined.

| Function | Description |
|---|---|
| **`GT radians(GT degrees)`** | Converts degrees to radians |
| **`GT degrees(GT radians)`** | Converts radians to degrees |
| **`GT sin(GT angle)`** | Standard sine |
| **`GT cos(GT angle)`** | Standard cosine |
| **`GT tan(GT angle)`** | Standard tangent |
| **`GT asin(GT x)`** | Returns an angle whose sine is x in the range of $ \\left\[-{\\pi\\over 2},{\\pi\\over 2}\\right\] $ |
| **`GT acos(GT x)`** | Returns an angle whose cosine is x in the range of $ \\left\[0,\\pi\\right\] $ |
| **`GT atan(GT y, GT x)`** | Returns an angle whose trigonometric arctangent is $ \\left\[{y\\over x}\\right\] $ in the range of $ \\left\[-\\pi,\\pi\\right\] $ |
| **`GT atan(GT y_over_x)`** | Returns an angle whose trigonometric arctangent is **`y_over_x`** in the range of $ \\left\[-{\\pi\\over 2},{\\pi\\over 2}\\right\] $ |

### Exponential functions

| Function | Description |
|---|---|
| **`GT pow(GT x, GT y)`** | Returns $ x\^y $ |
| **`GT exp(GT x)`** | Returns $ e\^x $ |
| **`GT log(GT x)`** | Returns $ ln(x) $ |
| **`GT exp2(GT x)`** | Returns $ 2\^x $ |
| **`GT log2(GT x)`** | Returns $ log_2(x) $ |
| **`GT sqrt(GT x)`** | Returns $ \\sqrt{x} $ |
| **`GT inversesqrt(GT x)`** | Returns $ 1\\over{\\sqrt{x}} $ |

### Common functions

| Function | Description |
|---|---|
| **`GT abs(GT x)`** | Absolute value |
| **`GT sign(GT x)`** | Returns -1.0, 0.0, or 1.0 based on sign of x |
| **`GT floor(GT x)`** | Nearest integer \<= x |
| **`GT ceil(GT x)`** | Nearest integer \>= x |
| **`GT fract(GT x)`** | Returns the fractional part of x |
| **`GT mod(GT x, GT y)`** | Returns value of x modulo y |
| **`GT mod(GT x, float y)`** | Returns value of x modulo y |
| **`GT min(GT x, GT y)`** | Returns minimum value of x or y |
| **`GT min(GT x, float y)`** | Returns minimum value of x or y |
| **`GT max(GT x, GT y)`** | Returns maximum value of x or y |
| **`GT max(GT x, float y)`** | Returns maximum value of x or y |
| **`GT clamp(GT x, GT`** **`minVal, GT maxVal)`** | Returns x clamped between minVal and maxVal. |
| **`GT clamp(GT x, float`** **`minVal, float maxVal)`** | Returns x clamped between minVal and maxVal |
| **`GT saturate(GT x)`** | Returns x clamped between 0.0 and 1.0 |
| **`GT mix(GT x, GT y,`** **`GT a)`** | Returns linear blend of x and y |
| **`GT mix(GT x, GT y,`** **`float a)`** | Returns linear blend of x and y |
| **`GT step(GT edge, GT x)`** | Returns 0.0 if x \< edge, else 1.0 |
| **`GT step(float edge,`** **`GT x)`** | Returns 0.0 if x \< edge, else 1.0 |
| **`GT smoothstep(GT edge0,`** **`GT edge1, GT x)`** | Performs Hermite interpolation between 0 and 1 when edge0 \< x \< edge1 |
| **`GT smoothstep(float`** **`edge0, float edge1,`** **`GT x)`** | Performs Hermite interpolation between 0 and 1 when edge0 \< x \< edge1 |

### Geometric functions

These functions operate on vectors as vectors, not component-wise. GT is float/half vectors in sizes 2-4.

| Function | Description |
|---|---|
| **`float/half length`** **`(GT x)`** | Returns length of vector |
| **`float/half distance(GT`** **`p0, GT p1)`** | Returns distance between points |
| **`float/half dot(GT x,`** **`GT y)`** | Returns dot product |
| **`float3/half3`** **`cross(float3/half3 x,`** **`float3/half3 y)`** | Returns cross product |
| **`GT normalize(GT x)`** | Normalize vector to length 1 |
| **`GT faceforward(GT N,`** **`GT I, GT Nref)`** | Returns N if dot(Nref, I) \< 0, else -N. |
| **`GT reflect(GT I, GT N)`** | Reflection direction I - 2 \* dot(N,I) \* N. |
| **`GT refract(GT I, GT N,`** **`float/half eta)`** | Returns [refraction vector](https://www.khronos.org/registry/OpenGL-Refpages/gl4/html/refract.xhtml) |

### Matrix functions

Type mat is any square matrix type.

| Function | Description |
|---|---|
| **`mat matrixCompMult(mat`** **`x, mat y)`** | Multiply x by y component-wise |
| **`mat inverse(mat m)`** | Returns the inverse of m |

### Vector relational functions

Compare x and y component-wise. Sizes of input and return vectors for a particular call must match. T is the union of integer and floating point vector types. BV is a boolean vector that matches the size of the input vectors.

| Function | Description |
|---|---|
| **`BV lessThan(T x, T y)`** | x \< y |
| **`BV lessThanEqual(T x,`** **`T y)`** | x \<= y |
| **`BV greaterThan(T x,`** **`T y)`** | x \> y |
| **`BV greaterThanEqual(T`** **`x, T y)`** | x \>= y |
| **`BV equal(T x, T y)`** | x == y |
| **`BV equal(BV x, BV y)`** | x == y |
| **`BV notEqual(T x, T y)`** | x != y |
| **`BV notEqual(BV x,`** **`BV y)`** | x != y |
| **`bool any(BV x)`** | `true` if any component of x is `true` |
| **`bool all(BV x)`** | `true` if all components of x are `true`. |
| **`BV not(BV x)`** | logical complement of x |

### Color functions

| Function | Description |
|---|---|
| **`vec4 unpremul(vec4`** **`color)`** | Converts color value to non-premultiplied alpha |
| **`half3 toLinearSrgb(half3`** **`color)`** | Color space transformation to linear SRGB |
| **`half3 fromLinearSrgb(half3`** **`color)`** | Color space transformation |

## Shader sampling (evaluation)

Sampler types aren't supported, but you can evaluate other shaders. If you need
to sample a texture, you can create a
[BitmapShader](https://developer.android.com/reference/android/graphics/BitmapShader) object, and add it as a
uniform. You can do this for any shader, which means you can directly evaluate
any Android Shader without turning it into a
[Bitmap](https://developer.android.com/reference/android/graphics/Bitmap) first, including other
[RuntimeShader](https://developer.android.com/reference/android/graphics/RuntimeShader) objects. This allows
for a huge amount of flexibility, but complex shaders can be expensive to
evaluate, particularly in a loop.

    uniform shader image;

    image.eval(coord).a   // The alpha channel from the evaluated image shader

## Raw buffer sampling

Although most images contain colors that should be color-managed, some images
contain data that isn't actually colors, including images storing normals,
material properties (e.g., roughness), heightmaps, or any other purely
mathematical data that happens to be stored in an image. When using these kinds
of images in AGSL, you can use a BitmapShader as a generic raw buffer using
[RuntimeShader#setInputBuffer](https://developer.android.com/reference/android/graphics/RuntimeShader#setInputBuffer(java.lang.String,%20android.graphics.BitmapShader)).
This will avoid color space transformations and filtering.

