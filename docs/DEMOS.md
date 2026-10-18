# 四首展示小曲

四首原创器乐曲由完整 JSON 乐谱生成。每首都有主题、段落变化和收尾；点击 MP3 下载或播放，也可以修改乐谱重新生成。

| 曲目 | 试听长度 | 乐谱主体 | 乐谱 | 编制 |
|---|---|---|---|---|
| 窗边微光 / Window Light | [MP3](audio/window-light.mp3) · 42.3 秒 | 41.74 秒 | [window-light.json](../examples/showcase/window-light.json) | 三层钢琴声部 |
| 律动工坊 / Pocket Workshop | [MP3](audio/pocket-workshop.mp3) · 40.1 秒 | 35.56 秒 | [pocket-workshop.json](../examples/showcase/pocket-workshop.json) | AVL Red Zeppelin 鼓组 |
| 林间晨行 / Morning Path | [MP3](audio/morning-path.mp3) · 33.4 秒 | 32.73 秒 | [morning-path.json](../examples/showcase/morning-path.json) | 长笛、小号、小提琴组 |
| 夜航 / After Hours | [MP3](audio/after-hours.mp3) · 35.3 秒 | 34.29 秒 | [after-hours.json](../examples/showcase/after-hours.json) | 电钢琴、贝斯、拨弦、Lead、Pad、Black Pearl 鼓组 |

乐谱主体按拍数和速度计算，不含尾音。鼓组最后的镲片自然衰减约占额外 4 秒；其余三首的试听接近主体长度。原先几秒钟的技术示例保留在 `examples/` 顶层，供快速入门和验收使用，不再作为主要试听展示。

## 乐谱怎么写

- **窗边微光：** D 大调，16 小节。右手提出主题并回答，左手分解和弦与内声部保持较轻力度；中段升高音区，结尾回到主音。踏板随和声更换。
- **律动工坊：** 16 小节 Funk 鼓组独奏。切分底鼓、轻军鼓和交替镲片重音形成律动；中间两小节让编制收敛，再以过门带回主节奏，最后完整落点。
- **林间晨行：** G 大调，12 小节。长笛与小号轮流承担旋律，弦乐从长音铺底转为分拍推进，增强后收束。按照现有持续音音源写作。
- **夜航：** D 小调，16 小节。电钢琴和拨弦引入，低音、鼓和主旋律依次进入；中段抽去鼓与 Lead，再以高音区旋律回归，最终由属和弦解决。

完整段落设计与重新生成方法见 [展示乐谱说明](../examples/showcase/README.md)。这里的修改不是把短循环重复拉长：旋律、和声进行、演奏力度、进出安排和句尾均写入乐谱。

## 这些示例证明什么

四段原始 PCM24 WAV 均通过 `music inspect` 的报告、文件完整性和音频复查，且报告内的乐谱与当前公开 JSON 内容一致。MP3 为 192 kbps 有损试听副本：裁掉多余的安静尾部，在末尾应用 50 ms 淡出，没有归一化或额外增益处理；已去除输入元数据并检查可解码。原始 WAV 和乐谱保留不变，精确音频指标针对原始 WAV，不宣称 MP3 与 WAV 逐采样相同。

试听制作时额外检查主体覆盖及末尾安静时长：以 100 ms 双声道 RMS 窗口和 −60 dBFS 为参考，四首的主体区间均有连续声音覆盖，结尾保留约 0.5 秒安静收尾，且未裁掉已安排的音符。这是本批展示的编辑检查，不是对所有音乐或渲染输出强制裁切的规则。

这里提供试听材料，**尚未记录维护者的主观听感确认**。技术检查不代表编曲或音色获得主观质量背书。

[manifest.json](audio/manifest.json) 记录版本、原始 WAV/试听文件 SHA-256、乐谱指纹、音源指纹和音量指标，不含本机绝对路径。四首均在 2026-10-18 根据新乐谱实际生成；既有短示例的完整音源验收未重跑。新作品通过 validate、dry-run、render、inspect，最终版本没有削波或尾音截断警告。

## 音源鸣谢与使用范围

- **钢琴：** Piano samples: Salamander Grand Piano by Alexander Holm; SF2 adaptation by Roberto / FreePats, V3+20200602. Licensed under [Creative Commons Attribution 3.0](https://creativecommons.org/licenses/by/3.0/)。
- **鼓组：** AVL Drumkits / Glen MacArthur，Red Zeppelin 与 Black Pearl。[来源与录制音乐例外](https://bandshed.net/avldrumkits/)，原始采样 CC-BY-SA-3.0。
- **管弦：** VSCO 2 Community Edition / Versilian Studios，采样 [CC0-1.0](https://github.com/sgossner/VSCO-2-CE)。
- **电子音色：** Surge XT 1.3.4；五个厂方预设来自 Claes。离线复现所需的相位、漂移和力度调整见 [音源说明](INSTRUMENTS.md)。

原创乐谱采用项目 MIT；音频涉及上述音源内容权利，不能仅凭项目 MIT 把原始采样或预设重新授权。软件和内容权利的区别见 [第三方声明](../THIRD_PARTY_NOTICES.md)。
