# 参与开发

code-to-music 当前支持 Windows x64 的 12 个固定音源。建议使用 64 位 Python 3.13，按 [README](README.md) 安装依赖、FFmpeg 和音源。修改 Python 代码时可使用 editable 安装：

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

## 验证改动

选择能暴露实际问题的最小验证范围。已经完成的 0.5.0 音源验收见 [验收摘要](docs/PALETTE_ACCEPTANCE.md)，清理其大体积产物不要求重新验收。

| 改动 | 建议验证 |
|---|---|
| 文档、包元数据、发布配置 | 检查说明和链接；构建普通 wheel，检查包内容及安装后命令 |
| 乐谱解析、CLI 或报告协议 | 最小有效和无效输入；检查退出码、JSON schema、错误码及修复建议 |
| 某一后端或音源 | 实际渲染受影响音源，inspect 检查；涉及时序或状态恢复时比较重复渲染和目标分轨修改 |
| 公共渲染链路或依赖升级 | 扩大到受影响的所有后端；影响广泛时执行 scripts/acceptance.py |

`.github/workflows/checks.yml` 在 Windows / Python 3.13 上检查 wheel 构建、打包内容、示例 schema 和安装后的基础 CLI。它不下载音源，也不代表 native 渲染或听感通过。完整回归仍使用现有 `scripts/acceptance.py`，按需要执行。

新增音源需要记录固定版本、来源、许可、资产指纹、支持的音域/控制器，以及真实加载、演奏、重复渲染结果。不要通过重试、放宽音频阈值或改报告来掩盖失败。主观试听与技术指标分别记录。

## 提交问题或修改

问题报告请附：工具版本、Windows 和 Python 版本、最小 UTF-8 乐谱、实际命令、退出码及 JSON 错误。如果是安装问题，再附 `python --version` 和 `ffmpeg -version` 的结果。日志可能包含用户名和绝对路径，请用占位符替换这些信息。

提交修改时说明用户遇到的问题、修改后的行为及实际验证结果。不要提交 `resources/`、`outputs/`、`work/`、`.music/`、本机配置、插件或采样文件。新增依赖或复制第三方代码时记录其来源和许可证。自有代码采用 [MIT](LICENSE)；请确认你有权提交贡献，并说明任何不同的第三方许可。
