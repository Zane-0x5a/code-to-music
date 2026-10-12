# 音源、后端与权利来源

## 实际选择

使用 FluidSynth 2.6.1 C API 演奏 SF2，用 Pedalboard 0.9.26 的 VST3 宿主演奏 Surge XT 1.3.4。两者在独立子进程内，无 GUI、无设备驱动，按 MIDI 时间线生成指定数量采样帧。

不采用 archived 的 sfizz/sfizz-ui。FluidSynth 和 Surge 主仓库的 `archived=false` 已通过 GitHub API 查询；Surge 主仓库的 latest release 指向 nightly，因此安装器改用官方稳定发行仓库 `surge-synthesizer/releases-xt` 的 1.3.4，而非 nightly。

| 音源/组件 | 固定版本、格式 | 来源与许可 | 加载方式 |
|---|---|---|---|
| Salamander Grand Piano | FreePats SF2 V3+20200602；原始 Yamaha C5，16 层力度，48kHz/24bit 录制 | [FreePats 原始页](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html)，CC-BY-3.0 | FluidSynth，bank=0/program=0；真实音频采样，不是自制合成器 |
| FluidSynth | 2.6.1 Windows x64 cpp11 | [官方发行](https://github.com/FluidSynth/fluidsynth/releases/tag/v2.6.1)，LGPL-2.1-or-later | ctypes C API；禁用 chorus/reverb，单 CPU，无 MIDI/audio driver |
| Surge XT | 1.3.4 Windows x64 portable VST3 | [官方稳定发行](https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4)，GPL-3.0-or-later 软件 | Pedalboard加载内层 `.vst3` 二进制；保持便携 SurgeXTData 目录结构 |
| Pedalboard | 0.9.26 Windows cp313 wheel | [官方源码](https://github.com/spotify/pedalboard)，GPL-3.0 | 无 GUI VST3 MIDI render；不代表所有插件可用 |

安装路径是仓库内 `resources/fluidsynth-2.6.1/`、`resources/salamander/`、`resources/surge-xt-1.3.4/`。精确绝对路径和 SHA-256 在 `music instruments --json` 与每次报告中。整个 FluidSynth bin 目录和 SurgeXTData 都锁定目录指纹，不仅锁单个主二进制。目录摘要按相对文件路径排序，加入 UTF-8 路径、NUL 和每个文件的 SHA-256 字节。

## 许可及鸣谢

钢琴原作：Alexander Holm。FreePats SF2 整理由 Roberto（roberto@zenvoid.org）。原始音源的 CC-BY-3.0 许可及版本说明随下载包 `readme.txt` 保存。分享含此音源的作品，请保留以下鸣谢及许可链接；不同发行用途应核对原始许可条款。

> Piano samples: Salamander Grand Piano by Alexander Holm; SF2 adaptation by Roberto / FreePats, V3+20200602. Licensed under Creative Commons Attribution 3.0: https://creativecommons.org/licenses/by/3.0/

Surge init profile来自已锁定插件的初始音色状态；本阶段没有加载第三方采样或第三方商业 preset。软件 GPL 与生成的音频权利是不同问题；不把“GPL 插件”理解成“所有输出自动必须 GPL”。使用其他 wavetables、样本、预设时需记录其独立许可证。本阶段软件依赖包括 GPL 库，软件再分发需履行相应义务；没有替用户完成法律审查。

## 真实验证与限制

当前准入：普通 MIDI 音符、力度 1..127、CC64 sustain；乐谱范围 21..108。验收以实际报告为准：分别演奏 MIDI 21/60/108 × 力度 1/64/127 的九点网格，检查各段非静音且每个音高的峰值随力度严格递增；踏板通过相同音符的 CC64 按下/松开与无踏板尾音做差分，检查延音能量增加。离散点验证不能代替每个键、每个力度或每个声音细节的试听。

Salamander SF2 自带发行说明明确省略 SFZ 的 `amp_veltrack`、踏板/击槌噪声和释键共鸣。它提供钢琴真实采样，但没有完整声学共鸣模拟；不能将原版 SFZ 能力写成这条链路的能力。

Surge 在状态恢复后异步加载 patch；直接紧接着离线渲染会静音。适配器先做丢弃的短音符探针，等待真实非静音响应（15 秒上限），随后应用固定 oscillator retrigger / drift 设置，并将 `A Velocity > VCA Gain` 的归一化值设为 `0.5`（-24dB 力度灵敏度）。原始 init patch 的振幅不随 MIDI 力度变化；当前固定 profile 已实际验证力度响应。宿主 reset 单独使用仍留下首次渲染差异；适配器再丢弃至少 2 秒音频，要求最后 100ms 峰值不超过 `1e-12`，最多推进 10 秒音频，失败则拒绝正式渲染。实际 MIDI 随后从零开始。这些是有上限的真实音频检查；重复性仍由独立进程的重渲染和分轨比较验证，不由初始化步骤本身保证。

宿主兼容层 `src/music/backends/surge.py` 严格要求 Pedalboard 0.9.26。该版本即使传入空参数表，也会枚举全部插件参数；普通 `raw_state` 赋值也触发枚举，实测耗时超过 90 秒。独立 worker 加载时临时替换 `ExternalPlugin.__set_initial_parameter_values__`，在 `finally` 中恢复；通过 `object.__setattr__` 设置 native raw_state 描述符，再为三个准入控制器创建 `AudioProcessorParameter(search_steps=1)` 并写入归一化值。这是明确的版本耦合，不支持同进程并发宿主。当前机器最新验收的 doctor 约 5.24 秒、双音源示例 render 约 6.43 秒；不是性能保证。升级 Pedalboard 前必须审查该兼容层并重新验收。

目前只准入这个 init profile。任意 factory preset、FXP、wavetable 依赖、插件参数自动化、程序切换、pitch bend和其他演奏法尚未实际验证；乐谱层拒绝未知字段和未准入 CC。用户分享插件目录不自动获得支持状态。

下一次扩展须先做真实无 GUI 加载、MIDI 演奏、离线渲染、重复运行，并记录版本、许可、资产指纹和边界。`resources/download-manifest.json` 保留固定源地址与归档 SHA-256；这些指纹是本次 HTTPS 下载后记录的本地锁定值，不是上游签名。项目不提交二进制音源、插件或安装归档。

重复性要求：钢琴 WAV 和 MIDI 必须逐字节一致；Surge 与含 Surge 的主输出必须逐采样差异不超过 `4/2^23`（4 个 PCM24 量化单位，约 -126.4 dBFS 满幅差异上限）。最新验收 `outputs/acceptance-20261012-191743/summary.json` 实测 Surge 和主输出最大差异均为 1 个量化单位；保留两次不同 SHA-256，不把技术容差通过写成逐字节一致。改变乐谱时须证明目标分轨改变、未改分轨仍落在该固定容差内。
