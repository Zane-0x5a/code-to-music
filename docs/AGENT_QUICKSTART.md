# Agent 快速开始

目的：用可版本控制的 JSON 精确改音乐。不要安装 DAW，不需要点击任何插件窗口。

1. 在仓库根目录，确认 `.venv` 中已经安装本包；执行 `.venv\Scripts\music.exe doctor --json`，要求 `ok=true`。缺资源时运行 `.venv\Scripts\python.exe scripts\install_resources.py`。
2. 复制 `examples/first-score.json` 到新的 UTF-8 JSON 文件。改 `pitch`、`beat`、`duration`、`velocity`、轨道 `gain_db`、`mute`。每拍始终是四分音符；C4=60。
3. `music instruments --json` 读取可用音源 id 与能力。`salamander-piano` 是采样钢琴，`surge-init` 是免费电子音源。
4. `music validate my-score.json --json` 要求 `ok=true`；`music render my-score.json --output "outputs/新作品 A" --dry-run --json` 查看资源与输出计划。
5. `music render my-score.json --output "outputs/新作品 A" --json`。不得复用已有目录；第二次用 `outputs/新作品 B`。
6. `music inspect "outputs/新作品 A" --json`，检查 `data.report.status=passed`、`data.integrity_passed=true`、`data.audio_recheck.passed=true`。技术验收不等于听感确认；`listening_verified` 当前始终 false。

产物：`master.wav`、`stems/<id>.wav`、`score.mid`、`stems/<id>.mid`、`report.json`。MIDI 保留音符、力度、CC、速度和拍号，不嵌入采样、插件 patch 或音频混音增益；在普通 GM 播放器里播放不能复现 WAV 音色。

成功响应示意：

```json
{"version":1,"tool_version":"0.1.0","command":"render","ok":true,"data":{"report_path":".../report.json","master_path":".../master.wav","status":"passed"},"error":null}
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
| `E_ARTIFACT` / `E_ARTIFACT_CHANGED` | 使用原始报告和产物，或重渲染到新目录 |

`--json` 成功退出 0；doctor 有失败项退出 1；错误退出 2。错误不需要人工确认才能重试。不要忽略 unsupported 错误，也不要把 native 退出码当成音频质量通过。
