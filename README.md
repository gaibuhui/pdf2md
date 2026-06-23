# pdf2md — PDF 转 Markdown + 图片提取一体化

> 基于 Microsoft [MarkItDown](https://github.com/microsoft/markitdown) 的增强工具，补齐图片提取短板，一键生成完整可读的 Markdown 论文笔记。

---

## 🤔 为什么需要这个工具？

MarkItDown 很强大，能把 PDF/Word/PPT 等文件转成 Markdown，但它有个明显短板：

**图片全部丢失。** 学术论文中，图表（架构图、实验结果、对比表）往往是最核心的信息载体。只保留文字，等于丢掉了论文的"灵魂"。

`pdf2md` 解决了这个问题：

| 功能 | MarkItDown 原生 | pdf2md |
|------|:---:|:---:|
| PDF 文字提取 | ✅ | ✅ |
| 图片提取保存 | ❌ | ✅ pymupdf |
| 图片引用自动插入 | ❌ | ✅ Figure 编号匹配 |
| 一键输出完整 Markdown | ❌ | ✅ 文字+图片+引用 |

---

## 🚀 快速开始

### 安装

```bash
pip install markitdown[all] pymupdf Pillow
```

### 使用

```bash
# 基本用法
python pdf2md.py paper.pdf

# 指定输出目录
python pdf2md.py paper.pdf -o ./notes/

# 只要文字（和原生 markitdown 一样）
python pdf2md.py paper.pdf --no-images
```

### 输出结构

```
paper_md/
├── paper.md           # 完整 Markdown（文字 + 图片引用）
└── images/            # 提取的图片
    ├── page04_img01.png
    ├── page08_img01.png
    └── ...
```

生成的 Markdown 在 VS Code / Typora / GitHub 中可直接预览，图片正常显示。

---

## 🧠 核心改进

### 改进 1：图片提取（pymupdf）

```python
import fitz  # pymupdf

doc = fitz.open("paper.pdf")
for page in doc:
    for img in page.get_images(full=True):
        pix = fitz.Pixmap(doc, img[0])
        pix.save(f"page{page.number}_img{n}.png")
```

- 自动跳过小于 50px 的图标/logo
- 支持 CMYK→RGB 色彩空间转换
- 按页面位置（上→下）排序输出

### 改进 2：智能图片引用插入

这是最核心的改进。提取到 24 张图片后，不能简单全部堆在文末——需要插入到正确的位置。

**策略 1：Figure 编号匹配**

```python
# 匹配文中 "Figure 1"、"Fig. 2" 等引用
pattern = re.compile(r'(?:Figure|Fig\.)\s*(\d+)', re.IGNORECASE)
# 将第 N 张图插入到对应 Figure N 提及处
```

**策略 2：分页标记插入**

部分 PDF 转换后会保留 `<!-- page N -->` 注释，利用这个标记把图片插入到对应页码处。

**策略 3：文末附录**

无法匹配的图片放入 `## 图片附录` 中。

### 改进 3：API + CLI 双模式

优先使用 MarkItDown 的 Python API（避免 CLI 路径问题），失败时自动回退到命令行。

---

## 📊 效果对比

### 原生 MarkItDown 输出

```
DragMesh-2: Physically Plausible Dexterous...
Abstract: Dexterous interaction with...
1 Introduction
Dexterous hand interaction with articulated objects...
（图片全部缺失）
```

### pdf2md 输出

```markdown
DragMesh-2: Physically Plausible Dexterous...

Abstract: Dexterous interaction with...

1 Introduction
Dexterous hand interaction with articulated objects...

![Figure 1](images/page04_img01.png)

To address these challenges, we propose DragMesh-2...

![Figure 2](images/page08_img01.png)

Main comparison. Figure 2 and Table 2 report...

## 图片附录
![Page 18, Image 10](images/page18_img10.png)
```

---

## 🔧 技术栈

| 组件 | 用途 |
|------|------|
| [MarkItDown](https://github.com/microsoft/markitdown) | PDF 文字 → Markdown 转换 |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | PDF 嵌入图片提取 |
| Pillow | 图片格式处理 |

---

## 📝 适用场景

- **学术论文阅读**：PDF → 完整 Markdown 笔记，保留图表
- **LLM 输入预处理**：图文并茂的 Markdown 更适合 GPT/Claude 理解
- **知识库构建**：批量处理 PDF 论文，建立可搜索的 Markdown 知识库
- **RAG 系统**：完整的文档内容（含图表描述）提升检索质量

---

## 🤝 与 MarkItDown 的关系

本项目是 MarkItDown 的**增强脚本**，并非 fork。它：

- 复用 MarkItDown 的文字转换能力
- 新增 PyMuPDF 图片提取能力
- 通过智能匹配将两者整合为一体化输出

欢迎提交 PR 到 MarkItDown 主仓库，将图片提取功能内置！

---

## 📄 License

MIT — 与 MarkItDown 保持一致。
