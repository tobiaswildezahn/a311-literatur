#!/usr/bin/env python3
"""Entfernt doppelte Frontmatter-Blöcke: behält nur den ersten (neuen) Block."""
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import re
import sys
from pathlib import Path

MD_DIR = Path(__file__).parent / "md"

def fix_file(filepath: Path, write: bool) -> bool:
    """Fixe doppeltes Frontmatter. Returns True if fixed."""
    text = filepath.read_text(encoding='utf-8')

    # Zähle --- Marker am Zeilenanfang
    markers = [i for i, line in enumerate(text.split('\n')) if line.strip() == '---']

    if len(markers) <= 2:
        return False  # Kein doppeltes Frontmatter

    lines = text.split('\n')

    # Erster Block: markers[0] bis markers[1]
    first_block_end = markers[1]

    # Zweiter Block: markers[2] bis markers[3] (wenn vorhanden)
    if len(markers) >= 4:
        second_block_end = markers[3]
        # Body beginnt nach dem zweiten Block
        body = '\n'.join(lines[second_block_end + 1:])
    elif len(markers) == 3:
        # Nur 3 Marker: der dritte ist wahrscheinlich ein Trennstrich im Body
        # Prüfe ob zwischen Marker 2 und 3 YAML-artige Inhalte sind
        between = lines[markers[2]:]
        # Kein zweiter Block — Body beginnt nach erstem Block
        # Aber der dritte --- könnte ein Separator im Markdown sein
        body = '\n'.join(lines[first_block_end + 1:])
        # Wenn body mit --- anfängt und danach kein key: value kommt, ist es ein MD-Separator
        body_lines = body.lstrip('\n').split('\n')
        if body_lines and body_lines[0].strip() == '---':
            # Prüfe ob nächste Zeile YAML ist
            if len(body_lines) > 1 and ':' in body_lines[1] and not body_lines[1].startswith('#'):
                # Zweiter YAML-Block — entferne ihn
                # Finde Ende dieses Blocks
                for i, l in enumerate(body_lines[1:], 1):
                    if l.strip() == '---':
                        body = '\n'.join(body_lines[i + 1:])
                        break
        return False  # Nicht sicher genug, manuell prüfen

    # Behalte ersten Block + Body
    header = '\n'.join(lines[:first_block_end + 1])
    result = header + '\n' + body.lstrip('\n')

    # Stelle sicher, dass Body nicht mit --- beginnt (alter zweiter Header-Rest)
    # Entferne alle weiteren YAML-Blöcke die direkt nach dem Header kommen
    while result.split('---', 2)[-1].lstrip().startswith('---'):
        parts = result.split('---')
        # Kompliziert — besser einfach Regex
        break

    if write:
        filepath.write_text(result, encoding='utf-8')

    return True


def fix_file_v2(filepath: Path, write: bool) -> bool:
    """Robustere Version: erkennt und entfernt den alten Frontmatter-Block."""
    text = filepath.read_text(encoding='utf-8')
    lines = text.split('\n')

    # Finde alle --- Positionen
    markers = [i for i, line in enumerate(lines) if line.strip() == '---']

    if len(markers) < 4:
        # 3 Marker: prüfe ob der dritte ein alter YAML-Block ist
        if len(markers) == 3:
            # Prüfe ob zwischen markers[2] und Ende YAML-Felder stehen
            return False
        return False

    # 4+ Marker: erster Block ist [0..1], zweiter Block ist [2..3]
    # Prüfe ob der zweite Block alte Felder hat (category, slug, type, tags)
    second_block = '\n'.join(lines[markers[2]:markers[3] + 1])
    old_fields = ['category:', 'slug:', 'type:', 'tags:']

    if any(f in second_block for f in old_fields):
        # Alter Block gefunden — entfernen
        new_lines = lines[:markers[2]] + lines[markers[3] + 1:]
        result = '\n'.join(new_lines)

        # Evtl. leere Zeilen bereinigen
        result = re.sub(r'\n{3,}', '\n\n', result)

        if write:
            filepath.write_text(result, encoding='utf-8')
        return True

    return False


def main():
    write = '--write' in sys.argv

    md_files = sorted(MD_DIR.glob('[0-9]*.md'))
    fixed = 0

    for f in md_files:
        text = f.read_text(encoding='utf-8')
        marker_count = text.count('\n---\n') + (1 if text.startswith('---\n') else 0)

        if fix_file_v2(f, write):
            fixed += 1
            print(f"  FIXED: {f.name}")

    print(f"\n{'Geschrieben' if write else 'Dry-Run'}: {fixed} Dateien korrigiert")
    if not write and fixed:
        print("  Mit --write ausführen um zu schreiben.")


if __name__ == '__main__':
    main()
