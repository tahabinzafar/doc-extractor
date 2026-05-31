# ocr-extractor

A tiny OCR tool. Point it at an image or a PDF, get back a JSON file with
every line of detected text. That's the whole job for now. Field extraction
(turning "Total Due 1,240.00" into `{"total_due": 1240.00}`) comes later, on
top of this output.

Built on [RapidOCR](https://github.com/RapidAI/RapidOCR), which runs the
PaddleOCR models on ONNX Runtime. One pip install, no `paddlepaddle`, fully
offline after the first run, and strong on printed financial text.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

First run downloads the OCR models (a few MB) and caches them in your home
folder, so it only happens once.

## Use

```bash
python extract.py invoice.pdf              # one PDF
python extract.py statement.png            # one image
python extract.py scans/                   # a whole folder
python extract.py invoice.pdf -o results   # custom output folder
python extract.py invoice.pdf --dpi 300    # sharper PDF render for small text
```

JSON lands in `output/` (or whatever `-o` you pass), one file per input,
named after the source.

Supported inputs: png, jpg, jpeg, tif, tiff, bmp, webp, pdf.

## Output shape

```json
{
  "source": "invoice.pdf",
  "page_count": 1,
  "pages": [
    {
      "page": 1,
      "full_text": "ACME LTD\nInvoice 00123\nTotal Due 1,240.00\n...",
      "lines": [
        {
          "text": "Total Due 1,240.00",
          "confidence": 0.987,
          "box": [[412.0, 880.0], [690.0, 880.0], [690.0, 905.0], [412.0, 905.0]]
        }
      ]
    }
  ]
}
```

Two ways to read it. `full_text` is the quick path if you just want all the
text. `lines` is the useful one for later: each line keeps its confidence and
its `box` (four corner points, clockwise from top-left), which is what you'll
use to group things into fields, columns, and tables.

## What's next

When you're ready to pull structured fields, we build on `lines`, not on raw
text. The boxes let us reason about position, so "the number to the right of
the label that says Total" becomes something we can actually code. Send me a
sample account and tell me which fields you want, and we'll start there.

## Swapping the engine

OCR lives in two functions, `load_engine()` and `run_ocr()`. If you ever want
to A/B against Tesseract or full PaddleOCR with table structure, those are the
only spots that change. Everything else stays the same.
