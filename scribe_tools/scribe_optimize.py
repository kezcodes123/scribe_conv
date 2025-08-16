#!/usr/bin/env python3
"""
Kindle Scribe PDF optimizer.

- Attempts vector-preserving grayscale with Ghostscript when available.
- Otherwise falls back to a raster pipeline using PyMuPDF + Pillow.
- Auto-detects content bounding box per page and crops margins with a safe inset.
- Resizes to Scribe-friendly page size by default.

Usage:
    python -m scribe_tools.scribe_optimize /path/to/input.pdf [--out output.pdf]

This keeps all text and illustrations (no reflow); only format/size/contrast/cropping is adjusted.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Tuple, Any, Literal

# Optional imports for raster fallback
try:
    import fitz  # PyMuPDF
    from PIL import Image, ImageOps, ImageFilter
except Exception:  # pragma: no cover - will be installed via requirements
    fitz = None
    Image = None
    ImageOps = None
    ImageFilter = None


@dataclass
class PageSize:
    width_pt: int
    height_pt: int


SCRIBE = PageSize(446, 595)  # ~ 6.2" x 8.26" @ 72dpi
A5 = PageSize(420, 595)


def has_ghostscript() -> bool:
    return shutil.which("gs") is not None


def detect_bbox(img: Any, threshold: int = 250, pad: int = 10) -> Tuple[int, int, int, int]:
    """Detect a loose bounding box of non-white content.

    Converts to grayscale, then finds the bbox of pixels darker than threshold.
    Returns (left, top, right, bottom). Falls back to full image if nothing detected.
    """
    gray = img.convert("L")
    # Invert so content becomes bright, then getbbox on thresholded mask
    bw = gray.point(lambda p: 255 if p < threshold else 0, mode="L")
    bbox = bw.getbbox()
    if not bbox:
        return (0, 0, img.width, img.height)
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(img.width, r + pad)
    b = min(img.height, b + pad)
    return (l, t, r, b)


def gs_grayscale(in_pdf: str, out_pdf: str, quality: Literal["screen","ebook","printer","prepress","default"] = "prepress") -> None:
    """Use Ghostscript to convert PDF to devicegray while preserving vectors."""
    cmd = [
        "gs",
        "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dCompatibilityLevel=1.7",
        "-sDEVICE=pdfwrite",
        "-sColorConversionStrategy=Gray",
        "-dProcessColorModel=/DeviceGray",
        "-dConvertCMYKImagesToRGB=false",
        "-dDetectDuplicateImages=true",
    f"-dPDFSETTINGS=/{quality}",
        f"-sOutputFile={out_pdf}",
        in_pdf,
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ghostscript failed with code {e.returncode}") from e


def raster_pipeline(
    in_pdf: str,
    out_pdf: str,
    page_size: PageSize,
    margin_top_pt: int = 14,
    margin_right_pt: int = 14,
    margin_bottom_pt: int = 14,
    margin_left_pt: int = 14,
    dpi: int = 300,
    autocontrast: bool = True,
    autocontrast_cutoff: int = 1,
    crop: bool = True,
    crop_threshold: int = 245,
    crop_pad: int = 10,
    fit_mode: Literal["contain","fit_width","fit_height","stretch"] = "contain",
    sharpen: bool = False,
    bilevel: bool = False,
    dither: bool = True,
    rotate_landscape: bool = False,
) -> None:
    assert fitz is not None and Image is not None and ImageOps is not None, "Raster deps missing"

    doc = fitz.open(in_pdf)
    images = []

    # Low-res pass for bbox detection to speed up
    low_zoom = max(1.0, dpi / 150)  # heuristic for bbox detection
    for page in doc:
        mat = fitz.Matrix(low_zoom, low_zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        gray = ImageOps.grayscale(img)
        if autocontrast:
            gray = ImageOps.autocontrast(gray, cutoff=autocontrast_cutoff)
        if crop:
            bbox = detect_bbox(gray, threshold=crop_threshold, pad=crop_pad)
        else:
            bbox = (0, 0, gray.width, gray.height)

        # High-res render of the page for final output
        mat2 = fitz.Matrix(dpi / 72, dpi / 72)
        pix2 = page.get_pixmap(matrix=mat2, alpha=False)
        img2 = Image.frombytes("RGB", [pix2.width, pix2.height], pix2.samples)
        gray2 = ImageOps.grayscale(img2)
        if autocontrast:
            gray2 = ImageOps.autocontrast(gray2, cutoff=autocontrast_cutoff)

        if crop:
            page_img = gray2.crop(bbox)
        else:
            page_img = gray2
        if sharpen and ImageFilter is not None:
            try:
                page_img = page_img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=3))
            except Exception:
                pass

        images.append(page_img)

    # Ensure doc is closed before heavy composition
    doc.close()

    # Compose onto final page size
    target_w = int(page_size.width_pt / 72 * dpi)
    target_h = int(page_size.height_pt / 72 * dpi)

    composed = []
    for img in images:
        # Scale to fit within target size preserving aspect; add margins
        ml_px = int(margin_left_pt / 72 * dpi)
        mr_px = int(margin_right_pt / 72 * dpi)
        mt_px = int(margin_top_pt / 72 * dpi)
        mb_px = int(margin_bottom_pt / 72 * dpi)
        avail_w = max(1, target_w - (ml_px + mr_px))
        avail_h = max(1, target_h - (mt_px + mb_px))

        # Pillow >= 9 has Image.Resampling; older uses Image.ANTIALIAS/BICUBIC
        try:
            lanczos = Image.Resampling.LANCZOS
            bicubic = Image.Resampling.BICUBIC
        except Exception:
            lanczos = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', Image.BICUBIC))
            bicubic = getattr(Image, 'BICUBIC', Image.NEAREST)

        if fit_mode == "contain":
            img = ImageOps.contain(img, (avail_w, avail_h), method=lanczos)
        elif fit_mode == "fit_width":
            new_h = max(1, int(img.height * (avail_w / img.width)))
            img = img.resize((avail_w, new_h), resample=lanczos)
            if new_h > avail_h:
                img = img.crop((0, 0, img.width, avail_h))
        elif fit_mode == "fit_height":
            new_w = max(1, int(img.width * (avail_h / img.height)))
            img = img.resize((new_w, avail_h), resample=lanczos)
            if new_w > avail_w:
                img = img.crop((0, 0, avail_w, img.height))
        else:  # stretch
            img = img.resize((avail_w, avail_h), resample=bicubic)

        if rotate_landscape and target_h >= target_w and img.width > img.height:
            img = img.rotate(90, expand=True)

        mode = "1" if bilevel else "L"
        bg = 1 if bilevel else 255
        canvas = Image.new(mode, (target_w, target_h), color=bg)
        # Center within margins
        x = ml_px + max(0, (avail_w - img.width) // 2)
        y = mt_px + max(0, (avail_h - img.height) // 2)
        if bilevel:
            img2 = img.convert("1", dither=Image.FLOYDSTEINBERG if dither else Image.NONE)
        else:
            img2 = img
        canvas.paste(img2, (x, y))
        composed.append(canvas)

    # Save a grayscale PDF
    try:
        composed[0].save(
            out_pdf,
            save_all=True,
            append_images=composed[1:],
            resolution=dpi,
        )
    except Exception:
        # Some PDF writers dislike mixed '1' mode pages; convert to 'L' and retry
        composedL = [p.convert('L') if getattr(p, 'mode', 'L') == '1' else p for p in composed]
        composedL[0].save(
            out_pdf,
            save_all=True,
            append_images=composedL[1:],
            resolution=dpi,
        )


def optimize_pdf(
    in_pdf: str,
    out_pdf: str,
    page_size: str = "scribe",
    margin_pt: int = 14,
    margin_top_pt: Optional[int] = None,
    margin_right_pt: Optional[int] = None,
    margin_bottom_pt: Optional[int] = None,
    margin_left_pt: Optional[int] = None,
    custom_width_pt: Optional[int] = None,
    custom_height_pt: Optional[int] = None,
    dpi: int = 300,
    autocontrast: bool = True,
    autocontrast_cutoff: int = 1,
    crop: bool = True,
    crop_threshold: int = 245,
    crop_pad: int = 10,
    fit_mode: Literal["contain","fit_width","fit_height","stretch"] = "contain",
    sharpen: bool = False,
    bilevel: bool = False,
    dither: bool = True,
    rotate_landscape: bool = False,
    gs_quality: Literal["screen","ebook","printer","prepress","default"] = "prepress",
    force_gs: bool = False,
    force_raster: bool = False,
) -> None:
    size = SCRIBE if page_size == "scribe" else A5 if page_size == "a5" else None
    if page_size == "custom" and custom_width_pt and custom_height_pt:
        size = PageSize(custom_width_pt, custom_height_pt)

    # Resolve margins
    mt = margin_top_pt if margin_top_pt is not None else margin_pt
    mr = margin_right_pt if margin_right_pt is not None else margin_pt
    mb = margin_bottom_pt if margin_bottom_pt is not None else margin_pt
    ml = margin_left_pt if margin_left_pt is not None else margin_pt

    if has_ghostscript() and not force_raster:
        tmp_gray = out_pdf.replace(".pdf", ".gray.tmp.pdf")
        gs_grayscale(in_pdf, tmp_gray, quality=gs_quality)
        if size is None and (not crop):
            # Keep original size exactly, no crop, just grayscale
            os.replace(tmp_gray, out_pdf)
            return
        if size is None and margin_pt == 0 and crop is False:
            # redundant guard
            os.replace(tmp_gray, out_pdf)
            return
        if size is None and margin_pt == 0 and crop is True:
            # crop-only while keeping original size requires raster pipeline
            pass
        if size is None and margin_pt == 0 and crop is False:
            # Already handled above
            os.replace(tmp_gray, out_pdf)
            return
        # If we need to crop/resize, run raster pipeline using grayscale as input
        if fitz is None:
            # Fallback: just output grayscale if PyMuPDF not available
            os.replace(tmp_gray, out_pdf)
            return
        # If source sizing requested, detect original page size from the grayscale doc
        target_size = size
        if target_size is None:
            try:
                gdoc = fitz.open(tmp_gray)
                rect = gdoc[0].rect
                target_size = PageSize(int(rect.width), int(rect.height))
            except Exception:
                # On failure, keep original by reading from input
                try:
                    odoc = fitz.open(in_pdf)
                    rect = odoc[0].rect
                    target_size = PageSize(int(rect.width), int(rect.height))
                except Exception:
                    target_size = SCRIBE  # last resort
        raster_pipeline(
            tmp_gray, out_pdf, target_size,
            mt, mr, mb, ml,
            dpi,
            autocontrast,
            autocontrast_cutoff,
            crop,
            crop_threshold,
            crop_pad,
            fit_mode,
            sharpen,
            bilevel,
            dither,
            rotate_landscape,
        )
        os.remove(tmp_gray)
    else:
        # No Ghostscript; rasterize original directly
        if size is None:
            # keep source size: we need to read the page size from first page
            if fitz is None:
                raise RuntimeError("PyMuPDF required when Ghostscript is missing")
            doc = fitz.open(in_pdf)
            rect = doc[0].rect
            size = PageSize(int(rect.width), int(rect.height))
        raster_pipeline(
            in_pdf, out_pdf, size,
            mt, mr, mb, ml,
            dpi,
            autocontrast,
            autocontrast_cutoff,
            crop,
            crop_threshold,
            crop_pad,
            fit_mode,
            sharpen,
            bilevel,
            dither,
            rotate_landscape,
        )


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Optimize a PDF for Kindle Scribe readability")
    parser.add_argument("input", help="Path to input PDF")
    parser.add_argument("--out", dest="out", help="Output PDF path (default: _scribe.pdf next to input)")
    parser.add_argument("--page-size", choices=["scribe", "a5", "source", "custom"], default="scribe")
    parser.add_argument("--margin-pt", type=int, default=14)
    parser.add_argument("--margin-top-pt", type=int)
    parser.add_argument("--margin-right-pt", type=int)
    parser.add_argument("--margin-bottom-pt", type=int)
    parser.add_argument("--margin-left-pt", type=int)
    parser.add_argument("--custom-width-pt", type=int)
    parser.add_argument("--custom-height-pt", type=int)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--no-autocontrast", action="store_true")
    parser.add_argument("--autocontrast-cutoff", type=int, default=1)
    parser.add_argument("--no-crop", action="store_true", help="Disable margin cropping; keep full page content")
    parser.add_argument("--crop-threshold", type=int, default=245)
    parser.add_argument("--crop-pad", type=int, default=10)
    parser.add_argument("--fit", choices=["contain","fit_width","fit_height","stretch"], default="contain")
    parser.add_argument("--sharpen", action="store_true")
    parser.add_argument("--bilevel", action="store_true")
    parser.add_argument("--no-dither", action="store_true")
    parser.add_argument("--rotate-landscape", action="store_true")
    parser.add_argument("--gs-quality", choices=["screen","ebook","printer","prepress","default"], default="prepress")
    parser.add_argument("--force-gs", action="store_true")
    parser.add_argument("--force-raster", action="store_true")

    args = parser.parse_args(argv)

    in_pdf = os.path.abspath(args.input)
    if not os.path.exists(in_pdf):
        print(f"Input not found: {in_pdf}", file=sys.stderr)
        sys.exit(1)

    out_pdf = args.out
    if not out_pdf:
        base, ext = os.path.splitext(in_pdf)
        out_pdf = base + "_scribe.pdf"
    out_pdf = os.path.abspath(out_pdf)

    optimize_pdf(
        in_pdf,
        out_pdf,
        page_size=args.page_size,
        margin_pt=args.margin_pt,
        margin_top_pt=args.margin_top_pt,
        margin_right_pt=args.margin_right_pt,
        margin_bottom_pt=args.margin_bottom_pt,
        margin_left_pt=args.margin_left_pt,
        custom_width_pt=args.custom_width_pt,
        custom_height_pt=args.custom_height_pt,
        dpi=args.dpi,
        autocontrast=not args.no_autocontrast,
        autocontrast_cutoff=args.autocontrast_cutoff,
        crop=not args.no_crop,
        crop_threshold=args.crop_threshold,
        crop_pad=args.crop_pad,
        fit_mode=args.fit,
        sharpen=args.sharpen,
        bilevel=args.bilevel,
        dither=not args.no_dither,
        rotate_landscape=args.rotate_landscape,
        gs_quality=args.gs_quality,
        force_gs=args.force_gs,
        force_raster=args.force_raster,
    )
    print(f"Wrote {out_pdf}")


if __name__ == "__main__":
    main()
