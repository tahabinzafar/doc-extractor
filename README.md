# doc-extractor

Pulls text out of scanned documents. Feed it an image or a PDF, get back a JSON file with every line it found.

Runs on RapidOCR (the PaddleOCR models on ONNX Runtime), so it works offline after the first run and there's no painful install.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The OCR models download once on the first run (a few MB) and cache locally after that.

## Use

```bash
python extract.py invoice.pdf            # single file
python extract.py scans/                 # a whole folder
python extract.py statement.png -o out   # choose the output folder
python extract.py invoice.pdf --dpi 300  # bump resolution if the text is small
```

Results land in `output/`, one JSON file per input. Handles png, jpg, tiff, bmp, webp, and pdf.

## Output

```json
{
  "source": "invoice.pdf",
  "page_count": 1,
  "pages": [
    {
      "page": 1,
      "full_text": "ACME LTD\nInvoice 00123\nTotal Due 1,240.00",
      "lines": [
        {
          "text": "Total Due 1,240.00",
          "confidence": 0.987,
          "box": [[412, 880], [690, 880], [690, 905], [412, 905]]
        }
      ]
    }
  ]
}
```

Use `full_text` if you just want the words. The `lines` array keeps each line's confidence and its box (four corners), which is what you'll reach for once you start pulling specific fields out by position.
