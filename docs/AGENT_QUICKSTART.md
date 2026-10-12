# Agent 快速开始

目的：用可版本控制的 JSON 精确改音乐。不要安装 DAW，不需要点击任何插件窗口。

1. 在仓库根目录，确认 `.venv` 中已经安装本包；执行 `.venv\Scripts\music.exe doctor --json`，要求 `ok=true`。缺资源时运行 `.venv\Scripts\python.exe scripts\install_resources.py`。
2. 复制 `examples/first-score.json` 到新的 UTF-8 JSON 文件。改 `pitch`、`beat`、`duration`、`velocity`、轨道 `gain_db`、`mute`。每拍始终是四分音符；C4=60。
3. `music instruments --json` 读取可用音源 id 与能力。`salamander-piano` 是采样钢琴，`surge-init` 是免费电子音源。
4. `music validate my-score.json --json` 要求 `ok=true`；`music render my-score.json --output "outputs/新作品 A" --dry-run --json` 查看资源与输出计划。
5. `music render my-score.json --output "outputs/新作品 A" --json`。不得复用已有目录；第二次用 `outputs/新作品 B`。
6. `music inspect "outputs/新作品 A" --json`，要求退出 0、`version=2`、`ok=true`、`data.status=passed`、`data.report_status=passed`、`data.integrity_passed=true`、`data.audio_recheck.passed=true`。需要完整乐谱、音源指纹或逐文件哈希时，读取 `data.report_path` 指向的报告文件。技术验收不等于听感确认；`listening_verified` 当前始终 false。

产物：`master.wav`、`stems/<id>.wav`、`score.mid`、`stems/<id>.mid`、`report.json`。MIDI 保留音符、力度、CC、速度和拍号，不嵌入采样、插件 patch 或音频混音增益；在普通 GM 播放器里播放不能复现 WAV 音色。

成功响应示意：

```json
{"version":2,"tool_version":"0.2.0","command":"render","ok":true,"data":{"report_path":".../report.json","master_path":".../master.wav","status":"passed"},"error":null}
```

| 错误码 | 修复 |
|---|---|
| `E_INPUT` / `E_SCHEMA` / `E_SCORE` | 按错误位置修正 UTF-8 JSON、版本、必要字段、音高或总长度 |
| `E_CONFIG` | 使用安装器生成的 v1 配置，资源路径以配置文件为基准 |
| `E_RESOURCE_MISSING` | 选择 instruments 中的 id 或补齐缺失采样 |
| `E_RESOURCE_CHANGED` | 恢复锁定资源；显式升级需重建配置并重跑验收 |
| `E_BACKEND_UNAVAILABLE` / `E_BACKEND_TIMEOUT` | 看错误指向的 native.log，恢复 DLL/插件/便携资源目录 |
| `E_UNSUPPORTED` / `E_OVERLAP` | 使用已支持能力；分开重叠的同音高音符 |
| `E_OUTPUT_EXISTS` | 使用新目录，旧文件未动 |
| `E_AUDIO_QA` | 读取失败报告；过响则降低 master_gain_db，过轻则提高轨道 gain_db，静音则检查事件和音源 |
| `E_RENDER_FAILED` | 原始渲染已失败；按 data.render_error_code 和 report_path 读取错误及 native 日志，修复后重渲染 |
| `E_RENDER_INCOMPLETE` | 原始渲染未完成；等待结束或查失败证据，不能使用当前目录 |
| `E_ARTIFACT_MISSING` | 恢复缺失的报告/产物，或重渲染到新目录 |
| `E_ARTIFACT_CHANGED` | 文件大小或 SHA-256 已变化；恢复原始产物或重渲染 |
| `E_ARTIFACT` | 报告不合规范、必需文件未登记或 WAV 无法解码；恢复原始报告和音频或重渲染 |

`--json` 成功退出 0；doctor 有失败项退出 1；错误退出 2。错误不需要人工确认才能重试。不要忽略 unsupported 错误，也不要把 native 退出码当成音频质量通过。

inspect 摘要使用 `kind=music.inspect/version=1`，字段定义在 CLI v2 schema 的 `$defs.inspection`。`status` 明确区分 passed、render_failed、render_incomplete、artifact_missing、artifact_changed、invalid_report、artifact_invalid 和 audio_failed；`report_status` 是原始报告状态。`artifacts` 只有登记/检查/缺失/变化数量；`issues` 最多 8 条。失败报告不会开始产物或音频复查，`integrity_passed/audio_recheck=null` 表示未检查。失败时 `ok=false` 且 `error` 给出修复指引，`data` 仍保留摘要。

从 0.1.0 迁移：CLI envelope 由 v1 升至 v2；读取 `data.status/report_status/report_path`，不再读取 `data.report` 或逐文件 `data.integrity`。完整报告文件格式仍为 v1。
