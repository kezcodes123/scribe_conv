#!/usr/bin/env python3
from __future__ import annotations

import io
import os
import re
from typing import List, Tuple

import fitz  # PyMuPDF
from ebooklib import epub
from PIL import Image


def _extract_page_text_and_sizes(page: fitz.Page) -> List[Tuple[str, float]]:
    """Return list of (paragraph_text, approx_font_size) per block in reading order."""
    data = page.get_text("dict")
    result: List[Tuple[str, float]] = []
    for block in data.get("blocks", []):
        # Only process text blocks (some dicts include 'type': 0 for text)
        if block.get("type", 0) != 0:
            continue
        parts: List[str] = []
        sizes: List[float] = []
        for line in block.get("lines", []):
            line_parts: List[str] = []
            for span in line.get("spans", []):
                t = span.get("text", "").strip()
                if not t:
                    continue
                line_parts.append(t)
                try:
                    sizes.append(float(span.get("size", 12)))
                except Exception:
                    pass
            if line_parts:
                parts.append(" ".join(line_parts))
        para = " ".join(parts).strip()
        if not para:
            continue
        size = _guess_body_size(sizes) if sizes else 12.0
        result.append((para, size))
    return result


def _guess_body_size(sizes: List[float]) -> float:
    sizes = [s for s in sizes if s >= 6]
    if not sizes:
        return 12.0
    sizes.sort()
    mid = len(sizes) // 2
    return sizes[mid]


