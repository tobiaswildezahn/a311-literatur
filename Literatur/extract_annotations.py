#!/usr/bin/env python3
"""
Extrahiert PDF-Annotationen (Highlights, Kommentare) aus PDF Expert u.a.

Gibt ein Dict zurueck:
  {
    "highlights": [{"page": 3, "text": "...", "comment": "..."}],
    "notes": [{"page": 5, "text": "Kommentartext"}],
    "notizen_summary": "Kompakte Zusammenfassung fuer Frontmatter"
  }

Nutzung:
    from extract_annotations import extract_annotations
    result = extract_annotations("path/to/annotated.pdf")
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf"]
# ///

import sys
import json

import fitz  # PyMuPDF


# Annotation type codes
HIGHLIGHT = 8
UNDERLINE = 9
SQUIGGLY = 10
STRIKEOUT = 11
TEXT_NOTE = 0
FREE_TEXT = 2


def extract_highlighted_text(page, annot):
    """Extrahiere den markierten Text unter einer Highlight-Annotation."""
    quads = annot.vertices
    if not quads:
        # Fallback: Rect-basierte Extraktion
        words = page.get_text("words")
        rect = annot.rect
        return " ".join(
            w[4] for w in words if fitz.Rect(w[:4]).intersects(rect)
        ).strip()

    # Quad-basierte Extraktion (praeziser)
    text_parts = []
    for i in range(0, len(quads), 4):
        quad = fitz.Quad(quads[i : i + 4])
        text_parts.append(page.get_textbox(quad.rect).strip())
    return " ".join(text_parts).strip()


def extract_annotations(pdf_path: str) -> dict:
    """Extrahiere alle relevanten Annotationen aus einer PDF."""
    doc = fitz.open(pdf_path)
    highlights = []
    notes = []

    for page in doc:
        for annot in page.annots():
            atype = annot.type[0]
            comment = (annot.info.get("content") or "").strip()

            if atype in (HIGHLIGHT, UNDERLINE, SQUIGGLY):
                text = extract_highlighted_text(page, annot)
                if text:
                    highlights.append({
                        "page": page.number + 1,
                        "text": text,
                        "comment": comment,
                    })

            elif atype == STRIKEOUT:
                # Durchgestrichener Text = "nicht relevant" Signal, ignorieren
                pass

            elif atype in (TEXT_NOTE, FREE_TEXT):
                if comment:
                    notes.append({
                        "page": page.number + 1,
                        "text": comment,
                    })

    doc.close()

    # Kompakte Zusammenfassung fuer das Frontmatter-Feld 'notizen'
    notizen_parts = []
    for h in highlights:
        entry = f"S.{h['page']}: \"{h['text'][:80]}\""
        if h["comment"]:
            entry += f" — {h['comment']}"
        notizen_parts.append(entry)
    for n in notes:
        notizen_parts.append(f"S.{n['page']}: {n['text']}")

    return {
        "highlights": highlights,
        "notes": notes,
        "notizen_summary": "; ".join(notizen_parts) if notizen_parts else "",
        "count": len(highlights) + len(notes),
    }


def _normalize(text: str) -> str:
    """Normalisiere Text fuer robustes Matching: Whitespace, Ligaturen, Sonderzeichen."""
    import re as _re
    import unicodedata
    # Unicode-Normalisierung (Ligaturen aufloesen)
    text = unicodedata.normalize("NFKD", text)
    # Typografische Anfuehrungszeichen → einfache
    for ch in "\u201c\u201d\u201e\u201f\u00ab\u00bb":
        text = text.replace(ch, '"')
    for ch in "\u2018\u2019\u201a\u201b":
        text = text.replace(ch, "'")
    # Bindestriche normalisieren (Halbgeviert, Geviert, bedingter Trennstrich)
    for ch in "\u2013\u2014\u2010\u2011\u00ad\u2012":
        text = text.replace(ch, "-")
    # Geschuetzte Leerzeichen
    for ch in "\u00a0\u2007\u202f":
        text = text.replace(ch, " ")
    # Mehrfach-Whitespace (inkl. Zeilenumbrueche) zu einem Leerzeichen
    text = _re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _find_best_match(needle: str, haystack: str) -> int | None:
    """Mehrstufige Suche: exakt → normalisiert → Wort-Ngrams → Sliding-Window."""
    import re as _re

    # Stufe 1: Exakter Match (erste 60 Zeichen)
    snippet = needle[:60].strip()
    if snippet:
        idx = haystack.find(snippet)
        if idx != -1:
            return idx

    # Stufe 2: Normalisierter Match
    norm_needle = _normalize(needle[:80])
    norm_hay = _normalize(haystack)
    idx_norm = norm_hay.find(norm_needle[:60])
    if idx_norm != -1:
        # Zurueck auf Position im Original-Haystack mappen
        # Approximation: gleicher Anteil
        ratio = idx_norm / max(len(norm_hay), 1)
        approx_idx = int(ratio * len(haystack))
        # Suche in der Naehe des approx_idx nach einem Wort-Anker
        anchor_words = needle.split()[:3]
        for w in anchor_words:
            w_clean = w.strip(".,;:!?\"'()-–")
            if len(w_clean) < 4:
                continue
            local_start = max(0, approx_idx - 200)
            local_end = min(len(haystack), approx_idx + 500)
            local_idx = haystack.find(w_clean, local_start, local_end)
            if local_idx != -1:
                return local_idx
        # Fallback: nutze approx_idx
        return approx_idx

    # Stufe 3: Wort-Ngram Match (suche nach 4-5 aufeinanderfolgenden Woertern)
    words = [w for w in _normalize(needle).split() if len(w) > 3]
    for ngram_len in [5, 4, 3]:
        if len(words) < ngram_len:
            continue
        for start in range(len(words) - ngram_len + 1):
            ngram = " ".join(words[start:start + ngram_len])
            idx_ng = norm_hay.find(ngram)
            if idx_ng != -1:
                ratio = idx_ng / max(len(norm_hay), 1)
                approx_idx = int(ratio * len(haystack))
                # Verifiziere mit einem Wort in der Naehe
                check_word = words[start].strip()
                local_start = max(0, approx_idx - 300)
                local_end = min(len(haystack), approx_idx + 500)
                local_idx = haystack.lower().find(check_word, local_start, local_end)
                if local_idx != -1:
                    return local_idx
                return approx_idx

    # Stufe 4: Einzelwort-Fallback (laengstes seltenes Wort)
    rare_words = sorted(
        [w for w in words if len(w) > 6],
        key=lambda w: norm_hay.count(w)
    )
    if rare_words:
        rarest = rare_words[0]
        idx_r = norm_hay.find(rarest)
        if idx_r != -1:
            ratio = idx_r / max(len(norm_hay), 1)
            return int(ratio * len(haystack))

    return None


def inject_markers(markdown_text: str, highlights: list) -> tuple[str, list]:
    """Fuege <!-- A311: --> Marker in den Markdown-Text ein, wo Highlights matchen.

    Returns:
        (modified_text, unmatched_highlights)
    """
    unmatched = []
    # Sortiere Highlights nach Position im Text (rueckwaerts), damit Einfuegungen
    # die Indizes nachfolgender Matches nicht verschieben
    positioned = []
    for h in highlights:
        if not h["text"].strip():
            unmatched.append(h)
            continue
        idx = _find_best_match(h["text"], markdown_text)
        if idx is not None:
            positioned.append((idx, h))
        else:
            unmatched.append(h)

    # Rueckwaerts einfuegen (hoechster Index zuerst)
    positioned.sort(key=lambda x: x[0], reverse=True)
    for idx, h in positioned:
        end = markdown_text.find("\n", idx)
        if end == -1:
            end = len(markdown_text)
        comment = h["comment"] if h["comment"] else "Markiert"
        marker = f"\n<!-- A311: {comment} -->"
        markdown_text = markdown_text[:end] + marker + markdown_text[end:]

    # Unmatched: haenge sie als Block am Ende des Frontmatters an
    if unmatched:
        for h in unmatched:
            comment = h["comment"] if h["comment"] else "Markiert"
            page = h.get("page", "?")
            marker = f"\n<!-- A311 [S.{page}, kein Textmatch]: {comment} -->"
            # Finde Ende des Frontmatters und fuege danach ein
            fm_end = markdown_text.find("\n---\n", 4)
            if fm_end != -1:
                insert_pos = fm_end + 5  # nach dem ---\n
                markdown_text = markdown_text[:insert_pos] + marker + "\n" + markdown_text[insert_pos:]

    return markdown_text, unmatched


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_annotations.py <pdf_path> [--json]")
        sys.exit(1)

    result = extract_annotations(sys.argv[1])

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Annotationen gefunden: {result['count']}")
        print(f"  Highlights: {len(result['highlights'])}")
        print(f"  Notizen: {len(result['notes'])}")
        if result["notizen_summary"]:
            print(f"\nNotizen-Feld:\n  {result['notizen_summary'][:500]}")
        for h in result["highlights"]:
            print(f"\n  [S.{h['page']}] {h['text'][:100]}")
            if h["comment"]:
                print(f"    → {h['comment']}")
        for n in result["notes"]:
            print(f"\n  [S.{n['page']} Notiz] {n['text']}")
