# 自有代码与第三方组件的许可

2026-10-18：根据维护者的宽松授权方向，自有代码、文档和原创示例采用 [MIT](../LICENSE)，署名沿用仓库作者 Zane-0x5a。第三方组件不在这份 MIT 授权范围内。音乐音频使用的采样和预设权利另见 [第三方声明](../THIRD_PARTY_NOTICES.md)。

## 推荐方向

**自有 Python 代码采用 MIT，第三方组件保留原有许可。** MIT 与 GPLv3 的兼容性允许 MIT 代码进入满足 GPL 条件的组合，并不让 GPL 组件变成 MIT，也不自动允许将依赖该组件的整体闭源分发。

因此，自有代码选择 MIT 与整个套件可以怎样分发是两个问题。当前默认运行路径直接依赖 GPLv3 的 Pedalboard；如分发构成 GPL 覆盖的组合，需要按相应条件授权、提供源码等。给自己的代码添加 MIT 许可不能免除这些条件。

## 当前各对象的边界

| 对象或场景 | MIT 方向下的处理 |
|---|---|
| 自有 Python 源码、脚本、schema | 采用 MIT；保留 MIT 版权及许可文本 |
| 自有文档、原创示例乐谱 | 一并采用 MIT；引用和第三方内容保留其来源及原许可 |
| Python wheel | 装入自有代码/schema、README 元数据、MIT 与第三方声明；声明依赖不会改变依赖许可 |
| 用户从上游自行安装依赖与音源 | 可以减少我们直接再分发第三方二进制的范围；不能据此断言组合关系及许可义务消失 |
| Pedalboard 与宿主代码 | 直接 import 的 GPLv3 依赖；不要宣传整套运行环境可任意闭源再分发 |
| Surge / FluidSynth | 按实际分发对象分别处理 GPL/LGPL，保留上游声明；若捆绑则核对源码提供等义务 |
| sfizioso Player VST3 | 已核对 0.12.3 原文：PlayerProcessor/PlayerEditor 属于 AGPLv3 应用，部分共享库/引擎为 BSD-2-Clause，JUCE 为 AGPLv3 或商业授权；不能仅凭独立 worker 断言豁免 |
| 商业服务 | MIT 本身不禁止商业用途；GPL/AGPL 也不等于禁止收费。AGPL 的网络交互要求需按实际程序、修改和部署方式判断 |
| WAV/MIDI 与采样/预设 | 音频不因使用 GPL 软件就自动 GPL；作品和所用内容的条款另行处理。采样与预设文件不纳入项目 MIT |

## 适合首发的分发范围

先发布自有源码、安装器、版本清单与示例，由用户从上游安装锁定资源。Release 不捆绑插件、采样或完整 Python 运行环境。这样分发对象清楚，也保留了以后调整后端的空间；它不是规避第三方许可的保证。

若未来希望让整个套件可闭源嵌入产品，需要重新评估默认依赖，可能涉及更换 GPL/AGPL 组件或取得其他授权，不能仅更换顶层 LICENSE。

## 固定版本原文核对

2026-10-18 通过 GitHub API 读取以下固定 tag 文件：

- [Pedalboard v0.9.26 LICENSE](https://github.com/spotify/pedalboard/blob/v0.9.26/LICENSE)：GPLv3；该文件 SHA-256 为 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`。
- [Pedalboard v0.9.26 README 许可段](https://github.com/spotify/pedalboard/blob/v0.9.26/README.md#license)：Spotify AB 版权所有，说明 JUCE 6、VST3 SDK、Rubber Band、FFTW、LAME、libgsm、dr_wav 等静态编入组件的许可。
- [sfizioso Player v0.12.3 LICENSE](https://github.com/rullopat/sfizioso-player/blob/v0.12.3/LICENSE)：逐目录区分 AGPL 应用、BSD 共享库及外部依赖，明确 `src/player/` 包含 PlayerProcessor 和 PlayerEditor。

上述核对支持如实标注组件许可，不代表对任意打包方式或 SaaS 部署作出统一法律结论。未来若捆绑二进制、修改播放器或改变服务方式，再核对对应分发义务。首发仅提供自有源码与安装器，第三方资源由上游下载。

参考：[GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html)、[MIT 文本](https://opensource.org/license/mit)、[第三方声明](../THIRD_PARTY_NOTICES.md)。
