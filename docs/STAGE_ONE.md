# 第一阶段技术验收记录

目标是让 Agent 修改声明式乐谱后，能够无 GUI 地得到真实采样钢琴与免费电子音源的离线音频，并凭报告检查结果。0.1.0 已完成这条垂直链路；当前交付供独立审查，尚未收到审查意见，也未做听感确认。此阶段结束后等待审查，不继续扩展音源。

## 已实现的用户行为

`doctor / instruments / validate / render / inspect` 提供版本化 JSON 和可行动错误。乐谱 v1 支持速度、拍号、音高、音符时间、力度、同音重叠策略、CC64、静音和输出选项；未知字段、未准入能力和资源变化会拒绝。validate 与 dry-run 不加载 native 音源。渲染在有超时的独立 worker 内执行；成功后原子发布新目录，已有输出不覆盖，失败保留日志和报告。

双音源为 Salamander Grand Piano FreePats SF2 V3+20200602 / FluidSynth 2.6.1，以及 Surge XT 1.3.4 / Pedalboard 0.9.26。产物包含 44100 或 48000Hz PCM24 立体声 WAV、可选分轨、MIDI、可选中间文件及报告。报告记录来源、许可、资源 SHA-256、实际后端版本、音频指标、阈值和产物指纹；inspect 重查解码、指纹和音频质量。详细准入边界见 [INSTRUMENTS.md](INSTRUMENTS.md)。

## 接近干净环境的实际执行

地点：`D:\Projects\Tools\code-to-music`。Windows 11 x64，Python 3.13.7，FFmpeg 8.1.1。另建 `.acceptance-venv`，安装锁定依赖与非 editable wheel，确认 schema 随包安装。这是新 Python 环境，复用同一 Windows 主机和经过哈希校验的资产缓存；不是新操作系统或完全重新下载验证。

以下为此环境的建立及复跑命令；本轮最后三条在补全 Surge 力度 profile 后再次执行：

```powershell
Set-Location 'D:\Projects\Tools\code-to-music'
& 'D:\Source2\Python\Python313\python.exe' -m venv .acceptance-venv
.\.acceptance-venv\Scripts\python.exe -m pip install -r requirements.lock
.\.acceptance-venv\Scripts\python.exe -m pip install --no-deps --force-reinstall .
.\.acceptance-venv\Scripts\python.exe scripts\install_resources.py --offline
.\.acceptance-venv\Scripts\python.exe scripts\acceptance.py
```

安装器不覆盖不同配置。重建 profile 时保留旧配置和旧 `resources/surge-profile.json` 后移出原位置，再运行安装器；不要只移配置却继续复用旧 profile。当前有效 profile 的 SHA-256 为 `f804220819e72162f1b5a7a3bf5808e386cb319cffce037dc9e82a5708b6638c`。

本轮安装产生的 wheel SHA-256 为 `0a76ae5ca67af716bd7e9d40840f3fecba9f893fc045d1e7bb505d2cc1007451`。构建时间等元数据可能使重新构建的 wheel 哈希变化；它是本轮证据，不是可复现构建承诺。

## 证据与结果

完整验收：[summary.json](../outputs/acceptance-20261012-191743/summary.json)。包含 16 次实际 CLI 调用与 11 项显式检查，状态 `passed`。完整代表产物在 `outputs/acceptance-20261012-191743/中文 路径/render A/`；保持整个目录，以免报告里的相对路径失效。

| 检查 | 本轮结果 |
|---|---|
| doctor、instruments、validate、dry-run、render、inspect | 全部成功，JSON envelope / render report schema 校验通过；dry-run 未创建目录 |
| 代表 WAV | 双声道 PCM24，48000Hz，562909 帧，11.727270833 秒，可解码 |
| 主输出技术指标 | -32.07 LUFS；-15.27 dBTP；RMS -36.04366 dBFS；0 个削波采样；末尾 50ms 全静音；无警告 |
| 分轨总和 | 轨道和 master 增益已计入分轨；最大残差 1 个 PCM24 单位，限值 3 单位 |
| 重复渲染 | 钢琴和 MIDI 逐字节一致；Surge/master 最大差异 1 单位，限值 4 单位；保留两次真实哈希 |
| 修改乐谱 | 改一个钢琴音高后钢琴分轨变化；未改 synth 最大差异 1 单位 |
| MIDI | 18 个 note-on，保留 sustain、速度与拍号 |
| 资源和失败 | 缺音源 id、缺 SF2、schema 错误、未准入 CC、缺插件、坏 DLL、已有输出分别失败且有错误码/资源/修复指引；失败未发布成功目录，已有 master 未变化 |
| 输出组合 | 44100Hz、静音轨道、关闭 stems/MIDI/intermediates 实测通过 |
| 演奏能力 | 两音源各 21/60/108 × 1/64/127 网格非静音且同音高峰值随力度严格递增；CC64 延音差分通过 |
| 路径和超时 | 中文与空格的乐谱/输出及实际 DLL/SF2 路径通过；强制 native 超时后进程树无残留 |

音频阈值是此阶段宽泛的技术门槛，不是发行母带目标。`listening_verified=false`。通过这些检查说明本例能被乐谱控制且可追溯，不证明所有旋律、音符、力度或音乐风格都已验证。

## 已观察到的问题与修正

Surge 异步恢复状态造成首次静音，短音符探针确认就绪后再开始。宿主 reset 留下首次渲染残留，增加有界丢弃衰减，并以重复进程渲染验证固定 4 单位容差。默认 init patch 接收力度但振幅不变，固定 VCA 力度控制并加入真实递增检查。

Pedalboard 全参数枚举造成超过 90 秒耗时与 doctor 超时，使用严格版本约束的局部兼容钩子；细节见音源文档与 `src/music/backends/surge.py`。Windows venv launcher 超时只杀父进程会残留 worker，改为父进程存活时终止整个树，并加入真实超时验证。FFmpeg stderr 含 JSON 后缀，改为解码单个 JSON 对象并关闭进度输出。旧失败证据保留在 `outputs/acceptance-*`，不能拿早期结果覆盖最新记录。

## 未解决的边界

仅实际验证本机 Windows x64 / Python 3.13.7 和这两个锁定音源、一个 Surge profile；其他 Python 版本、平台、任意 preset、自动化、其他 CC、pitch bend 均不作为已验证能力。Surge 兼容层依赖 Pedalboard 0.9.26 的内部加载钩子，不支持同进程并发宿主，升级须重审。资源 SHA-256 是上游 HTTPS 下载后的本地锁定值，不是上游签名。

钢琴 SF2 省略原始 SFZ 的部分噪声、释键共鸣与 amp_veltrack；没有完整共鸣建模。没有试听，尚不能确认主观音色与编曲品质。软件分发和作品鸣谢按原始许可证核对。核心链路已完成本机技术验收；长期产品质量仍需独立审查、纠偏及后续更广验证。
