# MinerU Windows 转换器

一个 Windows 源码版桌面包装器：用 Python/Tk 选择 PDF、指定页码，调用本机 MinerU 识别为 Markdown，再通过 Pandoc 和 Typst 生成便于阅读的 PDF。

本项目独立于 MinerU 官方。本仓库提供 GUI、脚本及排版模板，不包含模型、Python 环境、第三方工具或打包好的 EXE，也未附带来源尚未核实的图标。

## 安装

需要 Windows、Windows PowerShell，以及以下依赖：

| 依赖 | 要求与用途 |
| --- | --- |
| Python | MinerU 4.1.7 要求 `>=3.11,<3.15`；建议标准 Python 3.13 安装版，并启用 Tcl/Tk 与 Python Launcher |
| MinerU | 固定为本机验证版本 `4.1.7`，负责 PDF 识别 |
| Pandoc | 负责 Markdown 到 Typst 的转换 |
| Typst | 使用 `0.15`，负责 PDF 排版和 PNG 预览 |

先自行安装 [Python](https://www.python.org/downloads/windows/)、[Pandoc](https://pandoc.org/installing.html) 和 [Typst](https://github.com/typst/typst/releases)。在仓库目录打开 PowerShell，安装 Python 依赖：

```powershell
py -3.13 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

也可以在已激活的 Python 环境中运行：

```powershell
pip install -r requirements.txt
```

GUI 使用 Python 标准库 `tkinter`，不需要另装 GUI 包。可运行 `python -m tkinter` 检查当前 Python 是否带有 Tk。

Pandoc、Typst 应加入 `PATH`。MinerU 可安装在仓库的 `venv`，或加入 `PATH`；也可以在启动前指定可执行文件：

```powershell
$env:MINERU_EXE = 'D:\tools\mineru\venv\Scripts\mineru.exe'
$env:PANDOC_EXE = 'D:\tools\pandoc\pandoc.exe'
$env:TYPST_EXE = 'D:\tools\typst\typst.exe'
```

`MINERU_HOME` 默认使用仓库内的 `home` 目录，也可以在启动前设置为其他本地目录。首次运行可能需要下载模型并加载解析服务，请按 [MinerU 官方文档](https://opendatalab.github.io/MinerU/)准备所需模型和运行环境。硬件需求、下载要求及模型授权以所用版本的官方说明为准。

可选环境变量 `MINERU_TIER` 默认为 `standard`。具体档位是否可用取决于硬件与 MinerU 官方配置；脚本不会在失败时自动切换档位。

排版模板随仓库保存在 `templates/math-doc.typ`，转换时会复制到输出目录；请保留该文件。

## 使用

双击 `启动.cmd`。它优先使用仓库内的 `venv\Scripts\python.exe`，找不到时使用 `py -3`，并保留控制台以便查看启动错误。也可双击 `MinerU转换器.pyw`（使用系统关联的 Python），或运行：

```powershell
python "MinerU转换器.pyw"
```

1. 添加一个或多个 PDF。
2. 页码留空表示全文；也可输入 `20-35` 或 `1-5,8`，使用从 1 开始的页码。
3. 选择 PDF、Markdown 或两种格式，开始转换。

命令行入口仍可单独使用：

```powershell
.\pdf2md.cmd 'D:\books\book.pdf'
.\pdf2md.cmd 'D:\books\book.pdf' '1-5,8'
.\md2pdf.cmd 'D:\books\book_mineru\book.md'
```

`pdf2md.cmd` 和 `md2pdf.cmd` 调用同目录 PowerShell 脚本。选择只导出 Markdown 时不需要 Pandoc 或 Typst。

## 输出与原件保护

输入 `D:\books\book.pdf`，全文转换会在其旁边新建 `book_mineru` 目录；指定 `1-5,8` 时目录名为 `book_mineru_p1-5,8`。文件名沿用原书名：

```text
book.pdf
book_mineru/
  book.md
  book.pdf
  book.typ
  math-doc.typ
  book-preview-1.png
  ...
```

其中 `.typ`、模板与逐页 PNG 预览在生成 PDF 时产生并保留。MinerU 产生的其他资源也保存在输出目录。含公式的 PDF 由 Typst 排版，公式会先从 Markdown 转换为 Typst 语法。

输出目录已存在时，程序会拒绝再次转换。请先检查并手动重命名或移走已有目录后重试；程序不覆盖输入 PDF，也不自动清空旧结果。

在 GUI 中只选择 PDF 时，仅在本次 PDF 生成成功后删除本次创建的中间 Markdown；失败则保留 Markdown 便于检查和重试。选择 Markdown 或两种格式时保留 `.md`。Typst 源文件和预览图片始终保留，便于核对公式、中文与分页。

## 验证范围与限制

本次本地验证覆盖输出目录保护、失败处理等安全行为，以及 Typst 样例的编译和 PNG 预览；没有重新运行完整 OCR 流程。MinerU `4.1.7` 来自本机已安装并使用的版本，不代表其他版本已验证。

识别与排版结果需要人工核对，尤其是公式、表格、图片及阅读顺序。处理时间和识别精度随硬件、模型、输入质量与页数变化，本项目不承诺固定耗时或精度。生成 PDF 后请查看输出目录中的预览，必要时编辑 `.typ` 后重新编译。

若无法启动，先使用 `启动.cmd` 查看控制台；若某个依赖找不到，检查运行本程序的环境、`PATH` 和上面的可执行文件变量。转换失败时查看 GUI 输出以及当前 `MINERU_HOME` 下的日志；分享错误信息前请删除个人路径、文档内容和凭据。

## 仓库内容与授权

本仓库仅外部调用 MinerU、Pandoc、Typst，不分发这些工具或模型。第三方工具、依赖及模型分别适用各自授权，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

包装器源码的许可证尚未选择，目前没有 `LICENSE` 文件；第三方工具的许可证不代表本包装器采用同一许可证。

`.gitignore` 排除了本地运行环境、模型、MinerU 状态目录、缓存、日志、数据库、凭据、个人文档和转换目录。上传前仍应检查待提交文件，避免把自己的 PDF 或识别结果一并提交。
