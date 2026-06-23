#!/usr/bin/env python3
"""
pdf2md.py — PDF 转 Markdown + 图片提取一体化

用法:
    python pdf2md.py input.pdf                          # 输出到 input/ 目录
    python pdf2md.py input.pdf -o output_dir            # 指定输出目录
    python pdf2md.py input.pdf --no-images              # 只转文字，不提取图片
    python pdf2md.py input.pdf --max-img-size 500       # 图片最长边不超过500px（节省空间）

依赖:
    pip install markitdown[all] pymupdf Pillow
"""

import argparse
import subprocess
import sys
import os
import re
import shutil
from pathlib import Path

# ============================================================
# 图片提取 (pymupdf)
# ============================================================

def extract_images_pymupdf(pdf_path: Path, out_dir: Path, max_size: int = 1200) -> list[tuple]:
    """
    从 PDF 提取所有嵌入图片，保存到 out_dir/images/
    返回 [(page_num, image_index, relative_path), ...]
    同时尝试记录图片在页面上的位置（用于按阅读顺序插入）
    """
    try:
        import fitz
    except ImportError:
        print("[WARN] pymupdf 未安装，跳过图片提取: pip install pymupdf")
        return []

    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    records = []  # [(page, img_order, filename), ...]
    doc = fitz.open(str(pdf_path))

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        page_images = []  # 本页图片 (xref, top_y)
        for img_info in image_list:
            xref = img_info[0]
            # 获取图片在页面上的位置
            try:
                img_rects = page.get_image_rects(img_info)
                top_y = img_rects[0][1] if img_rects else 9999
            except Exception:
                top_y = 9999
            page_images.append((xref, top_y, img_info))

        # 按从上到下排序
        page_images.sort(key=lambda x: x[1])

        for order, (xref, top_y, img_info) in enumerate(page_images):
            try:
                pix = fitz.Pixmap(doc, xref)

                # 如果色彩空间不是 RGB，转换
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                # 确定后缀
                ext = "png"
                img_bytes = pix.tobytes("png")

                # 如果图片够大（不是小图标/logo）
                w, h = pix.width, pix.height
                if w < 50 or h < 50:
                    continue  # 跳过太小的图（可能是图标）

                fname = f"page{page_num + 1:02d}_img{order + 1:02d}.{ext}"
                fpath = img_dir / fname

                with open(fpath, "wb") as f:
                    f.write(img_bytes)

                rel_path = f"images/{fname}"
                records.append((page_num + 1, order, rel_path, top_y))
                print(f"  [IMG] p{page_num + 1} #{order + 1} -> {rel_path} ({w}x{h})")

            except Exception as e:
                print(f"  [WARN] p{page_num + 1} 图片提取失败: {e}")

    doc.close()
    return records


# ============================================================
# Markdown 生成 (markitdown)
# ============================================================

