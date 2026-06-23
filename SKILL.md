---
name: pdf2md
description: >
  PDF to Markdown converter with embedded image extraction. Uses Microsoft's markitdown for text
  extraction and PyMuPDF for image extraction, then automatically inserts image references into
  the generated Markdown. This skill should be used when the user asks to convert a PDF to Markdown,
  extract images from a PDF, or create a LLM-friendly document from a PDF paper. Trigger phrases
  include: "convert PDF to markdown", "pdf to md", "extract images from PDF", "论文转markdown",
  "PDF 转 Markdown", "pdf2md", and any request involving PDF + Markdown conversion.
---

# PDF to Markdown with Image Extraction

Convert PDF files to Markdown format while preserving embedded images. Uses Microsoft's
`markitdown` for high-quality text extraction and `pymupdf` (fitz) for image extraction,
then automatically matches figure references (e.g., "Figure 1", "Fig. 2") in the text
and inserts `![Figure N](images/xxx.png)` at the appropriate locations.

## When to Use

Use this skill when the user:
- Wants to convert a PDF to Markdown format
- Needs to extract images from a PDF along with text
- Wants LLM-friendly formatted paper/document content
- Mentions "pdf2md", "PDF 转 Markdown", "论文转 markdown"
- Asks to convert a research paper for reading/processing

## Dependencies

Before using, ensure dependencies are installed:

```bash
pip install "markitdown[all]" pymupdf
```

## Usage

Run the bundled script `scripts/pdf2md.py`:

```bash
# Basic usage (outputs to <pdf_name>_md/ directory)
python scripts/pdf2md.py "paper.pdf"

# Specify output directory
python scripts/pdf2md.py "paper.pdf" -o ./output_dir

# Text only, no image extraction
python scripts/pdf2md.py "paper.pdf" --no-images
```

### Output Structure

```
<output_dir>/
├── <pdf_name>.md     # Markdown with text + image references
└── images/           # Extracted embedded images
    ├── page04_img01.png
    ├── page08_img01.png
    └── ...
```

## How It Works

1. **Text extraction**: Calls `markitdown` Python API to convert PDF text to Markdown
2. **Image extraction**: Uses `pymupdf` (fitz) to extract all embedded images from each page
3. **Figure matching**: Scans the Markdown text for patterns like "Figure 1", "Fig. 2", etc.,
   and matches them to the extracted images based on order and heuristics
4. **Reference insertion**: Inserts `![Figure N](images/xxx.png)` after matched figure
   captions, and appends unmatched images to a "图片附录" (image appendix) section

## Limitations

- Only extracts embedded images (raster/vector), not text-rendered figures
- Image-to-figure matching is heuristic and may not be 100% accurate for all PDFs
- Requires `markitdown` and `pymupdf` to be installed in the Python environment
- `ffmpeg` warning can be safely ignored (only needed for audio conversion)
