# 复审纠偏 · 0.3.0

原始目标是让 Agent 单次读取就能判断音乐产物及其音源身份，且交付的主 WAV 通过非静音检查。0.2.0 的 inspect 省略了本次音源指纹，并让整份作品没有可发声音符时得到 passed；首次使用缺配置的修复提示也不够具体。此轮修正这三项，没有扩展音源。

## 行为与契约

inspect 摘要新增 `instruments`：从本次报告选用清单提取 ID、版本、以资产名称为键的 SHA-256，完整路径、大报告仍只在 `report_path`。此字段是记录快照，`source=render_report/current_assets_verified=false`，不读取当前配置或复验当前音源。failed/rendering 报告仍可返回快照，不能把选用清单当作已成功加载或演奏；缺失/无效报告为 null。声明格式错误的哈希会得到 E_ARTIFACT，不会变成内部异常或伪指纹。

音源部分有 2048 字节预算（默认 json.dumps ASCII 转义与空格的 UTF-8 编码）；按报告顺序逐个处理音源，每项先容纳身份，再在可用预算内添加该项哈希。过长的身份整项省略，资产超预算逐项省略，`total/omitted/assets_total/assets_omitted` 明确给出完整数量与省略数量。常规双音源直接返回全部六项资产指纹；超预算时完整信息可从 report_path 获取。工具版本为 0.3.0，CLI envelope 升至 v3，inspect 摘要升至 v2，新契约发布在 `src/music/schemas/cli-v3.json`。新增必需 instruments 会被旧 v2 严格 schema 拒绝；接入方须更新版本判断与 schema。旧 cli-v1/cli-v2 原样保留，乐谱和完整报告仍为 v1。具体字段见 [AGENT_QUICKSTART.md](AGENT_QUICKSTART.md)。

空事件、只有 CC 或全部轨道 mute 时，validate/dry-run/render 返回退出 2 / E_SCORE，fix 指引添加未静音音符或取消静音，不创建渲染目录。单条静音/无音符轨继续可用；主 WAV 在 render 与 inspect 始终执行 RMS/LUFS 下限检查，不能依赖旧报告中的静音标记跳过。渲染中实际变为静音或低于阈值时，仍以 E_AUDIO_QA 失败并保留失败证据。

缺失配置由 catalog 返回 E_CONFIG，并明确指引 `python scripts/install_resources.py` 或修正 `--config/MUSIC_CONFIG`。普通缺失乐谱仍保持 E_INPUT 和既有 UTF-8 JSON 修复语义。

## 验证入口

复用现有 Windows x64 `.acceptance-venv`，重新安装普通 wheel，没有 editable 或源目录注入：

```powershell
.\.acceptance-venv\Scripts\python.exe -m pip install --no-deps --force-reinstall .
.\.acceptance-venv\Scripts\python.exe scripts\acceptance.py
```

完整真实验收：[summary.json](../outputs/acceptance-20261012-201929/summary.json)，42 次 CLI 调用、31 项显式检查全部 passed。代表 inspect JSON 为 1603 字节，其中音源部分 770 字节，双音源六项哈希均无省略。安装时观测普通 wheel SHA-256 为 `f51b9b8d33db14ae7933ba7395d67665a2421361770d2653449f73204b89110c`。全部 20 个已安装 Python/schema 文件与本轮源文件一致；不是可复现构建保证。

主音频为 PCM24 双声道 48000 Hz、562909 帧、11.727270833 秒，-32.07 LUFS、-15.27 dBTP、0 削波采样。钢琴/MIDI 逐字节一致，Surge/master 重复差异和分轨求和残差均为 1 个 PCM24 单位，固定容差没有放宽。

提交与修正前后复现见 [复审交接](../outputs/review-followup/REVIEW_HANDOFF.md)。原 0.2.0 证据保留在 `outputs/stage-one-correction/`；首阶段证据也未覆盖。

新增真实 CLI 断言覆盖完整音源指纹、缺当前配置仍读取报告快照、失败/未完成快照、超预算省略、无效哈希、空事件和全部 mute、匹配哈希且保存 QA 为 passed 的全静音主 WAV、单条空轨及缺配置/普通缺乐谱的诊断区分；原完整验收继续执行。另以捕获的 0.2.0 响应验证旧 v2 schema，并确认新摘要冒用旧版本会被严格拒绝。

## 边界

尚待独立复审。没有试听结论，仍只验证当前 Windows 主机、两个锁定音源与一个 Surge profile；未声称新建虚拟环境或全新 OS。报告无签名，音源快照不认证来源。Pedalboard 0.9.26 兼容钩子、SF2 的功能省略及原有重复性容差均保留。
