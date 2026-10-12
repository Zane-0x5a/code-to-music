# code-to-music · 阶段一

Agent 修改 JSON 乐谱，运行 `music validate` 和 `music render`，得到经过技术检查的 PCM24 立体声 WAV、分轨、MIDI 和机器可读报告。第一条链路使用真实钢琴采样 **Salamander Grand Piano SF2** 和免费软件合成器 **Surge XT 1.3.4**，不需要 DAW、GUI 或音频设备。

这是供独立审查的第一阶段，尚未经过听感确认。实际验收状态、证据和限制见 `docs/STAGE_ONE.md`；不要把可加载的任意插件当成已验证音源。

当前纠偏版本为 **0.3.0 / CLI JSON v3**：inspect 返回状态、本次选用音源的 ID/版本/资产 SHA-256 和完整报告路径，失败报告不会返回成功。空事件或全部 mute 的作品以 `E_SCORE` 提前拒绝；主 WAV 始终检查非静音。0.1.0 的 `data.report` / 逐文件 `data.integrity` 回显已移除；接入方须按 `version=3` 与 `data.status` 读取。旧 CLI v1/v2 schema 原样保留用于历史证据；新增 instruments 使用 inspect 摘要 v2，严格校验接入方须切换到 cli-v3.json；乐谱和完整渲染报告仍为 v1。复审纠偏记录见 [REVIEW_FOLLOWUP.md](docs/REVIEW_FOLLOWUP.md)。

## 安装：Windows x64

需要 Python 3.11+（实际验证 3.13.7）、FFmpeg 在 PATH、约 5 GB 项目磁盘空间。锁定的 Windows x64 音源下载约 600 MB。所有命令在仓库根目录运行；安装不改系统音频设置或全局插件目录。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\.venv\Scripts\python.exe scripts\install_resources.py
.\.venv\Scripts\music.exe doctor --json
.\.venv\Scripts\music.exe validate examples\first-score.json --json
.\.venv\Scripts\music.exe render examples\first-score.json --output outputs\first --json
.\.venv\Scripts\music.exe inspect outputs\first --json
```

将 `.venv\Scripts` 加入当前 shell 的 PATH 后可直接用 `music`。`python -m music` 与 `music` 等价，但必须使用安装了本包的 Python。网络只用于安装：渲染完全离线。已缓存归档可用 `scripts/install_resources.py --offline`，归档 SHA-256 不匹配会拒绝解包。校验和来自本次上游 HTTPS 下载，是本地锁定值，不是上游签名。

安装器不覆盖不同的现有配置，也会复用已有 `resources/surge-profile.json`。更新固定音色 profile 时，保留并移出旧配置与旧 profile，再显式生成新配置并重跑验收；具体记录见 `docs/STAGE_ONE.md`。请不要擅自把 stable 升级成 nightly。

## 一次阅读后开始

最小使用路径见 `docs/AGENT_QUICKSTART.md`。完整格式见 `src/music/schemas/score-v1.json` 和 `docs/SCORE.md`。

| 命令 | 行为 |
|---|---|
| `music doctor --json` | 校验资源 SHA-256，实际加载两个音源并离线演奏 C4，检查 FFmpeg、运行时和权限 |
| `music instruments --json` | 音源来源、许可、版本、路径、能力、记录的验证状态；不会演奏 |
| `music validate score.json --json` | 乐谱 schema、语义、音源引用与哈希；不加载 native 后端 |
| `music render score.json --output outputs\new --dry-run --json` | 解析资源和输出计划，拒绝已有目录；不创建输出 |
| `music render score.json --output outputs\new --json` | 离线渲染并检查；原子发布新目录 |
| `music inspect outputs\new --json` | 返回状态、本次选用音源指纹和 report_path；只有报告通过、产物完整、主音频复查通过才成功 |

各子命令接受 `--config PATH`。默认 `MUSIC_CONFIG` 环境变量或当前工作目录的 `music.config.json`；配置内相对路径以配置文件所在目录为基准。路径可有空格和中文；调用 shell 时用引号或参数数组。

`--json` 的 stdout 恰好一个 JSON 对象：`version/tool_version/command/ok/data/error`，当前 `version=3`，schema 为 `src/music/schemas/cli-v3.json`。成功退出 0；`doctor` 健康检查失败退出 1；输入/渲染/inspect 错误退出 2。失败包含稳定错误码、受影响资源、原因、下一步；inspect 的诊断摘要保留在 `data`，未检查的完整性和音频为 null，不能视为通过。命令帮助保留普通文本。`validate` 成功只代表解析/资源校验成功；`doctor` 和 `render` 才实际触发 native 音源。

## 目录、缓存与隐私边界

* `src/music/`：乐谱、资源、后端适配、渲染、音频检查、MIDI、CLI；schema 随包安装。
* `music.config.json`：本机路径和 SHA-256；Git 忽略，不含密钥。
* `resources/`：便携插件、采样、生成的音色状态、下载清单；Git 忽略。
* `work/downloads/`：固定版本归档缓存；Git 忽略。
* `.music/doctor/`：实际探针请求、native 日志、音频中间文件。
* `.music/logs/`：CLI 错误以及失败渲染目录，保留报告和 native 日志。
* `outputs/`：用户产物与验收证据；Git 忽略。输出目录默认 `outputs/render`，已存在就失败，不覆盖。

保留中间文件时 `request.json` 记录的是执行当时暂存路径；原子发布后这些请求用于追溯，不能直接重放旧绝对路径。报告中的日志与 command 请求路径映射到最终证据目录。关闭中间文件后，后端 `command/log=null`、`intermediates_retained=false`，不会给出已删除文件的入口。

## 真实验收

```powershell
.\.venv\Scripts\python.exe scripts\acceptance.py
```

脚本在新的中文/空格路径执行实际 CLI；包含双音源渲染、重渲染 SHA-256 对比、改音高确认对应分轨变化、MIDI、缺资源、非法 schema、不支持的 CC、坏 DLL、缺后端、已有输出与 dry-run 保护、零帧拒绝、inspect 对真实失败/缺失/损坏产物的判定、摘要契约、证据路径、音高/力度端点和踏板差分。完整证据落到 `outputs/acceptance-*/summary.json`。近干净环境的执行命令见阶段记录。

0.3.0 另覆盖音源指纹与超长元数据的明确省略、失败/未完成报告的快照语义、整份作品空事件/全部 mute 的拒绝、主 WAV 静音复查、单条无音符轨仍可渲染，以及缺配置的安装指引；旧 v2 响应继续符合旧 schema，新形状必须使用 CLI v3 / inspect v2。

## 技术边界与许可

只验证 Windows x64、两个锁定音源和一个 Surge profile。采样来自 Alexander Holm，FreePats SF2 改编由 Roberto 维护；使用 CC-BY-3.0，请在分享作品时保留 `docs/INSTRUMENTS.md` 的鸣谢。FluidSynth 为 LGPL-2.1-or-later，Surge 为 GPL-3.0-or-later，Pedalboard 为 GPL-3.0；若分发组合软件应核实这些许可证义务。音源、插件、安装包不进 Git。

限制、许可证原始来源、后端选择与已验证能力见 `docs/INSTRUMENTS.md`。第三方插件可能崩溃或卡住，渲染子进程有超时和隔离，但这不是针对恶意插件的安全沙箱。阶段一拒绝随机选择/任意 preset 与未验证控制器；不承诺任何 VST3 都能稳定离线渲染。
