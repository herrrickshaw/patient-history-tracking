"""OCR-assisted digitization of a photographed/scanned doctor's
prescription, using local Tesseract (no cloud OCR service, no API key).

OCR on handwritten prescriptions is unreliable -- misreads on drug
names and doses are exactly the kind of error that matters most here.
Nothing this module extracts is trusted automatically: every parsed
line becomes a *pending* candidate that a human must review and
approve (see main.py's pending-queue endpoints) before it becomes an
active order. This mirrors how real prescription-digitization tools
are built -- OCR assists data entry, it doesn't replace clinical
verification.
"""
from __future__ import annotations

import io
import re

import pytesseract
from PIL import Image

DISCLAIMER = (
    "OCR-assisted digitization using local Tesseract. Handwriting recognition "
    "is unreliable -- every extracted line is a candidate only, requiring "
    "human review and approval before it becomes an active order. Never "
    "auto-trust OCR output for medication dosing."
)

# Frequency abbreviation -> illustrative demo administration cadence, in
# sim-seconds (same compressed-schedule convention as prescriptions.py).
# STAT (once, immediately) and PRN (as-needed) have no repeat cadence.
FREQUENCY_MAP = {
    "OD": 120, "QD": 120,
    "BD": 90, "BID": 90,
    "TDS": 60, "TID": 60,
    "QID": 45, "QDS": 45,
    "HS": 150,
    "STAT": None,
    "PRN": None,
    "SOS": None,
}
FREQUENCY_PATTERN = re.compile(r"\b(" + "|".join(FREQUENCY_MAP) + r")\b", re.IGNORECASE)
ROUTE_PATTERN = re.compile(r"\b(PO|IV|IM|SC|SL|PR|IV infusion)\b", re.IGNORECASE)
DOSE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|iu|units?))\b", re.IGNORECASE)


def extract_text(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)


def parse_candidates(raw_text: str) -> list[dict]:
    candidates = []
    for line in raw_text.splitlines():
        line = line.strip()
        if len(line) < 3:
            continue

        dose_match = DOSE_PATTERN.search(line)
        freq_match = FREQUENCY_PATTERN.search(line)
        route_match = ROUTE_PATTERN.search(line)

        remainder = line
        for m in (dose_match, freq_match, route_match):
            if m:
                remainder = remainder.replace(m.group(0), "")
        drug = re.sub(r"[,\-–;:]+$", "", remainder).strip(" ,-–;:") or line

        freq_abbrev = freq_match.group(0).upper() if freq_match else None
        candidates.append(
            {
                "raw_line": line,
                "drug": drug,
                "dose": dose_match.group(0).strip() if dose_match else None,
                "route": route_match.group(0).upper() if route_match else None,
                "frequency_abbrev": freq_abbrev,
                "frequency_sim_sec": FREQUENCY_MAP.get(freq_abbrev) if freq_abbrev else None,
            }
        )
    return candidates
