# 第三方组件与音源

本文件记录 code-to-music 0.5.0 的依赖及来源，不替代各组件的许可证，也不将第三方组件重新授权为 MIT。软件、采样/预设与音乐输出分别处理。当前源码仓库不包含插件、采样或安装归档；资源安装器从固定上游地址获取文件。

## Python 运行依赖

以下版本和许可标识依据本机已安装发行包的元数据核对；具体版权声明、随 wheel 捆绑的其他库及完整许可文本以各发行包为准。

| 组件 | 锁定版本 | 许可标识 | 来源 |
|---|---|---|---|
| NumPy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | [源码](https://github.com/numpy/numpy) |
| jsonschema | 4.26.0 | MIT | [源码](https://github.com/python-jsonschema/jsonschema) |
| Mido | 1.3.3 | MIT | [源码](https://github.com/mido/mido) |
| Pedalboard | 0.9.26 | GPLv3 | [源码](https://github.com/spotify/pedalboard) |
| attrs | 26.1.0 | MIT | [源码](https://github.com/python-attrs/attrs) |
| jsonschema-specifications | 2025.9.1 | MIT | [源码](https://github.com/python-jsonschema/jsonschema-specifications) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | [源码](https://github.com/pypa/packaging) |
| referencing | 0.37.0 | MIT | [源码](https://github.com/python-jsonschema/referencing) |
| rpds-py | 2026.9.1 | MIT | [源码](https://github.com/crate-py/rpds) |

## 插件、采样与外部工具

下表延续 [音源说明](docs/INSTRUMENTS.md) 中记录的来源。发布捆绑版之前，仍需逐个核对所分发产物的完整许可；底层引擎许可不等同于整个插件许可。

2026-10-18 已在线核对 Pedalboard v0.9.26 与 sfizioso Player v0.12.3 的许可原文，固定版本链接见 [许可说明](docs/LICENSING.md#固定版本原文核对)。Pedalboard 的上游 README 另列静态编入的 JUCE 6、VST3 SDK、Rubber Band、FFTW 等组件；sfizioso 的许可明确应用为 AGPLv3，不能用共享库的 BSD 许可代替应用许可。

| 组件或内容 | 版本 | 记录的许可与来源 |
|---|---|---|
| FluidSynth | 2.6.1 | LGPL-2.1-or-later；[官方发行](https://github.com/FluidSynth/fluidsynth/releases/tag/v2.6.1) |
| Surge XT | 1.3.4 | GPL-3.0-or-later 软件；[官方发行](https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4) |
| sfizioso Player | 0.12.3 | AGPL-3.0 播放器、BSD-2-Clause 引擎；[官方发行](https://github.com/rullopat/sfizioso-player/releases/tag/v0.12.3) |
| Salamander Grand Piano | FreePats SF2 V3+20200602 | CC-BY-3.0；Alexander Holm 原作，Roberto / FreePats 整理；[来源](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html) |
| AVL Red Zeppelin / Black Pearl | AVL Drumkits 1.1 SF2 | CC-BY-SA-3.0，原站另有录制音乐例外；[来源](https://bandshed.net/avldrumkits/) |
| VSCO 2 CE | commit 28092772094b2d9f1148d84cea97f4545b8c687d | CC0-1.0 采样；[固定版本](https://github.com/sgossner/VSCO-2-CE/tree/28092772094b2d9f1148d84cea97f4545b8c687d) |
| Surge 厂方内容 | 1.3.4 中五个 Claes 预设及 init 状态 | 具体来源和对预设的调整见音源说明；[官方 FAQ](https://surge-synthesizer.github.io/faq/) |
| FFmpeg | 用户自行安装 | 取决于构建选项及其包含的库；[官方许可说明](https://ffmpeg.org/legal.html) |

安装器的 URL 与哈希在 `scripts/install_resources.py`；安装完成后的清单在本地 `resources/download-manifest.json`。哈希用于固定内容，不代替许可证或上游签名。

## 生成音乐时的说明

GPL/AGPL 软件许可不意味着全部音频输出自动采用 GPL/AGPL；输出还需要考虑实际采样和预设的条款。Surge 的官方 FAQ 对厂方预设生成音频的分发和商用有说明，不应将其扩展为任意第三方预设的授权。

使用 Salamander 的作品附以下鸣谢及许可链接：

> Piano samples: Salamander Grand Piano by Alexander Holm; SF2 adaptation by Roberto / FreePats, V3+20200602. Licensed under Creative Commons Attribution 3.0: https://creativecommons.org/licenses/by/3.0/

AVL 原站的录制音乐例外与原始采样文件的再分发规则应分别阅读。VSCO 采样采用 CC0，仍建议保留来源以方便追溯。公开示例应列出实际使用的音源，不能将所有输出统一标为“无条件免版税”。

## 再分发软件时的说明

仅发布自有源码、发布 Python wheel、以及捆绑完整运行环境是不同的分发对象。附上本声明不自动满足 GPL/LGPL/AGPL 对具体分发形式的全部要求；发行二进制组合时需要核对对应源码、许可文本、修改说明及其他适用义务。MIT 方向的具体评估见 [许可方案](docs/LICENSING.md)。
