#!/usr/bin/env python3
"""Simple OCR extractor.

Takes an image or a PDF (or a folder of them) and dumps every line of
detected text to JSON. No field logic yet, just clean raw output you can
process later.

Usage:
    python src/extract.py data/raw/ -o data/json
    python src/extract.py data/raw/statement.png -o data/json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
PDF_EXTS = {".pdf"}


def load_engine():
    """Load RapidOCR. Works across the v1 and v3 package names."""
    try:
        from rapidocr import RapidOCR          # rapidocr 2.x / 3.x
    except ImportError:
        from rapidocr_onnxruntime import RapidOCR  # rapidocr 1.x fallback
    return RapidOCR()


def run_ocr(engine, image):
    """Run OCR on a file path or a numpy image and normalise the output.

    Returns a list of {text, confidence, box} dicts. Handles both the
    newer result-object API and the older (items, elapse) tuple API.
    """
    out = engine(image)
    lines = []

    # Newer API: result object with .txts / .boxes / .scores
    if hasattr(out, "txts") and out.txts is not None:
        boxes = out.boxes if out.boxes is not None else [None] * len(out.txts)
        scores = out.scores if out.scores is not None else [None] * len(out.txts)
        for box, text, score in zip(boxes, out.txts, scores):
            lines.append(_line(text, score, box))
        return lines

    # Older API: (items, elapse) tuple, items = [[box, text, score], ...]
    items = out[0] if isinstance(out, tuple) else out
    if not items:
        return lines
    for item in items:
        box, text, score = item[0], item[1], item[2]
        lines.append(_line(text, score, box))
    return lines


def _line(text, score, box):
    return {
        "text": str(text),
        "confidence": round(float(score), 4) if score is not None else None,
        "box": _box_to_list(box),
    }


def _box_to_list(box):
    """Normalise a bounding box to [[x, y], ...] floats."""
    if box is None:
        return None
    arr = np.array(box, dtype=float).reshape(-1, 2)
    return [[round(float(x), 1), round(float(y), 1)] for x, y in arr]


def pdf_to_images(path, dpi=200):
    """Render each PDF page to a BGR numpy image."""
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    images = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:        # RGBA -> RGB
            img = img[:, :, :3]
        elif pix.n == 1:      # grayscale -> 3 channels
            img = np.repeat(img, 3, axis=2)
        # PyMuPDF gives RGB, OpenCV-based OCR expects BGR
        img = np.ascontiguousarray(img[:, :, ::-1])
        images.append(img)
    doc.close()
    return images


def process_file(engine, path, dpi=200):
    ext = path.suffix.lower()
    pages = []

    if ext in PDF_EXTS:
        for i, img in enumerate(pdf_to_images(path, dpi=dpi), start=1):
            pages.append(_page(i, run_ocr(engine, img)))
    elif ext in IMAGE_EXTS:
        pages.append(_page(1, run_ocr(engine, str(path))))
    else:
        raise ValueError(f"unsupported file type: {ext}")

    return {
        "source": path.name,
        "page_count": len(pages),
        "pages": pages,
    }


def _page(number, lines):
    return {
        "page": number,
        "full_text": "\n".join(line["text"] for line in lines),
        "lines": lines,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Dump all OCR text from images / PDFs to JSON."
    )
    parser.add_argument("input", help="An image, a PDF, or a folder of them.")
    parser.add_argument("-o", "--out", default="data/json", help="Output folder (default: data/json).")
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI for PDFs (default: 200).")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if in_path.is_dir():
        targets = sorted(
            p for p in in_path.iterdir() if p.suffix.lower() in IMAGE_EXTS | PDF_EXTS
        )
    elif in_path.is_file():
        targets = [in_path]
    else:
        print(f"Not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    if not targets:
        print("No supported files found.", file=sys.stderr)
        sys.exit(1)

    print("Loading OCR engine (first run downloads the models, a few MB)...")
    engine = load_engine()

    for path in targets:
        print(f"Processing {path.name} ...")
        try:
            result = process_file(engine, path, dpi=args.dpi)
        except Exception as exc:
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        out_file = out_dir / f"{path.stem}.json"
        out_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        n_lines = sum(len(p["lines"]) for p in result["pages"])
        print(f"  -> {out_file}  ({result['page_count']} page(s), {n_lines} lines)")


if __name__ == "__main__":
    main()
