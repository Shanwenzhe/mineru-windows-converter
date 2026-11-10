# 第三方说明

本项目是独立的 Windows 转换包装器，不是 MinerU、Pandoc 或 Typst 的官方产品。仓库仅通过外部进程调用用户自行安装的工具，不随仓库分发第三方可执行文件、Python 环境或模型。下列许可说明不替代各项目随具体版本提供的完整许可。

| 项目 | 用途 | 许可与来源 |
| --- | --- | --- |
| [MinerU](https://github.com/opendatalab/MinerU) | PDF 识别与 Markdown 导出；本仓库依赖固定为 `4.1.7` | [MinerU Open Source License](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md)，基于 Apache License 2.0 并附加条件，不应简写为纯 Apache-2.0 |
| [Pandoc](https://github.com/jgm/pandoc) | 将 Markdown 转为 Typst 源文件 | GPL-2.0-or-later，见[官方仓库 COPYING.md](https://github.com/jgm/pandoc/blob/main/COPYING.md)及[官网](https://pandoc.org/) |
| [Typst](https://github.com/typst/typst) | 将 Typst 源文件编译为 PDF 和 PNG 预览；本项目使用 `0.15` | Apache License 2.0，见[官方仓库 LICENSE](https://github.com/typst/typst/blob/main/LICENSE) |

MinerU 的附加条件涉及商业许可门槛和在线服务标识等事项，使用时应阅读所安装版本的完整许可。模型权重、字体及各工具的间接依赖可能适用单独条款，由用户按实际安装和使用的内容分别确认。

本仓库不包含原本地图标，因其来源和再分发授权尚未核实。

本项目维护者有权授权的包装器源码、脚本、模板及文档采用 [MIT License](LICENSE)，版权署名为 `Copyright (c) 2026 Shanwenzhe`。本项目的 MIT 授权不适用于 MinerU、Pandoc、Typst、模型、字体或其他第三方内容，也不改变它们各自的许可与附加条件。
