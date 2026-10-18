# 音源、后端与权利来源

## 实际选择

使用 FluidSynth 2.6.1 C API 演奏 SF2，用 Pedalboard 0.9.26 的 VST3 宿主演奏 Surge XT 1.3.4。两者在独立子进程内，无 GUI、无设备驱动，按 MIDI 时间线生成指定数量采样帧。

不采用 archived 的 sfizz/sfizz-ui。FluidSynth 和 Surge 主仓库的 `archived=false` 已通过 GitHub API 查询；Surge 主仓库的 latest release 指向 nightly，因此安装器改用官方稳定发行仓库 `surge-synthesizer/releases-xt` 的 1.3.4，而非 nightly。sfizioso Player 0.12.3 用于三类已固定的 VSCO 2 CE SFZ；不采用归档的 sfizz 仓库。

| 音源/组件 | 固定版本、格式 | 来源与许可 | 加载方式 |
|---|---|---|---|
| Salamander Grand Piano | FreePats SF2 V3+20200602；原始 Yamaha C5，16 层力度，48kHz/24bit 录制 | [FreePats 原始页](https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html)，CC-BY-3.0 | FluidSynth，bank=0/program=0；真实音频采样，不是自制合成器 |
| AVL Red Zeppelin / Black Pearl | AVL Drumkits 1.1 的两套 SF2；真实鼓组采样 | [AVL 原站](https://bandshed.net/avldrumkits/) 与 [SF2 下载目录](https://www.bandshed.net/sounds/AVLDrumkits_SF2/)，CC-BY-SA-3.0，录制音乐例外见原站 | FluidSynth，bank=0/program=0；MIDI 36..61，导出打击乐通道 10 |
| FluidSynth | 2.6.1 Windows x64 cpp11 | [官方发行](https://github.com/FluidSynth/fluidsynth/releases/tag/v2.6.1)，LGPL-2.1-or-later | ctypes C API；禁用 chorus/reverb，单 CPU，无 MIDI/audio driver |
| Surge XT | 1.3.4 Windows x64 portable VST3 | [官方稳定发行](https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4)，GPL-3.0-or-later 软件 | Pedalboard加载内层 `.vst3` 二进制；保持便携 SurgeXTData 目录结构 |
| VSCO 2 CE | 固定 commit `28092772094b2d9f1148d84cea97f4545b8c687d`，SFZ 与引用的 WAV | [官方仓库](https://github.com/sgossner/VSCO-2-CE)，CC0-1.0 | sfizioso Player 0.12.3 VST3，持续音长笛/小号/小提琴组 |
| sfizioso Player | 0.12.3 Windows VST3 | [官方发行](https://github.com/rullopat/sfizioso-player/releases/tag/v0.12.3)，AGPL-3.0 播放器、BSD-2-Clause 引擎 | JUCE 状态恢复路径；freewheel=1、preload=1024 KiB |
| Pedalboard | 0.9.26 Windows cp313 wheel | [官方源码](https://github.com/spotify/pedalboard)，GPL-3.0 | 无 GUI VST3 MIDI render；不代表所有插件可用 |

安装路径是仓库内 `resources/fluidsynth-2.6.1/`、`resources/salamander/`、`resources/avl-red-zeppelin/`、`resources/avl-black-pearl/`、`resources/surge-xt-1.3.4/`。精确绝对路径和 SHA-256 在 `music instruments --json` 与每次报告中。整个 FluidSynth bin 目录和 SurgeXTData 都锁定目录指纹，不仅锁单个主二进制。目录摘要按相对文件路径排序，加入 UTF-8 路径、NUL 和每个文件的 SHA-256 字节。

## 许可及鸣谢

钢琴原作：Alexander Holm。FreePats SF2 整理由 Roberto（roberto@zenvoid.org）。原始音源的 CC-BY-3.0 许可及版本说明随下载包 `readme.txt` 保存。分享含此音源的作品，请保留以下鸣谢及许可链接；不同发行用途应核对原始许可条款。

> Piano samples: Salamander Grand Piano by Alexander Holm; SF2 adaptation by Roberto / FreePats, V3+20200602. Licensed under Creative Commons Attribution 3.0: https://creativecommons.org/licenses/by/3.0/

Surge init profile来自已锁定插件的初始音色状态；另准入 Surge 厂方随包的五个 Claes 预设，不加载第三方商业 preset。软件 GPL 与生成的音频权利是不同问题；不把“GPL 插件”理解成“所有输出自动必须 GPL”。使用其他 wavetables、样本、预设时需记录其独立许可证。本阶段软件依赖包括 GPL 库，软件再分发需履行相应义务；没有替用户完成法律审查。

AVL 原站列出的 CC-BY-SA-3.0 条款包含录制音乐例外；不要把采样文件再分发许可与使用鼓组产生的录音混为一谈。项目保留原站 URL、下载地址和锁定 SHA-256，分享或再分发前应核对其原始许可文本。当前只接入上述两套 SF2，不宣称具备六麦克风混音、完整 LV2 插件能力或主观听感保证。

## 真实验证与限制

钢琴和 Surge 准入普通 MIDI 音符、力度 1..127、CC64 sustain，范围 21..108。验收分别演奏 MIDI 21/60/108 × 力度 1/64/127 的九点网格，检查各段非静音且同音高峰值随力度严格递增；踏板用 CC64 与无踏板尾音差分验证。离散点验证不能代替每个键、每个力度或每个声音细节的试听。

两套 AVL 鼓组准入 MIDI 36..61、力度 1..127、无 CC。固定 SF2 的 62..64 在实际逐键探测中静音，因此即使公开键位图可能包含这些编号，本项目仍拒绝它们。验收覆盖 36/38/42 × 力度 1/64/127、36..61 每个音符的非静音、真实八拍节奏的 CLI 渲染/inspect、MIDI 打击乐通道和独立渲染的逐采样比较。FluidSynth 对已经自然结束的一次性鼓采样执行 note-off 可能返回无活动声部；适配器允许这种幂等释放。采样鼓目前只输出立体声，不支持独立麦克风和 round-robin 控制。示例见 `examples/drum-beat.json`。

Salamander SF2 自带发行说明明确省略 SFZ 的 `amp_veltrack`、踏板/击槌噪声和释键共鸣。它提供钢琴真实采样，但没有完整声学共鸣模拟；不能将原版 SFZ 能力写成这条链路的能力。

Surge 先以空 MIDI 准备采样率、恢复状态，再推进音频块处理排队的 patch；直接核对恢复后的名称、振荡器类型和已修改参数，不注入测试音符。随后推进至少 2 秒静音，要求最后 100ms 峰值不超过 `1e-12`，最多 10 秒，正式乐谱只渲染一次。init profile保留三个既有控制；厂方 profile 则保留 FX 与嵌入 wavetable，并明确记录 A/B 振荡器 retrigger=1、drift=0、VCA velocity sensitivity=-24dB。这会改变相位/随机漂移和力度响应，不能宣称与未修改厂方音色完全相同。

| instrument id | 来源预设/演奏法 | 准入 MIDI 音域 | CC |
|---|---|---|---|
| `vsco-flute-sustain` | FluteSusNV：独奏长笛无颤音持续音 | 60..96 | 无 |
| `vsco-trumpet-sustain` | TrumpetSus：独奏小号持续音 | 52..84 | 无 |
| `vsco-violin-ensemble` | ViolinEnsSusVib：小提琴组颤音持续音 | 55..86 | 无 |
| `surge-dx-ep` | Keys/DX EP.fxp | 36..96 | 无 |
| `surge-e-bass` | Basses/E-Bass.fxp | 24..84 | 无 |
| `surge-nice-pluck` | Plucks/Nice Pluck 1.fxp | 36..96 | 无 |
| `surge-classic-lead` | Leads/Classic Lead 1.fxp | 36..96 | 无 |
| `surge-fm-pad` | Pads/FM Pad.fxp | 36..96 | 无 |

这些音源支持普通 notes/velocity、和弦及固定厂方效果；不支持 keyswitch、expression CC、任意 FXP、pitch bend、程序切换和插件参数自动化。力度网格验证 1/64/127，不能代替所有组合的试听。厂方电子预设的每个力度点使用独立进程初始化与演奏，避免前音效果残响污染弱音测量；连续音符和和弦另行比较复现。Classic Lead 峰值可能超过 1，使用示例中的分轨/主增益；FM Pad 需要足够尾音。另试过 Pad 1，但跨进程随机差异超容差，因此没有准入。

Surge 官方 [FAQ](https://surge-synthesizer.github.io/faq/) 明确允许从 factory presets 生成的音频免费分发、销售或商业许可；GPL3 约束软件修改与二进制分发，不约束这些音频输出。此声明不等于原始 preset 文件可以无条件再分发。本项目资源留在本机，记录厂方 FXP 作者及 SHA-256。

宿主兼容层 `src/music/backends/vst3.py` 严格要求 Pedalboard 0.9.26，供 Surge 与 SFZ 共同使用。该版本空参数表仍触发完整控制枚举；独立单音源 worker 临时替换枚举钩子，`finally` 恢复，通过 native raw_state 描述符恢复 JUCE 状态。init 的三个控制用 `AudioProcessorParameter(search_steps=1)`；厂方与 SFZ 状态不枚举参数。不支持同进程并发宿主，升级 Pedalboard 必须重新验收。

该宿主的 MIDI 渲染入口以 float32 秒数乘采样率后截取整数帧，某些时长会少一帧。适配层先计算宿主实际会生成的帧数，必要时将 float32 时长向上移动，再一次生成真实音频并截取所需帧数；不会补零或重试整段。新增 88 BPM 管弦曲覆盖了原先失败的 1,676,509 帧；`scripts/check_native_frames.py` 在 44.1/48 kHz 下用 Surge 与 SFZ 的短真实音符分别回归该边界。

SFZ 原先连续音符随机缺样并非通过放宽容差解决。根因是实时磁盘串流不能跟上高速离线渲染；适配器改为 freewheel 同步读样并增加 preload。无探针重试、无整段重渲染掩盖失败。验收覆盖三类 SFZ 完整准入音域、两种采样率的管弦和弦乐谱与独立进程复现；五个厂方 profile 覆盖两种采样率的音域/力度网格、电子和弦乐谱、分轨修改隔离。所有新音源仍未经主观听感评价。

BBC Symphony Orchestra Discover 尚未完成厂商安装流程与无 GUI 验证；未纳入。VSCO 仅三个持续音演奏法，不代表完整管弦乐团；采样鼓仅当前两套立体声 SF2，不具备 Virtuosity Drums 的独立麦克风能力。

下一次扩展须先做真实无 GUI 加载、MIDI 演奏、离线渲染、重复运行，并记录版本、许可、资产指纹和边界。`resources/download-manifest.json` 保留固定源地址与归档 SHA-256；这些指纹是本次 HTTPS 下载后记录的本地锁定值，不是上游签名。项目不提交二进制音源、插件或安装归档。

重复性要求：钢琴 WAV 和 MIDI 必须逐字节一致；Surge 与含 Surge 的主输出必须逐采样差异不超过 `4/2^23`（4 个 PCM24 量化单位，约 -126.4 dBFS 满幅差异上限）。两套鼓组的节奏重复渲染最大逐采样差异为 0。改变乐谱时须证明目标分轨改变、未改分轨仍落在固定容差内。最新通过的验收证据见 `outputs/acceptance-*/summary.json`，须以 `status=passed` 选取；历史失败诊断不能当作当前通过证据。
