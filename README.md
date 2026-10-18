# code-to-music

Agent 修改 JSON 乐谱，运行 `music validate` 和 `music render`，得到经过技术检查的 PCM24 立体声 WAV、分轨、MIDI 和机器可读报告。当前提供 **12 个固定音源**：Salamander 钢琴、两套 AVL 采样鼓组、VSCO 长笛/小号/小提琴组、Surge init 及电钢琴/贝斯/拨弦/Lead/FM Pad；不需要 DAW、GUI 或音频设备。

先听 [四段示例](docs/DEMOS.md)，再复制对应 JSON 修改音符或编曲。安装后使用 [Agent 快速开始](docs/AGENT_QUICKSTART.md)；本次版本说明见 [0.5.0 发布说明](docs/RELEASE_NOTES_0.5.0.md)。

音色尚未经过听感确认。0.5.0 的交付范围和通过证据见 [PALETTE_ACCEPTANCE.md](docs/PALETTE_ACCEPTANCE.md)；第一阶段历史证据见 `docs/STAGE_ONE.md`。不要把可加载的任意插件当成已验证音源。

当前版本为 **0.5.0 / CLI JSON v3**：inspect 返回状态、本次选用音源的 ID/版本/资产 SHA-256 和完整报告路径，失败报告不会返回成功。空事件或全部 mute 的作品以 `E_SCORE` 提前拒绝；主 WAV 始终检查非静音。0.4.0 区分主输出与安静分轨的响度要求，失败响应给出实际指标、阈值和报告路径。CLI JSON v3、inspect 摘要 v2、乐谱与完整报告 v1 保持兼容；历史迁移记录见 [REVIEW_FOLLOWUP.md](docs/REVIEW_FOLLOWUP.md)。

## 安装：Windows x64

推荐 **64 位 Python 3.13**（实际验证 3.13.7）；依赖要求的最低版本为 3.12，尚未完成该版本的音源验收。还需要 FFmpeg 在 PATH、至少 5 GB 项目磁盘空间，验收证据另占空间。锁定的 Windows x64 音源下载约 650 MB。安装不改系统音频设置或全局插件目录。

先从本仓库的 **Code → Download ZIP** 下载并解压源码，或 clone 本仓库。在包含 `pyproject.toml` 的目录打开 PowerShell。安装脚本和示例随源码提供，单独安装 wheel 不包含这些文件。

