# 首轮独立审查纠偏 · 0.2.0

根本要求是让 Agent 凭 inspect 的单次响应正确判断产物能否使用。审查发现 0.1.0 把 failed 报告的空 artifacts 判为完整，继而返回成功；同时存在 dry-run 与正式渲染不一致、零帧乐谱和失效证据路径。本轮修正这些行为，没有扩展音源。原始阶段记录与限制保留在 [STAGE_ONE.md](STAGE_ONE.md)。

本文保留 0.2.0 的历史验收记录。后续复审指出音源指纹单读遗漏与全静音作品误通过，0.3.0 的修正、最新证据和诊断改进见 [REVIEW_FOLLOWUP.md](REVIEW_FOLLOWUP.md)。

## 行为修正

| 审查问题 | 当前行为与端到端证据 |
|---|---|
| failed 报告返回成功 | 先验证报告格式与状态；真实坏 DLL 渲染产生的 failed/空 artifacts 报告，以及审查指定的历史失败报告，都返回退出 2 / ok=false / E_RENDER_FAILED；完整性和音频复查为 null |
| 失败、缺损、通过混淆 | E_RENDER_INCOMPLETE 区分未完成；E_ARTIFACT_MISSING 区分缺文件；E_ARTIFACT_CHANGED 区分大小/哈希变化；E_ARTIFACT 区分无效报告、缺登记或不能解码的 WAV；只有完整 passed 报告与音频复查通过才退出 0 |
| inspect 回显整份 report | CLI v2 返回 music.inspect v1 摘要：状态、报告路径、检查数量、最多 8 条问题、主音频复查指标；完整报告留在文件。当前短示例 JSON 为 817 字节（序列化正文加 LF，不计终端 CRLF 差异），回归要求小于 4096 字节 |
| dry-run 对已有目录成功 | dry-run 与正式 render 共用输出存在检查，均 E_OUTPUT_EXISTS；原 master 哈希保持不变；新目录 dry-run 仍不创建文件 |
| validate 接受 0 帧 | tempo=300、length_beats=1e-10、tail=0、空 events 在 validate/dry-run/render 均 E_SCORE，给出增加时长/尾音的修复指引，不创建输出 |
| 关闭 intermediates 后悬空 command | command/log=null，intermediates_retained=false；保留时两条路径指向实际证据文件；静音轨保留 skipped 语义 |

inspect 会验证 report-v1 schema、必需产物登记、文件大小与哈希、主 WAV 解码/技术复查，以及保存的主输出、分轨和求和检查。登记为空不能自动通过。仅哈希匹配也不能跳过 WAV 解码：回归将损坏 WAV 的新哈希登记进复制报告，仍得到 E_ARTIFACT / artifact_invalid。报告没有签名；这些检查不认证篡改后的报告来源，也没有替代试听。

## 契约与迁移

工具版本为 0.2.0，CLI envelope `version=2`，定义在 `src/music/schemas/cli-v2.json`；旧 cli-v1 schema 保留，供历史证据读取。inspect 的 `data.report` 与逐文件 `data.integrity` 已移除，接入方改读 `data.status/report_status/report_path`。失败响应的 data 也可包含诊断摘要，不能假设所有错误的 data 都是 null。

乐谱与完整报告仍为 v1，既有字段含义不变；报告校验补全了实际输出必需字段的类型约束。新增后端证据字段是可选诊断字段。旧正常报告可继续 inspect；原始历史失败报告可被正确识别。API 详情见 [AGENT_QUICKSTART.md](AGENT_QUICKSTART.md)。

## 非 editable 安装与真实复验

地点：`D:\Projects\Tools\code-to-music`。复用首阶段建立的 `.acceptance-venv`，重新构建并强制安装普通 wheel，没有 editable 或源目录注入；19 个已安装 Python/schema 文件与当前 src 一致。环境仍为 Windows 11 x64、Python 3.13.7、FFmpeg 8.1.1 与已锁定的两音源资产。

```powershell
Set-Location 'D:\Projects\Tools\code-to-music'
.\.acceptance-venv\Scripts\python.exe -m pip install --no-deps --force-reinstall .
.\.acceptance-venv\Scripts\python.exe -m pip check
.\.acceptance-venv\Scripts\music.exe --help
.\.acceptance-venv\Scripts\music.exe inspect --help
.\.acceptance-venv\Scripts\python.exe scripts\acceptance.py
.\.acceptance-venv\Scripts\music.exe inspect '.music\logs\60a6f298d2b84051a7a44005e7a129cb' --json
```

最后一条预期退出 2，错误码 E_RENDER_FAILED。修正前上述失败报告、已有目录 dry-run、零帧 validate 均实际复现为退出 0；修正后同一输入的快速回归全部退出 2。本轮最终安装的 wheel 观测 SHA-256：`c0a67ea3044757dc7d753bcd79c4810d28b922ecb72ea05a175bd3fa2889d1dd`，不是可复现构建承诺。

最终完整证据：[outputs/acceptance-20261012-195010/summary.json](../outputs/acceptance-20261012-195010/summary.json)，**29 次实际 CLI 调用 / 19 项显式检查全部通过**。所有响应按 CLI v2 schema 验证；真实双音源渲染、两次重复比较、改单轨音高、MIDI、力度/踏板、Unicode 路径、native 超时与进程树清理均复跑。pip check、命令帮助及 Git 空白检查通过。

代表音频：PCM24 立体声 48000Hz，562909 帧 / 11.727270833 秒；-32.07 LUFS、-15.27 dBTP、0 削波采样。钢琴/MIDI 逐字节一致；Surge/master 重复差异及分轨求和残差均为 1 个 PCM24 单位，既有容差未放宽。

## 当前边界

此轮审查列出的五项问题均已修正并有真实 CLI 回归。尚待独立复审；无试听结论、仅本机 Windows 与两个锁定音源、Surge 的 Pedalboard 0.9.26 版本耦合及 SF2 功能省略仍是原有限制。下一步是复审这些纠偏与契约迁移，之后再决定扩展。
