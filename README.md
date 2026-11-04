# PDFMathTranslate 科研文档保护补丁

为 PDFMathTranslate Next **2.9.0** / BabelDOC **0.6.4** 的 Windows 版维护可重现的软件修复。重点解决科研 PDF 中公式方框、字体编码混淆、面积单位丢失和异常文字输出，并接入 DeepSeek 官方 API。

这是一份本地修复工程，不是上游官方发布。可以保护已识别的数值、公式、单位与标识符，但不能保证所有专业语义或所有 PDF 排版都完全正确。

## 持久部署与复用

软件安装在 `%USERPROFILE%\Documents\Codex\DevTools\apps\PDFMathTranslate\2.9.0-safety-v1\pdf2zh`，独立于聊天、临时目录及本仓库。通用开发工具优先复用本机已有 Git、GitHub CLI 和该发行版自带的 Python 3.13.3；无需为下一个工程重新安装这些工具。

本机维护源码固定放在 `%USERPROFILE%\Documents\Codex\Projects\pdfmathtranslate-scientific-safety`。更换聊天不会改变安装或源码位置。

| 内容 | 持久位置 |
| --- | --- |
| 软件及自带 Python、依赖 | `%USERPROFILE%\Documents\Codex\DevTools\apps\PDFMathTranslate\2.9.0-safety-v1\pdf2zh` |
| 独立启动脚本 | `%USERPROFILE%\Documents\Codex\DevTools\apps\PDFMathTranslate\2.9.0-safety-v1\Start-PDFMathTranslate.ps1` |
| 官方安装包缓存 | 工具目录下的 `downloads` |
| 部署前文件备份 | 工具目录下的 `patch-backups` |
| 启动日志 | 工具目录下的 `logs` |
| GUI 私人设置及 API 密钥 | `%USERPROFILE%\.config\pdf2zh\config.v3.toml` |
| 布局模型及字体缓存 | `%USERPROFILE%\.cache\babeldoc` |
| 输入暂存与翻译工作目录 | `%USERPROFILE%\Documents\Codex\PDFMathTranslate-data` |

工程归档时保留这些共享位置。Windows 发行版依赖应使用自己的运行时，不要混入其他工程的 Python 环境。

本次持久部署与验证记录见 [docs/deployment-validation.md](docs/deployment-validation.md)。安装版本及启动命令已登记到 DevTools 的 `registry.json`；`-InstallRoot` 可以复用其他已部署位置。

## 安装或验证已有安装

```powershell
git clone https://github.com/dadanmiao/pdfmathtranslate-scientific-safety.git
cd pdfmathtranslate-scientific-safety
./scripts/Install.ps1
```

安装脚本优先复用已有软件。需要安装时，下载 `release.lock.json` 指定的官方完整资源包，验证 SHA256，再部署修复。也可通过 `-ArchivePath` 使用本机缓存的官方 ZIP。脚本不改写 API 密钥或私人配置。

安装包约 621 MB；不要提交到 Git。`requirements.windows-inventory.txt` 记录官方发行包中 135 个 Python 包的版本供维护参考；受支持的 Windows 部署来源是锁定的完整发行包，不是逐个 `pip install` 重建这份环境。

```powershell
./scripts/Start.ps1
# 跨工程直接使用，不需要当前仓库：
& "$env:USERPROFILE\Documents\Codex\DevTools\apps\PDFMathTranslate\2.9.0-safety-v1\Start-PDFMathTranslate.ps1"
```

打开 http://127.0.0.1:7860/，上传 PDF 并点击“翻译”。页面底部显示“科研文档保护：已启用（本地修复版 1）”。

## 当前翻译配置

选择 DeepSeek 官方服务，模型 `deepseek-flash`、思考模式 `disabled`、JSON 模式关闭、QPS=4、自动术语提取启用。官方接口由原生 DeepSeek 适配器使用 `https://api.deepseek.com/v1`，请求超时为 120 秒。

`config.example.toml` 是无密钥模板；在界面自行填写官方 API 密钥并保存。不要用模板覆盖已经配置好的用户设置。真实密钥、其他平台的旧配置和日志全部留在本机。

## 修复范围

- 解决页面与 Form 同名资源的字体编码冲突，保留原始公式符号。
- 仅裁剪新增字体，避免改变原文已有字体的字形和字距。
- 将独立 Form 中的单位并入相邻数值，并避免旧 Form 边界裁掉移动后的单位。
- 保护常见 SI 数值/单位、技术标识符和图中信号名；表格翻译关闭时保留表内文字。
- 检查公式占位符丢失、重复和新增，拒绝无效模型文字；重试失败后停止生成。
- 拒绝无字体的译文字符，并检查实际排版文字的完整性。
- 修复新增字体的连字符 Unicode 别名，保留无轮廓空格的映射，避免复制文字出现控制字符。
- 对原文与输出中位置及字形一致的 Symbol 字体私有区字符，避免因 Unicode 映射差异产生缺字误报。
- DeepSeek 新模型别名遵守关闭思考的设置；本地启动采用短路径，HTTPS 证书验证保持启用。

详细原因与维护规则见 [docs/maintenance.md](docs/maintenance.md)。

## 验证

```powershell
./scripts/Test.ps1
./scripts/Test.ps1 -Pipeline
# 可选：对本机已有论文做离线结构回归，文件不会上传或提交：
./scripts/Test.ps1 -Pipeline -SourcePdf 'C:\path\paper.pdf'
```

9 项部署测试验证安装幂等性、完整原版安装与回滚、旧补丁升级、校验失败时拒绝整批修改、版本检查和路径约束。13 项科研保护测试覆盖单位、公式占位符、无效 Unicode、图表保护、字体像素与文字映射。完整流程测试生成两页合成 PDF，使用模拟模型验证正常输出和错误拦截；模拟结果只用于测试，不是实际译文。

2026-10-13 已使用 DeepSeek 官方接口和当前 GUI 配置实际翻译四页论文，并逐页检查中文及双语输出。用户论文、实际译文和术语表只保存在本机，不提交仓库。GitHub Actions 自动运行部署测试和 Python 语法检查；完整 PDF 回归需要本地软件及资源缓存。

## 更新与恢复

补丁文件、官方基线、可审阅 diff 与 SHA256 清单分别放在 `patches/patched`、`patches/original`、`patches/review`、`patches/manifest.json`。重复应用不会重复修改。

软件升级可能覆盖修复。更新到其他版本前，重新适配补丁并测试，不能直接强行覆盖。回滚前关闭该软件：

```powershell
& "$env:USERPROFILE\Documents\Codex\DevTools\apps\PDFMathTranslate\2.9.0-safety-v1\pdf2zh\runtime\python.exe" ./scripts/manage_patch.py restore --app-dir "$env:USERPROFILE\Documents\Codex\DevTools\apps\PDFMathTranslate\2.9.0-safety-v1\pdf2zh"
```

回滚只还原清单中的代码文件，并保存被替换的内容，私人设置仍保留。需要重新启用修复时，再执行 `scripts/Install.ps1`。

## 许可

本工程包含上游派生源码，按 AGPL-3.0 提供。保留上游许可证及来源，见 [LICENSE](LICENSE) 和 [NOTICE.md](NOTICE.md)。