def run_markitdown(pdf_path: Path, out_md: Path) -> str:
    """调用 markitdown Python API 生成 markdown"""
    try:
        from markitdown import MarkItDown
    except ImportError:
        # 回退到 CLI
        cmd = ["markitdown", str(pdf_path), "-o", str(out_md)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and "ffmpeg" not in result.stderr.lower():
            print(f"[WARN] markitdown 警告: {result.stderr.strip()}")
        return out_md.read_text(encoding="utf-8")

    md = MarkItDown()
    result = md.convert(str(pdf_path))
    md_text = result.text_content
    out_md.write_text(md_text, encoding="utf-8")
    return md_text


# ============================================================
# 图片引用插入策略
# ============================================================

def insert_image_refs(md_text: str, img_records: list[tuple], out_dir: Path) -> str:
    """
    在 Markdown 中智能插入图片引用。
    策略:
    1. 查找 "Figure N" / "Fig. N" 文本 -> 在提及后插入
    2. 剩余的按页码插入到每页末尾
    """
    if not img_records:
        return md_text

    lines = md_text.split("\n")
    used_imgs = set()

    # 策略1: 按 Figure 编号匹配
    # 提取每张图片的页码
    page_images = {}  # {page: [(rel_path, top_y), ...]}
    for page, order, rel_path, top_y in img_records:
        page_images.setdefault(page, []).append((rel_path, top_y))

    # 尝试匹配 "Figure N" 引用
    figure_pattern = re.compile(r'(Figure\s*\d+|Fig\.\s*\d+)', re.IGNORECASE)

    new_lines = []
    img_idx = 0
    page_fig_count = {}  # {page: count} 每页已匹配的 Figure 数量

    for line_num, line in enumerate(lines):
        new_lines.append(line)

        # 找到 Figure 提及
        m = figure_pattern.search(line)
        if m:
            fig_text = m.group(0)
            fig_num = re.search(r'(\d+)', fig_text)
            if fig_num:
                fig_num = int(fig_num.group(1))

        # 检查当前行所属的"页码上下文"
        # markitdown 有时输出 <!-- page N --> 注释
        page_m = re.search(r'<!--\s*page\s*(\d+)\s*-->', line)
        if page_m:
            page = int(page_m.group(1))
            # 在该页注释后插入该页剩余未用的图片
            if page in page_images:
                remaining = page_images[page]
                if remaining:
                    for rel_path, _ in remaining:
                        new_lines.append("")
                        new_lines.append(f"![Figure]({rel_path})")
                        new_lines.append("")

    # 策略2: 如果没有按页插入，在文末追加所有图片
    has_page_refs = any("<!-- page" in l for l in lines)
    if not has_page_refs:
        new_lines.append("")
        new_lines.append("---")
        new_lines.append("")
        new_lines.append("## 论文图片")
        new_lines.append("")
        for page, order, rel_path, top_y in img_records:
            caption = f"Page {page}, Image {order + 1}" if hasattr(img_records[0], '__len__') and len(img_records[0]) > 2 else f"Image {order + 1}"
            new_lines.append(f"![{caption}]({rel_path})")
            new_lines.append("")

    return "\n".join(new_lines)


def insert_image_refs_smart(md_text: str, img_records: list[tuple]) -> str:
    """
    智能插入图片：在每页的 <!-- page N --> 注释后插入该页的图片。
    如果没有分页注释，则在 Figure/Fig 提及附近插入，其余放到文末。
    """
    if not img_records:
        return md_text

    # 按页码组织图片
    page_imgs = {}
    for page, order, rel_path, top_y in img_records:
        page_imgs.setdefault(page, []).append(rel_path)

    lines = md_text.split("\n")

    # 检查是否有 <!-- page N --> 分页标记
    has_page_markers = any(re.search(r'<!--\s*page\s*\d+\s*-->', l) for l in lines)

    if has_page_markers:
        # 在分页标记后插入图片
        new_lines = []
        for line in lines:
            new_lines.append(line)
            m = re.search(r'<!--\s*page\s*(\d+)\s*-->', line)
            if m:
                page = int(m.group(1))
                if page in page_imgs and page_imgs[page]:
                    new_lines.append("")
                    for rel_path in page_imgs[page]:
                        new_lines.append(f"![Figure - Page {page}]({rel_path})")
                    new_lines.append("")
        return "\n".join(new_lines)

    else:
        # 没有分页标记：尝试匹配 Figure 编号
        # 在第一次出现 "Figure" 的段落后插入图片
        result_lines = []
        img_queue = list(img_records)  # [(page, order, rel_path, top_y), ...]
        inserted = set()

        for i, line in enumerate(lines):
            result_lines.append(line)

            # 查找 Figure N 模式
            fig_match = re.search(r'(?:Figure|Fig\.)\s*(\d+)', line, re.IGNORECASE)
            if fig_match and img_queue:
                fig_num = int(fig_match.group(1))
                # 尝试匹配：第 N 个 Figure 对应第 N 张图
                if fig_num <= len(img_queue):
                    idx = fig_num - 1
                    if idx not in inserted and idx < len(img_queue):
                        page, order, rel_path, top_y = img_queue[idx]
                        result_lines.append("")
                        result_lines.append(f"![Figure {fig_num}]({rel_path})")
                        result_lines.append("")
                        inserted.add(idx)

        # 剩余未插入的图片放到文末
        remaining = [(p, o, r, t) for i, (p, o, r, t) in enumerate(img_records) if i not in inserted]
        if remaining:
            result_lines.append("")
            result_lines.append("---")
            result_lines.append("")
            result_lines.append("## 图片附录")
            result_lines.append("")
            for page, order, rel_path, top_y in remaining:
                result_lines.append(f"![Page {page}, Image {order + 1}]({rel_path})")
                result_lines.append("")

        return "\n".join(result_lines)


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="PDF → Markdown + 图片提取 一体化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pdf2md.py paper.pdf
  python pdf2md.py paper.pdf -o output/
  python pdf2md.py paper.pdf --no-images
  python pdf2md.py paper.pdf --max-img-size 800
        """
    )
    parser.add_argument("pdf", type=Path, help="输入 PDF 文件路径")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="输出目录 (默认: PDF同目录下的 <文件名>_md/)")
    parser.add_argument("--no-images", action="store_true",
                        help="不提取图片，仅转换文字")
    parser.add_argument("--max-img-size", type=int, default=1200,
                        help="图片最长边限制 (默认: 1200px)")
    parser.add_argument("--png", action="store_true",
                        help="图片保存为 PNG (默认)")
    args = parser.parse_args()

    pdf_path = args.pdf.resolve()
    if not pdf_path.exists():
        print(f"[ERROR] 文件不存在: {pdf_path}")
        sys.exit(1)

    # 输出目录
    if args.output:
        out_dir = args.output.resolve()
    else:
        out_dir = pdf_path.parent / f"{pdf_path.stem}_md"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / f"{pdf_path.stem}.md"

    print(f"[INFO] 输入: {pdf_path}")
    print(f"[INFO] 输出: {out_dir}")
    print()

    # Step 1: 提取图片
    img_records = []
    if not args.no_images:
        print("[1/2] 提取图片...")
        img_records = extract_images_pymupdf(pdf_path, out_dir, args.max_img_size)
        print(f"      提取了 {len(img_records)} 张图片\n")
    else:
        print("[1/2] 跳过图片提取\n")

    # Step 2: MarkItDown 转换
    print("[2/2] MarkItDown 文字转换...")
    md_text = run_markitdown(pdf_path, out_md)
    print(f"      文字已保存: {out_md}")
    print()

    # Step 3: 插入图片引用
    if img_records:
        print("[3/3] 插入图片引用...")
        md_text = insert_image_refs_smart(md_text, img_records)
        out_md.write_text(md_text, encoding="utf-8")
        print(f"      已更新: {out_md}")
        print()

    # 汇总
    print("=" * 60)
    print("  完成!")
    print(f"  输出目录: {out_dir}")
    print(f"  Markdown: {out_md.name}")
    if img_records:
        print(f"  图片数量: {len(img_records)} 张 → images/")
    print("=" * 60)


if __name__ == "__main__":
    main()
