# 乐谱 v1

规范 schema：`src/music/schemas/score-v1.json`，JSON Schema Draft 2020-12。公开接口是 CLI JSON 和乐谱文件；Python 内部模块暂不承诺稳定。现有 v1 字段的含义不做不兼容修改；扩展 schema/能力须显式验证，破坏性变化提升主版本。未知字段、未知版本、NaN/Infinity、重复 JSON 键全部拒绝。

```json
{
  "version": 1,
  "tempo": 120,
  "time_signature": [4, 4],
  "length_beats": 4,
  "tracks": [{
    "id": "piano",
    "instrument": "salamander-piano",
    "events": [{"type":"note","beat":0,"duration":2,"pitch":"C4","velocity":90}]
  }]
}
```

* `tempo`：20..300 BPM，固定速度。每个 `beat` 是四分音符，不随拍号分母变化。拍号是 MIDI 乐谱信息；不强制事件落在整小节。
* `length_beats`：乐谱总长；音符必须在范围内结束，CC 必须发生在结束点之前。实际 WAV 时长是 `round((length_beats*60/tempo + tail_seconds)*sample_rate)` 帧。必须至少 1 帧，否则 validate/dry-run/render 都以 `E_SCORE` 拒绝，并指引增加时长或尾音。上限 300 秒，最多 15 轨，每轨最多 10000 个事件。
* `pitch`：MIDI 整数或 `C4`、`F#3`、`Bb2`；C4=60。声明的音源范围当前为 MIDI 21..108；实际验证的离散点见验收证据，不代表每个半音都已试听。
* `duration`：至少 .001 拍；`velocity`：整数 1..127（0 不是音符）。不能把未验证力度层数写成已验证的全范围听感。
* `id`：ASCII 文件安全名称，大小写不敏感唯一；乐谱标题、输入路径和输出路径支持非 ASCII。
* `overlap=polyphonic`（默认）：允许不同音高交叠。同一音高的重叠无论模式都拒绝，避免 MIDI note-off 截断错误的声部。`reject` 禁止轨内任何音符重叠；需要同音高交叠则拆成多个轨。
* `mute=false`（默认）：静音轨不会启动 native 后端；分轨写零值，MIDI 中省略此轨。仍然校验该轨所有字段及资源引用。
* `gain_db=0`（默认）：轨道线性音频增益；不改 MIDI 力度，也不写成 MIDI CC7。
* CC：`{"type":"cc","beat":0,"controller":64,"value":127}`。当前只准入 CC64（0..63 松开、64..127 按下）。全局长度末尾自动释放 CC64，尾音继续渲染。未验证的控制器、演奏法、pitch bend、速度自动化、插件参数和 preset 选择全部在校验时拒绝。
* 同一采样位置执行顺序：note-off → CC → note-on；音频时刻四舍五入到采样帧，MIDI 时刻四舍五入到 960 PPQ。

输出选项默认：

```json
{"sample_rate":48000,"tail_seconds":2,"master_gain_db":-6,"stems":true,"midi":true,"intermediates":false}
```

采样率只准入 44100 / 48000；立体声 PCM24 固定。尾音 0..30 秒。分轨包括轨道增益和主增益，求和应与主输出只存在 PCM24 量化误差；报告记录实测误差和容差 `(轨数+1)/2^23`。不自动归一化或限幅，避免偷偷改变乐谱混音；超过技术阈值会失败并留证据。

技术检查：可解码、采样率/声道/帧数、非静音、采样峰值≤-1 dBFS、FFmpeg 过采样真峰值≤-1 dBTP、RMS -65..-6 dBFS、综合响度 -45..-6 LUFS。刻意静音/无音符的单条轨道免于非静音与响度下限检查。整份作品必须至少有一个未 mute 的 note；所有轨道空事件、仅 CC 或全部 mute 时，validate/dry-run/render 均返回 `E_SCORE`，指引添加音符或取消静音。主 WAV 在 render 和 inspect 中始终执行非静音检查，旧报告的静音豁免不能使它通过。短乐谱与长休止可能达不到 LUFS 下限；此时必须明确调整音乐或增益。`final_50ms_peak_dbfs` 高于 -60 会提示尾音尚未消失；当前只警告，未自动延长。

报告 v1 记录乐谱内容、源文件 SHA-256、配置 SHA-256、音源与后端路径/指纹、Python/库/FFmpeg 版本、实际执行参数、各轨与主输出检查、文件哈希和失败原因。实际后端的 `intermediates_retained` 表示 native 证据是否保留；关闭中间文件时 `command/log=null`。静音/无音符的轨道用 `backend.skipped`，没有 native 调用。

当前 CLI JSON 契约为 v3，inspect 摘要为 v2（完整报告和乐谱仍为 v1）。`inspect` 先验证报告格式与状态；failed/rendering 不会被空 artifacts 判为通过。只有 passed 报告登记必需产物、文件大小/哈希匹配、主输出解码和复查通过、保存的技术检查通过，才退出 0。默认输出摘要而不回显报告；`report_path` 是完整报告入口。`inspect` 不通过再次执行音源来认证原始音色。报告不带数字签名；修改报告本身不能被当成可信来源。

`inspect.data.instruments` 是报告中的选用音源 ID/版本和资产 SHA-256 快照，包含预算和省略计数；完整路径仍留在报告。`current_assets_verified=false` 表明 inspect 没有重验当前音源资产。失败/未完成报告中的快照不证明这些音源已经成功演奏，详见 [AGENT_QUICKSTART.md](AGENT_QUICKSTART.md)。