安装 Python 后先确认 `python --version` 指向所需版本。FFmpeg 可从其 [下载页](https://ffmpeg.org/download.html) 选择 Windows 构建，解压后将包含 `ffmpeg.exe` 的 `bin` 目录加入 PATH；也可使用已有的包管理器安装。修改 PATH 后重新打开终端；在 Codex 等桌面应用内使用时，可能需要重启应用才能继承新 PATH。

在下载音源前运行：

```powershell
python --version
python -c "import struct, sys; print(sys.executable); assert sys.version_info >= (3, 12), 'Python 3.12+ required'; assert struct.calcsize('P') == 8, '64-bit Python required'"
ffmpeg -version
```

三条都成功后，逐条执行以下命令；任何一条报错时先修复再继续。最后的输出目录必须尚不存在，再次渲染时改为 `outputs\second` 等新目录。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\.venv\Scripts\python.exe scripts\install_resources.py
.\.venv\Scripts\music.exe doctor --json
.\.venv\Scripts\music.exe validate examples\first-score.json --json
.\.venv\Scripts\music.exe validate examples\drum-beat.json --json
.\.venv\Scripts\music.exe render examples\first-score.json --output outputs\first --json
.\.venv\Scripts\music.exe inspect outputs\first --json
```

将 `.venv\Scripts` 加入当前 shell 的 PATH 后可直接用 `music`。`python -m music` 与 `music` 等价，但必须使用安装了本包的 Python。网络只用于安装：渲染完全离线。已缓存归档可用 `scripts/install_resources.py --offline`，归档 SHA-256 不匹配会拒绝解包。校验和来自本次上游 HTTPS 下载，是本地锁定值，不是上游签名。

安装器保留自定义配置项，只补入缺少的固定音源；若同名项已被修改，会报错而不覆盖。SFZ 播放器、三类 VSCO 采样和五个固定 Surge 厂方 profile 默认安装；`--prepare-sfz` 保留为兼容选项。更新固定音色 profile 时，保留并移出旧配置与旧 profile，再显式生成新配置并重跑验收；具体记录见 `docs/STAGE_ONE.md`。

## 一次阅读后开始

最小使用路径见 `docs/AGENT_QUICKSTART.md`。完整格式见 `src/music/schemas/score-v1.json` 和 `docs/SCORE.md`。

| 命令 | 行为 |
|---|---|
| `music doctor --json` | 校验资源 SHA-256，实际加载配置中的所有音源并离线演奏探针音符，检查 FFmpeg、运行时和权限 |
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

0.5.0 已完成 81 次 CLI 调用、65 项检查，摘要见 [音源扩展验收](docs/PALETTE_ACCEPTANCE.md)。完整本地产物后来因清理空间删除，不影响已完成的验收结论。仅修改文档或包元数据无需重跑音源验收；修改渲染、后端、依赖或音源时，按影响范围回归。

需要完整回归时运行（会生成大量音频和日志）：

```powershell
.\.venv\Scripts\python.exe scripts\acceptance.py
```

脚本在新的中文/空格路径执行实际 CLI；包含钢琴和 Surge 双音源渲染、重渲染比较、改音高确认目标分轨变化、MIDI、异常资源/乐谱、失败报告及产物检查。三类 SFZ 逐键探测并跨进程重复，五个厂方电子音源检查两种采样率的音域/力度网格与复现；管弦和电子完整乐谱检查分轨及目标修改隔离。两套鼓组还逐键探测 36..61、演奏真实鼓节奏、检查 MIDI 打击乐通道和重复渲染。完整证据落到 `outputs/acceptance-*/summary.json`。

0.3.0 另覆盖音源指纹与超长元数据的明确省略、失败/未完成报告的快照语义、整份作品空事件/全部 mute 的拒绝、主 WAV 静音复查、单条无音符轨仍可渲染，以及缺配置的安装指引；旧 v2 响应继续符合旧 schema，新形状必须使用 CLI v3 / inspect v2。

## 技术边界与许可

只验证 Windows x64、12 个锁定音源。新增音源使用原有乐谱字段和命令；可直接渲染 `examples/orchestra-sketch.json`、`examples/electronic-sketch.json`。钢琴来自 Alexander Holm，经 FreePats 改编，使用 CC-BY-3.0；AVL 鼓组使用 CC-BY-SA-3.0 并对录制音乐有例外条款。软件依赖另有 LGPL/GPL/AGPL 条款。音源、插件、安装包不进 Git。来源、许可和音乐输出的区别见 [第三方声明](THIRD_PARTY_NOTICES.md)，具体能力见 [音源说明](docs/INSTRUMENTS.md)。

本项目自有代码、文档及原创示例采用 [MIT](LICENSE)。第三方软件、采样和预设保留各自许可；MIT 不意味着包含 GPL/AGPL 组件的整套运行环境可以任意闭源分发。适用范围见 [许可说明](docs/LICENSING.md)。

限制、许可证原始来源、后端选择与已验证能力见 `docs/INSTRUMENTS.md`。SFZ 已启用同步离线读样，避免实时磁盘串流在高速渲染时随机缺样。Surge 仅准入五个实测厂方 profile；BBC Discover 尚未完成厂商安装流程，未纳入。第三方插件可能崩溃或卡住，渲染子进程有超时和隔离，但这不是针对恶意插件的安全沙箱；不承诺任何 VST3 都能稳定离线渲染。

## 参与和反馈

开发环境、按改动范围验证的方法和问题反馈要求见 [贡献说明](CONTRIBUTING.md)。提交问题时附工具版本、命令、错误码和最小乐谱；先移除日志中的个人路径，不上传整套音源或下载缓存。
