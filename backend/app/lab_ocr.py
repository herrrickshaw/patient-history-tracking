"""OCR-assisted digitization of a photographed/scanned lab report,
using local Tesseract (no cloud OCR service, no API key).

Same discipline as prescription_ocr.py, for the same reason: OCR
misreads on a lab value are exactly the kind of error that matters
most here. Every parsed line becomes a *pending* candidate that a
human must review and approve (see main.py's pending-queue endpoints)
before it's recorded as a lab result. This assists data entry, it
does not replace verification against the actual report.
"""
from __future__ import annotations

import io
import re

import pytesseract
from PIL import Image

DISCLAIMER = (
    "OCR-assisted digitization using local Tesseract. Every extracted line is "
    "a candidate only, requiring human review and approval before it's "
    "recorded as a lab result. Never auto-trust OCR output for lab values."
)

# Recognized analyte names -- lines that don't mention one of these are
# skipped, so report headers/footers/patient details don't become
# spurious "results". Not an exhaustive lab ontology, just enough
# common tests to demonstrate the flow.
KNOWN_TESTS = [
    "Hemoglobin", "Haemoglobin", "Hb", "WBC", "White Blood Cell", "RBC",
    "Red Blood Cell", "Platelet Count", "Platelets", "Hematocrit", "Haematocrit", "HCT",
    "Creatinine", "Sodium", "Potassium", "Glucose", "Urea", "BUN",
    "ALT", "AST", "Bilirubin", "Cholesterol", "HDL", "LDL", "Triglycerides",
    "TSH", "CRP", "ESR",
]
_TEST_PATTERN = re.compile(r"\b(" + "|".join(re.escape(t) for t in KNOWN_TESTS) + r")\b", re.IGNORECASE)

VALUE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(g/dL|mg/dL|mmol/L|mEq/L|IU/L|U/L|%|x10\^?9/L|/µL|K/µL)?",
    re.IGNORECASE,
)
RANGE_PATTERN = re.compile(r"\(\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*\)")
FLAG_TEXT_PATTERN = re.compile(r"\b(HIGH|LOW|NORMAL|ABNORMAL|CRITICAL)\b", re.IGNORECASE)


def extract_text(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)


def parse_candidates(raw_text: str) -> list[dict]:
    candidates = []
    for line in raw_text.splitlines():
        line = line.strip()
        if len(line) < 3:
            continue

        test_match = _TEST_PATTERN.search(line)
        if not test_match:
            continue  # not a recognized analyte -- likely header/footer noise

        after_test = line[test_match.end():]
        value_match = VALUE_PATTERN.search(after_test)
        range_match = RANGE_PATTERN.search(line)
        flag_text_match = FLAG_TEXT_PATTERN.search(line)

        value = value_match.group(1) if value_match else None
        flag = None
        if value is not None and range_match:
            lo, hi = float(range_match.group(1)), float(range_match.group(2))
            v = float(value)
            flag = "low" if v < lo else "high" if v > hi else "normal"
        elif flag_text_match:
            flag = flag_text_match.group(0).lower()

        candidates.append(
            {
                "raw_line": line,
                "test": test_match.group(0),
                "value": value,
                "unit": value_match.group(2) if value_match and value_match.group(2) else None,
                "reference_range": f"{range_match.group(1)}-{range_match.group(2)}" if range_match else None,
                "flag": flag,
            }
        )
    return candidates