def _sanitize_html(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace('"', "&quot;").replace("'", "&apos;")
    return s


def _page_to_html(page: fitz.Page, max_img_px: int = 1600, bilevel: bool = False, dither: bool = True) -> Tuple[str, List[Tuple[str, bytes, str]]]:
    """Create HTML for a page and return (html, images) where images is list of (id, data, media_type).

    Images are converted to JPEG and downscaled preserving aspect ratio so long edge <= max_img_px for Kindle compatibility.
    """
    spans = _extract_page_text_and_sizes(page)
    sizes = [sz for _, sz in spans]
    body_size = _guess_body_size(sizes)
    # simple heuristic: spans >= body_size*1.25 are headings
    html_lines = []
    last_was_heading = False
    for text, sz in spans:
        safe = _sanitize_html(text)
        if sz >= body_size * 1.3 and len(safe) <= 140:
            # Slightly higher threshold to avoid over-heading
            level_tag = "h2" if not last_was_heading else "h3"
            html_lines.append(f"<{level_tag}>{safe}</{level_tag}>")
            last_was_heading = True
        else:
            html_lines.append(f"<p>{safe}</p>")
            last_was_heading = False

    # images
    images: List[Tuple[str, bytes, str]] = []
    for i, img in enumerate(page.get_images(full=True)):
        xref = img[0]
        try:
            pix = fitz.Pixmap(page.parent, xref)
            if pix.n > 4:  # CMYK or other
                pix = fitz.Pixmap(fitz.csRGB, pix)
            # Convert to PIL Image and force grayscale
            mode = "RGB" if pix.n in (3, 4) else "L"
            pil = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            pil = pil.convert("L")  # grayscale baseline
            # Downscale to max_img_px on long edge
            w, h = pil.size
            scale = min(1.0, float(max_img_px) / float(max(w, h)))
            if scale < 1.0:
                new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                pil = pil.resize(new_size, Image.LANCZOS)
            # Optional bilevel with dithering; save as L for JPEG compatibility
            if bilevel:
                try:
                    pil_bw = pil.convert("1", dither=Image.FLOYDSTEINBERG if dither else Image.NONE)
                    pil = pil_bw.convert("L")
                except Exception:
                    pass
            bio = io.BytesIO()
            pil.save(bio, format="JPEG", quality=80, optimize=True, progressive=True)
            img_bytes = bio.getvalue()
            img_id = f"img_{page.number+1}_{i}"
            images.append((img_id, img_bytes, "image/jpeg"))
            html_lines.append(f'<figure><img src="images/{img_id}.jpg" alt="Figure {i+1}"></figure>')
        except Exception:
            continue

    html = "\n".join(html_lines) if html_lines else "<p></p>"
    return html, images


def pdf_to_epub(in_pdf: str, out_epub: str, title: str | None = None, author: str | None = None, *, epub_bilevel: bool = False, epub_dither: bool = True) -> None:
    doc = fitz.open(in_pdf)

    book = epub.EpubBook()
    book.set_identifier(os.path.basename(in_pdf))
    book.set_title(title or os.path.splitext(os.path.basename(in_pdf))[0])
    book.set_language("en")
    if author:
        book.add_author(author)

    chapters = []
    toc = []

    # Optional: create a cover from the first page render for better Send-to-Kindle compatibility
    try:
        if len(doc) > 0:
            page0 = doc.load_page(0)
            # Render first page to a decent JPEG cover
            target_w = 1600
            zoom = max(1.0, target_w / float(page0.rect.width))
            mat = fitz.Matrix(zoom, zoom)
            p0 = page0.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (p0.width, p0.height), p0.samples).convert("L")
            if epub_bilevel:
                try:
                    img_bw = img.convert("1", dither=Image.FLOYDSTEINBERG if epub_dither else Image.NONE)
                    img = img_bw.convert("L")
                except Exception:
                    pass
            bio = io.BytesIO()
            img.save(bio, format="JPEG", quality=80, optimize=True, progressive=True)
            book.set_cover("cover.jpg", bio.getvalue())
    except Exception:
        pass

    # Iterate pages and build chapters
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        html, images = _page_to_html(page, bilevel=epub_bilevel, dither=epub_dither)

        # add images as items (ensure extension matches media type)
        img_items = []
        for img_id, data, media_type in images:
            ext = "jpg" if media_type == "image/jpeg" else "png"
            item = epub.EpubItem(uid=img_id, file_name=f"images/{img_id}.{ext}", media_type=media_type, content=data)
            book.add_item(item)
            img_items.append(item)

        # Fallback: if there is no text and no images, render the whole page as an image
        if (not html or html.strip() == "<p></p>") and not img_items:
            try:
                target_w = 1600
                zoom = max(1.0, target_w / float(page.rect.width))
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                pil = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
                if epub_bilevel:
                    try:
                        pil_bw = pil.convert("1", dither=Image.FLOYDSTEINBERG if epub_dither else Image.NONE)
                        pil = pil_bw.convert("L")
                    except Exception:
                        pass
                bio = io.BytesIO()
                pil.save(bio, format="JPEG", quality=80, optimize=True, progressive=True)
                data = bio.getvalue()
                img_id = f"page_{page_index+1}"
                item = epub.EpubItem(uid=img_id, file_name=f"images/{img_id}.jpg", media_type="image/jpeg", content=data)
                book.add_item(item)
                html = f'<figure><img src="images/{img_id}.jpg" alt="Page {page_index+1}"></figure>'
            except Exception:
                pass

        chap = epub.EpubHtml(title=f"Page {page_index+1}", file_name=f"chap_{page_index+1}.xhtml", lang="en")
        chap.content = f"""
        <html xmlns="http://www.w3.org/1999/xhtml">
            <head>
                <title>Page {page_index+1}</title>
                <meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />
                <link rel=\"stylesheet\" type=\"text/css\" href=\"style/nav.css\" />
            </head>
            <body>
                {html}
            </body>
        </html>
        """
        book.add_item(chap)
        chapters.append(chap)
        toc.append(chap)

    # spine and TOC
    book.toc = toc
    book.spine = ['nav'] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # CSS for readability on e-ink
    style = """
    html, body { margin: 0; padding: 0; }
    body { font-family: serif; line-height: 1.25; }
    h2, h3 { page-break-after: avoid; margin: 0.35em 0 0.2em; }
    p { margin: 0.2em 0; }
    img { width: 100%; height: auto; display: block; margin: 0; }
    figure { margin: 0; text-align: center; }
    """
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    try:
        epub.write_epub(out_epub, book)
    finally:
        try:
            doc.close()
        except Exception:
            pass
