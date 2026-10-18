# code-to-music 0.5.0 — Windows x64 preview

Turn versioned JSON scores into real instruments, offline WAV, stems and MIDI—without a DAW or audio device.

code-to-music 面向 Coding Agent 和希望精确修改乐谱的开发者：改音符、力度、时间和轨道增益，再通过 CLI 生成音频及可检查的报告。

## 包含什么

- 12 个固定音源：Salamander 钢琴、两套 AVL 鼓组、三类 VSCO 持续音、Surge init 和五个电子音色。
- `doctor / instruments / validate / render / inspect`，CLI JSON v3；乐谱与完整报告 schema v1。
- 44.1/48 kHz PCM24 立体声 WAV、可选分轨、MIDI 和包含资产指纹的报告。
- 四首 33–42 秒的原创展示小曲及完整 JSON 乐谱，另保留四份简短入门示例；技术检查与主观听感状态分别说明。
- 自有代码采用 MIT，第三方软件和音源保留各自许可。

## 开始使用

下载完整源码归档，解压后按 README 安装。推荐 Windows x64 / 64 位 Python 3.13，需先安装 FFmpeg 并确认 PATH 可用。依赖最低要求为 Python 3.12，但音源验收使用 3.13.7。音源下载约 650 MB，安装后离线渲染；预留至少 5 GB 空间。

本次以源码安装为入口。仓库包含资源安装器、锁定依赖和示例；不包含插件、采样、下载缓存或整套 Python 运行时。单独 wheel 不构成完整安装套件。

## 验证及边界

0.5.0 已完成 81 次实际 CLI 调用、65 项检查；完整大体积产物后因清理空间删除，结论和关键指标保留在 `docs/PALETTE_ACCEPTANCE.md`。发布准备仅针对新增包元数据和示例展示作必要检查，没有重复完整验收。

展示曲写作暴露并修正了 Pedalboard float32 时长转换在部分长度下少一帧的问题：一次渲染足够的真实采样后截取目标长度，不补零、不重试整曲。原先失败的管弦乐谱已通过，另以 44.1/48 kHz 的 Surge 与 SFZ 短音符做针对性回归。

只验证 Windows x64 和锁定音源；不承诺任意 VST3、完整管弦演奏法、实时预览或其他操作系统。MIDI 不嵌入音源和插件状态，普通播放器无法据此复现 WAV。试听材料的原始 WAV 技术检查通过，尚未记录主观听感确认。

第三方依赖含 GPL/LGPL/AGPL 组件；项目 MIT 不将整套运行环境重新授权为 MIT。安装和分发前请阅读 `THIRD_PARTY_NOTICES.md` 与 `docs/LICENSING.md`。
