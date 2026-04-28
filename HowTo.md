Shadertoy
Search...
浏览
新建
登录

如何


1. How to create shaders
2. How to build applications that use the shaders - API




1. How to create shaders

关于着色器如何基于你的选择（网络端的WebG；原生平台的Opengl 2、Opengl 3或者Opengl 4；移动平台的OpenGL ES）在Shadertoy界面渲染的简介。界面介绍包括着色器生成图像，声音和虚拟现实渲染时所需的输入和输出信号。

图像着色器
为了通过计算每个像素的颜色来生成过程图像着色器需要执行mainImage()函数。每生成一个像素点时此函数都会被调用，并且此程序的责任是提供正确的输入并从中获得输出颜色并将其分配给屏幕像素。设计原型:

void mainImage( out vec4 fragColor, in vec2 fragCoord );

其中fragCoord包括着色器用来计算颜色的像素坐标。坐标是以像素为单位，精确范围从0.5 到-0.5, 覆盖渲染表面，其中分辨率通过iResolution参数(详见下文)传递给着色器。

产生的结果颜色由四位向量储存在fragColor里, 最后一位被接受端忽略。 在未来用于叠加多个渲染目标时，结果作为“输出”参数储存。

声音着色器
声音由GLSL着色器通过mainSound()函数产生, 遵循以下设计原型:

vec2 mainSound( float time )

其中time变量变量是用于计算波幅的声音样本的时间（以秒为单位）。这个时间将以iSampleRateuniform指定的采样率进行采样，根据应用程序，该采样率通常为44100或48000。

通过mainSound函数的返回值，将期望的波幅输出为立体声（左和右声道）声音的一对值。
由mainSound入口点生成的着色器将被自动标记为声音着色器，并且可以通过声音输出限定词的过滤器系统进行搜索。

虚拟现实着色器
Shadertoy着色器可以为虚拟现实（VR）无缝生成图像。这些着色器需要实现mainVR()函数, 此方程不是着色器必须实现方程但遵循以下设计原型:

void mainVR( out vec4 fragColor, in vec2 fragCoord, in vec3 fragRayOri, in vec3 fragRayDir )

其中fragCoord和fracColor工作方式和普通2D图像着色器一样：他们包括像素在表面空间的坐标系数和输出像素颜色。

变量fragRayOri和fragRayDir包含在跟踪器空间中给出的经过虚拟空间里的像素的射线原点和射线方向。 如果移动的相机是通过虚拟空间移动，那么着色器将把这些值转换到相机空间。射线原点是一个变量并且在相机不作为针孔相机的VR系统中不是uniform参数。

由mainVR入口点生成的着色器将被自动标记为VR，并且可以通过VR限定词的过滤器系统进行搜索。

统一变量输入
着色器可以通过使用以下统一变量来提供不同类型的每帧静态信息:

uniform vec3 iResolution;
uniform float iTime;
uniform float iTimeDelta;
uniform float iFrame;
uniform float iChannelTime[4];
uniform vec4 iMouse;
uniform vec4 iDate;
uniform float iSampleRate;
uniform vec3 iChannelResolution[4];
uniform samplerXX iChanneli;



2. How to build applications that use the shaders

Creating Shadertoy API keys is free, but a Shadertoy account with Silver or Gold Status is required (check your Profile to see your current Status). Obtaining such Status is solely possible through positive use of the Shadertoy platform.

Due to the volume of requests, the API usage is limited to 1500 requests per month. If you need additional requests, please consider joining our Patreon.


Request Your Key
Sign In and come back to this page for instructions

What Can You Access?
After you request your API Key, you will be able to access your (and others') beloved Shadertoys from any website/app. This basically means that you can run queries on our database, and even download shaders to use them on your own software (check licenses).

If you can not see your shader listed in the API make sure the privacy of your shader is set to "Public + API", be aware that when you do that other users will be able to access/use your shaders.

Coding: Simple, Very Simple
All API calls require a key that you can request (check the first section of this page) for free and returns JSON files that you can easily read with your favorite parser.

Here are the basics of our API:
Query shaders: as a developer you can pass any query to run on our database. This service will return an array of IDs.

https://www.shadertoy.com/api/v1/shaders/query/string?key=appkey

where string is your search string such as tags, usernames, words...


Get a shader from a shader ID.

https://www.shadertoy.com/api/v1/shaders/shaderID?key=appkey

where shaderID is the same ID used in the Shadertoy URLs, and also the values returned by the "Query Shaders".


Access the assets.

When you retrieve a shader you will see a key called "inputs", this can be a texture/video/keyboard/sound used by the shader. The JSON returned when accessing a shader will look like this:

[..]{"inputs":[{"id":17,"src":"/media/a/(hash.extension)","ctype":"texture","channel":0}[..]

To access this specific asset you can just cut and paste this path https://www.shadertoy.com/media/a/(hash.extension)


Get all shaders.

https://www.shadertoy.com/api/v1/shaders?key=appkey

Advanced queries:
Query shaders sorted by "name", "love", "popular", "newest", "hot" (by default, it uses "popular").

https://www.shadertoy.com/api/v1/shaders/query/string?sort=newest&key=appkey


Query shaders with paging. Define a "from" and a "num" of shaders that you want (by default, there is no paging)

https://www.shadertoy.com/api/v1/shaders/query/string?from=5&num=25&key=appkey


Query shaders with filters: "vr", "soundoutput", "soundinput", "webcam", "multipass", "musicstream" (by default, there is no filter)

https://www.shadertoy.com/api/v1/shaders/query/string?filter=vr&key=appkey



Source Code
Official Shadertoy App - Check our Github!

License
"Shadertoy.com API" is free and open. Shadertoy.com is not responsible for either the malfunctioning of the API or the malfunctioning of any of the shaders return by the API.

Since the API is part of Shadertoy.com, developers that use the API have to respect the terms of use. For example, developers must respect the specific licenses of each shader.

Any product (app, web...) that uses the "Shadertoy.com API", either free or commercial, must mention that uses "Shadertoy.com API".
Community Forums
事件
In Facebook (english)
In Facebook (korean)
In Discord (direct link)
Feedback and Support
Facebook
Twitter
Patreon
Roadmap
Shadertoy
商店
如何
条款和隐私
关于
Apps and Plugins
Official iPhone App by Reinder
Screensaver by Kosro
Shadertoy plugin by Patu
Tutorials
Shader coding intro by iq
Shadertoy Unofficial by FabriceNeyret2