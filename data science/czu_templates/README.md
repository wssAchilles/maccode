# 常州工学院数据科学系列课程 — 大作业 LaTeX 模板

本仓库包含用于常州工学院数据科学系列课程大作业的 LaTeX 模板（`template.tex`）及相关资源（`assets/`）。本 README 简要说明如何使用该模板在本地或在线（Overleaf）编译，并给出若干使用 Word 的替代方案与注意事项。

**文件结构**

- `template.tex`：主 LaTeX 源文件（报告正文、封面、目录等）。
- `assets/`：图片、logo、样式或其他资源。
- `README.md`：本说明文档。

**先决条件（推荐）**

- TeX 发行版：Mac 推荐安装 MacTeX（包含 XeLaTeX 等）。
- 推荐命令行工具：`xelatex`、`latexmk`。如需将 Word 转换为 LaTeX，请安装 `pandoc`。

**在本地编译（推荐 XeLaTeX，以支持中文）**

1. 打开终端，切换到本模板目录。
2. 运行（简单两遍编译）：

```bash
xelatex template.tex
xelatex template.tex
```

3. 如果有参考文献（`.bib`），请在中间运行 `bibtex` 或使用 `biber`（视模板而定）：

```bash
# 如果使用 bibtex
bibtex template
xelatex template.tex
xelatex template.tex

# 或者使用 latexmk（自动处理多轮编译、bib/biber）
latexmk -xelatex template.tex
```

注意：若模板中使用了特定宏包或自定义字体，需要保证本地 TeX 环境已安装相应字体与宏包。

**在 Overleaf 上使用**

1. 登录 Overleaf，创建新项目并选择 "Upload Project"。
2. 上传 `template.tex`、`assets/` 下所有文件。
3. 在 Overleaf 的项目设置里将编译器设为 `XeLaTeX`（或模板指定的编译器），然后点击 Recompile。

**如果你更习惯用 Word（.docx）**
模板仓库中默认有一个 Word 模板；如果你确实要用 Word 完成报告，请参考下列两种常见做法：

1) 最简单、最可靠的方式 — Word 写作并导出 PDF 提交：

  - 在 Word 中按模板要求排版（封面、摘要、章节、图表、参考文献等）。
  - 使用 Word 的“另存为 PDF”或“导出为 PDF”功能生成最终提交文件。
  - 提交 PDF（如果老师需要源文件，可同时上传 `.docx`）。

2) 将 Word 转成 LaTeX（适合想利用模板外观但源为 Word 的情况）：

  - 使用 `pandoc` 将 `.docx` 转为 `.tex`：

```bash
pandoc report.docx -o report.tex --standalone
```

  - 采用该方法生成的 LaTeX 文件通常需要手动调整（公式、图表、图像路径和样式可能不完全匹配 `template.tex`），之后将内容合并进 `template.tex`，并用 XeLaTeX 编译。

提示：自动转换可能无法完美保留复杂排版与数学公式，请务必校对生成的 `.tex` 和最终 PDF。

**提交建议**

- 最终提交 PDF（`report.pdf`）。
- 如有要求提交源文件，可一并提交 `template.tex`、`assets/` 及 `.bib`（若有）。
- 若使用 Word，请同时提交 `.docx`（以便评分者复现或修改）。

**常见问题**

如果编译时报错，先查看终端输出，定位缺失的宏包或字体；常见解决方式是通过 TeX 发行版的包管理器安装缺失包。若为图片路径错误，确认图片位于 `assets/`，并在 `.tex` 中使用相对路径引用。
