# 2026-10-13 持久安装验证

本次部署使用 `release.lock.json` 锁定的官方完整 Windows 包：PDFMathTranslate Next 2.9.0、BabelDOC 0.6.4、自带 Python 3.13.3。安装包 SHA256 验证通过，14 个科研保护补丁文件完成部署与校验，原文件保留在回滚备份中。

默认安装位置调整到 `%USERPROFILE%\Documents\Codex\DevTools\apps\PDFMathTranslate\2.9.0-safety-v1`，与持久工具根目录要求一致。`Install.ps1`、`Start.ps1`、`Test.ps1` 及测试运行时定位保持一致；`-InstallRoot` 仍支持其他已部署位置。

安装、官方离线资源、备份和启动脚本不依赖聊天目录。DevTools 注册表登记了安装位置、运行时、启动入口、发行锁与依赖清单；源码位于持久 Projects 目录。

验证结果：

- 官方发行包 SHA256 与仓库锁一致。
- 14 个补丁文件校验通过，重复安装不产生额外修改。
- 8 项部署测试通过，包括完整基线安装、幂等、拒绝未知修改、版本及路径检查、回滚。
- 12 项科研保护测试通过。
- 两页合成 PDF 的离线完整流程通过。
- 模拟模型破坏公式占位符时，阻止生成 PDF。
- 迁入 DevTools 后重复运行全部检查，结果通过。

本次完整流程使用合成文档与离线模拟模型，验证安装和补丁行为，没有发送用户论文、没有调用用户付费接口。已有私人接口配置原样保留，不进入仓库。真实接口的连接与翻译效果应在用户选择服务后另行验证。

恢复时保留版本目录中的 `downloads`、`patch-backups` 和 DevTools 中登记的锁文件。关闭软件后使用 `manage_patch.py restore` 回滚代码，或重新执行 `Install.ps1` 恢复保护补丁。完整操作参见 README。
