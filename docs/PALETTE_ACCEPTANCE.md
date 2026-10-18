# 0.5.0 音源扩展验收

2026-10-12，在 Windows x64 / Python 3.13.7 上完成。目标是让 Agent 继续使用熟悉的 JSON 乐谱和 validate/render/inspect，不承担插件窗口、预设恢复和采样加载的操作。

## 交付范围

共 12 个固定音源：既有 Salamander 钢琴、两套 AVL 鼓组和 Surge init；新增 VSCO 长笛、小号、小提琴组持续音，以及 Surge 厂方电钢琴、贝斯、拨弦、Lead、FM Pad。新增音源沿用 beat/duration/pitch/velocity 字段。音域由 instruments 查询并由 validate 强制检查；新增 8 项不支持 CC。

复制 `examples/orchestra-sketch.json` 或 `examples/electronic-sketch.json` 后修改音符和 instrument 即可。详细入口见 `AGENT_QUICKSTART.md`；版本、来源、权利和能力边界见 `INSTRUMENTS.md`。

## 真实证据

完整验收：`outputs/acceptance-20261012-224457/summary.json`，status=passed，81 次 CLI 调用、65 项检查全部通过。

2026-10-18 补记：维护者确认完整验收目录在清理磁盘空间时删除。上述路径仅用于标识当时的验收运行，不是当前可下载的证据入口；本页保留已完成的验收结论与指标，无需为恢复已删除产物重复执行验收。

- 12 个音源实际无 GUI 加载与演奏；音域/力度网格、已准入 CC、异常输入、资源损坏、超时隔离与产物完整性均检查。
- 三类 VSCO 完整准入音域逐键有声，跨独立进程重复渲染最大逐采样差异为 0。
- 五个厂方电子 profile 在 48kHz 和 44.1kHz 下复现；低/中/高音各检查力度 1/64/127。每个力度点独立初始化，避免效果残响污染测量；连续音符另行比较。最大逐采样差异为 0。
- 管弦和电子公开示例在两种采样率下各渲染两次，主音频与全部分轨最大逐采样差异为 0；48kHz 下刻意修改第一轨音符，只目标轨变化。
- 两套鼓组的逐键与真实节奏复现、打击乐 MIDI 通道，以及实际 DLL/SF2 中文和空格路径均通过。

独立 wheel 安装：`outputs/package-0.5.0-verification/summary.json`，status=passed；0.5.0 包中的两个公开示例均实际 validate/render/inspect 成功。包不含采样和插件。

资源查询：`outputs/asset-cache-verification/summary.json`，status=passed；12 项 instruments 查询耗时 2.286 秒。共享资源只在同一次命令内计算一次指纹，错误哈希以及下一次命令前的文件改动仍会拒绝。

本机完整 doctor 约 60 秒；三轨管弦示例每次 render 约 50 秒，六轨电子示例约 12 秒。它们包含独立进程加载和技术检查，是本机实测耗时，不是实时预览承诺。正常改谱循环无需反复运行完整 doctor。

## 稳定性与边界

SFZ 随机缺样的根因是实时磁盘串流跟不上高速离线渲染；现在启用 freewheel 同步读样和 1024 KiB preload，正式乐谱只渲染一次。Surge 不再注入初始化音符；恢复并检查 patch 后，以空 MIDI 完成静音平滑，避免 Pad 残留音。厂方 profile 保留效果及内嵌 wavetable，同时记录相位重触发、关闭漂移和力度响应的修改。

本轮工程验收通过，不表示完成主观听感评估。仅验证 Windows x64 与锁定版本；VSCO 只包含三个持续音演奏法。BBC Discover 的厂商安装及无 GUI 使用尚未完成；Virtuosity Drums 的多麦克风控制未接入。任意预设、keyswitch、expression、pitch bend 和插件参数自动化不在交付范围。

验收当时的音频、下载与中间文件保存在本地项目内。大体积验收产物后来已按磁盘清理需要删除；仓库不分发这些本地目录。安装验证和资源查询的摘要按现存记录保留，后续验证按改动影响范围执行。
