#!/usr/bin/env python3
"""
extract_figs.py — Auto-extract main figures from a scientific PDF.

策略（无需手动 bbox）:
1. 全 PDF 扫描，识别 "Fig. N" / "Figure N" caption（不依赖字体加粗）。
2. 识别图页 = drawings 数量 >= 阈值（默认 100）的页面（矢量图版式）。
3. 把每个 Fig N 关联到对应的图页：
   - caption 与图同页 → 取 caption_top_y 作为图下边界。
   - caption 在文本页（顶部 y<100）→ 图在上一图页。
   - caption 在文本页（底部 y>500）→ 图在下一图页。
   - 图页无 caption → 整页作为 figure（用 drawings extent 作为边界）。
4. 渲染整页 → 按坐标裁剪 → 保存 PNG。

适用：Nature / Science / Cell / NEJM 等矢量图论文。
对光栅图嵌入的 PDF，可改用 page.get_images() 提取。

USAGE:
    python3 extract_figs.py <pdf_path> <output_dir> [--dpi 200] [--min-drawings 100]
"""
import fitz  # PyMuPDF
from PIL import Image
import io
import os
import re
import sys
import argparse


# 匹配行首的 "Fig. N" / "Figure N" / "Fig N"
CAPTION_RE = re.compile(r"^(Fig(?:ure|\.)?)\s*(\d+)\b", re.IGNORECASE)


def find_caption_on_page_explicit(page):
    """Return list of (fig_number, caption_top_y) for ALL figure captions on this page.

    逐 line 重构整行文本（caption 常被切成多 span），匹配行首 "Fig N"。
    """
    blocks = page.get_text("dict")["blocks"]
    results = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            line_text = "".join(s["text"] for s in line["spans"]).strip()
            m = CAPTION_RE.match(line_text)
            if not m:
                continue
            fig_num = int(m.group(2))
            line_top = min(s["bbox"][1] for s in line["spans"])
            results.append((fig_num, line_top))
    return results


def detect_figure_pages(doc, min_drawings=100):
    """Return dict {page_num_1based: drawings_count} for pages that look like figure pages."""
    figure_pages = {}
    for i in range(len(doc)):
        page = doc[i]
        n_draw = len(page.get_drawings())
        if n_draw >= min_drawings:
            figure_pages[i + 1] = n_draw
    return figure_pages


def scan_captions(doc):
    """Return dict {fig_number: [(page_num, caption_top_y), ...]} for all captions in PDF."""
    captions = {}
    for i in range(len(doc)):
        page = doc[i]
        for fig_num, cap_y in find_caption_on_page_explicit(page):
            captions.setdefault(fig_num, []).append((i + 1, cap_y))
    return captions


def match_figures_to_pages(figure_pages, captions):
    """对每个 fig 号决定其图像所在页。

    返回 {fig_num: (image_page, caption_top_y_on_same_page_or_None)}。
    """
    sorted_fig_pages = sorted(figure_pages.keys())
    fig_to_caption = {}
    for fig_num, occurrences in captions.items():
        occurrences.sort(key=lambda x: x[0])
        fig_to_caption[fig_num] = occurrences[0]  # 取首次出现

    fig_to_image_page = {}
    for fig_num, (cap_page, cap_y) in fig_to_caption.items():
        if cap_page in figure_pages:
            # caption 与图同页
            fig_to_image_page[fig_num] = (cap_page, cap_y)
        else:
            # caption 在文本页 → 找最近的图页
            if not sorted_fig_pages:
                continue
            if cap_y < 100:
                # caption 在顶部 → 图在上一图页
                prev_candidates = [p for p in sorted_fig_pages if p < cap_page]
                if prev_candidates:
                    chosen = max(prev_candidates)
                else:
                    chosen = min(sorted_fig_pages, key=lambda p: abs(p - cap_page))
            else:
                # caption 在底部 → 图在下一图页
                next_candidates = [p for p in sorted_fig_pages if p > cap_page]
                if next_candidates:
                    chosen = min(next_candidates)
                else:
                    chosen = min(sorted_fig_pages, key=lambda p: abs(p - cap_page))
            fig_to_image_page[fig_num] = (chosen, None)
    return fig_to_image_page


def get_drawing_extent(page):
    """Return (x_min, y_min, x_max, y_max) of all drawings on page, or None."""
    xs, ys = [], []
    for d in page.get_drawings():
        if "rect" in d:
            r = d["rect"]
            xs.extend([r[0], r[2]])
            ys.extend([r[1], r[3]])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def crop_figure(pdf_path, output_dir, fig_num, page_num, caption_top_y, dpi=200):
    """渲染整页 → 按坐标裁剪 → 保存 PNG。"""
    scale = dpi / 72.0
    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]
    page_w, page_h = page.rect.width, page.rect.height

    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    # 优先用 drawings extent；否则用页面默认边距
    extent = get_drawing_extent(page)
    if extent:
        x_min, y_min, x_max, y_max = extent
    else:
        x_min, y_min, x_max, y_max = (40, 38, page_w - 40, page_h - 38)

    left = max(28, x_min - 4)
    right = min(page_w - 28, x_max + 4)
    top = max(38, y_min - 2)
    if caption_top_y is not None:
        bottom = caption_top_y - 6
    else:
        bottom = min(page_h - 30, y_max + 4)

    crop_box = (int(left * scale), int(top * scale),
                int(right * scale), int(bottom * scale))
    cropped = img.crop(crop_box)

    out_name = f"Figure{fig_num}.png"
    out_path = os.path.join(output_dir, out_name)
    cropped.save(out_path, "PNG", optimize=True)
    print(f"  Saved Figure{fig_num}.png  page={page_num}  "
          f"bbox=({left:.0f},{top:.0f},{right:.0f},{bottom:.0f})  size={cropped.size}")
    doc.close()


def main():
    parser = argparse.ArgumentParser(description="Auto-extract figures from a PDF.")
    parser.add_argument("pdf_path")
    parser.add_argument("output_dir")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--min-drawings", type=int, default=100,
                        help="Min drawings count to consider a page as figure page.")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    doc = fitz.open(args.pdf_path)
    print(f"PDF: {args.pdf_path}")
    print(f"Total pages: {len(doc)}")

    figure_pages = detect_figure_pages(doc, args.min_drawings)
    print(f"\nFigure pages (drawings >= {args.min_drawings}):")
    for p, n in sorted(figure_pages.items()):
        print(f"  page {p}: {n} drawings")

    captions = scan_captions(doc)
    print(f"\nCaptions found: {len(captions)} unique figure numbers")
    for fig_num, occurrences in sorted(captions.items()):
        for page_num, cap_y in occurrences:
            print(f"  Fig {fig_num}: caption on page {page_num}, top y={cap_y:.0f}")

    mapping = match_figures_to_pages(figure_pages, captions)
    print(f"\nFigure → image page mapping:")
    for fig_num in sorted(mapping):
        page_num, cap_y = mapping[fig_num]
        print(f"  Fig {fig_num}: image on page {page_num}, caption_y_on_same_page={cap_y}")

    print(f"\nExtracting figures at {args.dpi} DPI:")
    for fig_num in sorted(mapping):
        page_num, cap_y = mapping[fig_num]
        crop_figure(args.pdf_path, args.output_dir, fig_num, page_num, cap_y, args.dpi)

    doc.close()
    print(f"\nDone. {len(mapping)} figures → {args.output_dir}")


if __name__ == "__main__":
    main()
