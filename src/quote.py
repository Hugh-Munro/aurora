"""
src/quote.py
------------
Extracts passages from PDFs and picks a random quote for the daily email.
Public entry point: pick_random_quote(folder, pattern, recursive, gap_multiplier) -> Quote

Design notes:
  - Paragraphs are detected by gap analysis between lines on each PDF page.
  - A JSON cache keyed on file path + mtime avoids re-parsing unchanged PDFs.
  - The cache file is written to the passages folder (gitignored via .gitignore).
"""
from __future__ import annotations

import json
import random
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber

# -- Cache --------------------------------------------------------------------
CACHE_FILENAME = ".passages_cache.json"

# -- Filename pattern ---------------------------------------------------------
# Matches:
#   Passages - Title - Author
#   Passages - Title
FILENAME_RE = re.compile(
    r"^\s*Passages\s*-\s*(?P<title>.+?)(?:\s*-\s*(?P<author>.+?))?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Quote:
    title:       str
    author:      Optional[str]
    text:        str
    source_path: Path


# -- Filename parsing ----------------------------------------------------------

def parse_title_author_from_filename(pdf_path: Path) -> Tuple[str, Optional[str]]:
    stem = pdf_path.stem
    m = FILENAME_RE.match(stem)
    if not m:
        return stem.strip(), None
    title  = (m.group("title")  or "").strip()
    author = (m.group("author") or "").strip() if m.group("author") else None
    return title, author


# -- Text extraction helpers ---------------------------------------------------

def _join_wrapped_lines(lines: List[str]) -> str:
    s = " ".join(line.strip() for line in lines if line.strip())
    return re.sub(r"\s+", " ", s).strip()


def _merge_cross_page(paragraphs: List[str]) -> List[str]:
    """Merge paragraphs split across pages.

    A paragraph is merged with the next if it does not end a sentence
    and the following paragraph begins with a lowercase letter.
    """
    merged: List[str] = []
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i].strip()
        while i + 1 < len(paragraphs):
            nxt = paragraphs[i + 1].strip()
            if not p or not nxt:
                break
            ends_sentence = re.search(r"[.!?][\'\"]?\s*$", p) is not None
            starts_lower  = nxt[0].islower()
            if (not ends_sentence) and starts_lower:
                p  = f"{p} {nxt}".strip()
                i += 1
            else:
                break
        if p:
            merged.append(p)
        i += 1
    return merged


def extract_quotes_from_pdf(pdf_path: Path, gap_multiplier: float = 1.8) -> List[str]:
    """Extract individual passages from a PDF using line-gap analysis."""
    paragraphs: List[str] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            lines = page.extract_text_lines(strip=True, return_chars=False) or []
            lines = [ln for ln in lines if (ln.get("text") or "").strip()]
            lines.sort(key=lambda d: (d.get("top", 0.0), d.get("x0", 0.0)))
            if not lines:
                continue

            gaps: List[float] = []
            for i in range(1, len(lines)):
                prev_bottom = float(lines[i - 1].get("bottom", 0.0))
                cur_top     = float(lines[i].get("top", 0.0))
                gaps.append(cur_top - prev_bottom)

            median_gap = statistics.median(gaps) if gaps else 0.0
            threshold  = max(median_gap * gap_multiplier, 2.5)

            buf: List[str] = [lines[0]["text"]]
            for i in range(1, len(lines)):
                prev_bottom = float(lines[i - 1].get("bottom", 0.0))
                cur_top     = float(lines[i].get("top", 0.0))
                gap         = cur_top - prev_bottom
                if gap > threshold:
                    paragraphs.append(_join_wrapped_lines(buf))
                    buf = [lines[i]["text"]]
                else:
                    buf.append(lines[i]["text"])
            if buf:
                paragraphs.append(_join_wrapped_lines(buf))

    # Drop any line that is just the PDF title header
    paragraphs = [
        p for p in paragraphs
        if p.strip() and not p.strip().lower().startswith("passages -")
    ]
    paragraphs = _merge_cross_page(paragraphs)
    return [p.strip() for p in paragraphs if p.strip()]


# -- Cache helpers -------------------------------------------------------------

def _load_cache(cache_path: Path) -> Dict[str, dict]:
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache_path: Path, cache: Dict[str, dict]) -> None:
    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# -- Public API ----------------------------------------------------------------

def load_all_quotes(
    folder:         Path,
    pattern:        str   = "Passages - *.pdf",
    recursive:      bool  = False,
    gap_multiplier: float = 1.8,
    use_cache:      bool  = True,
) -> List[Quote]:
    folder = folder.expanduser()
    pdfs   = sorted(folder.rglob(pattern) if recursive else folder.glob(pattern))
    if not pdfs:
        return []

    cache_path    = folder / CACHE_FILENAME
    cache         = _load_cache(cache_path) if use_cache else {}
    cache_changed = False
    quotes: List[Quote] = []

    for pdf_path in pdfs:
        key   = str(pdf_path.resolve())
        mtime = pdf_path.stat().st_mtime
        title, author = parse_title_author_from_filename(pdf_path)
        cached = cache.get(key)

        if (
            use_cache
            and cached
            and cached.get("mtime") == mtime
            and cached.get("gap_multiplier") == gap_multiplier
        ):
            paras = cached.get("paragraphs", [])
        else:
            paras = extract_quotes_from_pdf(pdf_path, gap_multiplier=gap_multiplier)
            if use_cache:
                cache[key] = {
                    "mtime":          mtime,
                    "gap_multiplier": gap_multiplier,
                    "title":          title,
                    "author":         author,
                    "paragraphs":     paras,
                }
                cache_changed = True

        for p in paras:
            quotes.append(Quote(title=title, author=author, text=p, source_path=pdf_path))

    if use_cache and cache_changed:
        _save_cache(cache_path, cache)

    return quotes


def pick_random_quote(
    folder:         Path,
    pattern:        str   = "Passages - *.pdf",
    recursive:      bool  = False,
    gap_multiplier: float = 1.8,
) -> Quote:
    quotes = load_all_quotes(
        folder,
        pattern=pattern,
        recursive=recursive,
        gap_multiplier=gap_multiplier,
        use_cache=True,
    )
    if not quotes:
        raise RuntimeError("No quotes found/extracted.")
    return random.choice(quotes)