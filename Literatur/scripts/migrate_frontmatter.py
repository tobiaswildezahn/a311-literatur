#!/usr/bin/env python3
"""
Migriert den A311-Literaturkorpus auf das neue LLM-optimierte Frontmatter-Schema.

Liest bestehende YAML-Frontmatter + source_classification.json und erzeugt
einheitliche Header mit 13 Feldern. Dateien ohne Frontmatter bekommen einen
neuen Header aus der classification.json + Dateiname-Heuristik.

Nutzung:
    uv run migrate_frontmatter.py              # Dry-Run (zeigt Änderungen)
    uv run migrate_frontmatter.py --write      # Schreibt Dateien
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["python-frontmatter", "pyyaml"]
# ///

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import frontmatter

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

MD_DIR = Path(__file__).parent / "md"
CLASSIFICATION_FILE = Path(__file__).parent / "source_classification.json"

THEMA_ENUM = [
    "Gesamtverteidigung/OPLAN",
    "KRITIS/Infrastrukturschutz",
    "Klimawandel/Naturgefahren",
    "Hybride Bedrohungen/Cyber",
    "Warnung/Uebungen/GeKoB",
    "Ehrenamt/Personal/BOS",
    "Strategietheorie",
    "NATO/International",
    "Recht/Gesetzgebung",
    "Bevoelkerungsschutz allgemein",
]

EBENE_ENUM = ["bund", "land", "kommune", "nato", "eu", "international"]

TYP_ENUM = ["primaer", "sekundaer", "grau", "journalistisch", "tertiaer", "aktivistisch"]

EVIDENZ_ENUM = ["hoch", "mittel", "niedrig"]

# ---------------------------------------------------------------------------
# Mapping: alte category -> neues thema
# ---------------------------------------------------------------------------

CATEGORY_TO_THEMA = {
    "strategiepapiere bund": "Bevoelkerungsschutz allgemein",
    "kritis/blackout": "KRITIS/Infrastrukturschutz",
    "kritis-dachgesetz": "Recht/Gesetzgebung",
    "klimawandel/extremwetter": "Klimawandel/Naturgefahren",
    "oplan/gesamtverteidigung": "Gesamtverteidigung/OPLAN",
    "nato/international": "NATO/International",
    "strategietheorie (lykke)": "Strategietheorie",
    "ehrenamt/personal": "Ehrenamt/Personal/BOS",
    "hamburg": "Bevoelkerungsschutz allgemein",
    "übungen/warnung": "Warnung/Uebungen/GeKoB",
    "uebungen/warnung": "Warnung/Uebungen/GeKoB",
    "weitere kontextquellen": "Bevoelkerungsschutz allgemein",
    "think tanks": "Bevoelkerungsschutz allgemein",
    "hybride bedrohungen": "Hybride Bedrohungen/Cyber",
}

# Keywords in Institution/Titel -> ebene
NATO_KEYWORDS = ["nato", "nato act", "nato cimic", "naadsn"]
EU_KEYWORDS = ["eu council", "eu jrc", "eu/dg echo", "eu ", "clingendael"]
INTERNATIONAL_KEYWORDS = ["msb schweden", "isdp", "modern war institute", "west point",
                          "army war college", "us army", "strategycentral"]
LAND_KEYWORDS = ["hamburg", "bv hamburg", "polizei hamburg", "stmwi bayern",
                 "landtag rlp", "spd-fraktion rlp", "spd rlp"]
KOMMUNE_KEYWORDS = ["dstgb", "deutscher staedtetag", "deutscher landkreistag",
                    "kommunal"]


def clean_category(raw: str) -> str:
    """Entfernt Markdown-Links aus category-Werten."""
    # z.B. "[Hybride Bedrohungen](45_BBK_Hybride_Bedrohungen.md)" -> "Hybride Bedrohungen"
    # z.B. "Berliner [[Stromausfall](74...)...](...) 2026" -> Berliner Stromausfall 2026
    cleaned = re.sub(r'\[([^\[\]]*)\]\([^)]*\)', r'\1', raw)
    # Nochmal für verschachtelte Links
    cleaned = re.sub(r'\[([^\[\]]*)\]\([^)]*\)', r'\1', cleaned)
    return cleaned.strip()


def map_thema(category: str, title: str, institution: str, filename: str = "") -> str:
    """Mappt alte category auf neues thema."""
    cat_clean = clean_category(category).lower()

    # Spezialfall: Berliner Stromausfall
    if "stromausfall" in cat_clean and "berlin" in cat_clean:
        return "KRITIS/Infrastrukturschutz"

    # Direktes Mapping
    for key, val in CATEGORY_TO_THEMA.items():
        if key in cat_clean:
            return val

    # Titel + Dateiname + Institution Heuristik
    combined = f"{(title or '').lower()} {filename.lower()} {(institution or '').lower()}"

    if any(k in combined for k in ["oplan", "gesamtverteidigung", "zivile verteidigung",
                                    "rrgv", "rahmenrichtlini", "weissbuch", "kriegstüchtig",
                                    "meilenstein_sicherheitspolitik", "plenardebatte_haushalt",
                                    "bloag", "zmz"]):
        return "Gesamtverteidigung/OPLAN"
    if any(k in combined for k in ["kritis", "stromausfall", "blackout", "infrastruktur",
                                    "stromnetz", "cyber", "sabotage", "it-sicherheit",
                                    "bdew", "vku", "taylor wessing", "goerg"]):
        return "KRITIS/Infrastrukturschutz"
    if any(k in combined for k in ["nato", "resilience", "alliance", "cimic",
                                    "strategic concept", "civil preparedness",
                                    "clingendael", "naadsn", "marshall fund"]):
        return "NATO/International"
    if any(k in combined for k in ["klima", "hochwasser", "hitze", "extremwetter",
                                    "naturgefahren", "waldbrand", "dwd", "uba",
                                    "greenpeace"]):
        return "Klimawandel/Naturgefahren"
    if any(k in combined for k in ["hybrid", "desinformation", "bfv", "verfassungsschutz",
                                    "bka", "gba", "spionage"]):
        return "Hybride Bedrohungen/Cyber"
    if any(k in combined for k in ["warnung", "übung", "lükex", "gekob", "sifo",
                                    "bundesrechnungshof", "babz"]):
        return "Warnung/Uebungen/GeKoB"
    if any(k in combined for k in ["ehrenamt", "freiwillig", "personal", "feuerwehr",
                                    "thw_", "dfv"]):
        return "Ehrenamt/Personal/BOS"
    if any(k in combined for k in ["dachgesetz", "kritis-dach", "datenschutz"]):
        return "Recht/Gesetzgebung"
    if any(k in combined for k in ["lykke", "yarger", "ends means ways", "strategy theory",
                                    "cgsc"]):
        return "Strategietheorie"
    if any(k in combined for k in ["schweden", "if crisis", "tab_stromausfall",
                                    "risikoanalyse"]):
        return "KRITIS/Infrastrukturschutz"
    if any(k in combined for k in ["dgap", "think tank", "bertelsmann", "boell",
                                    "krisennavigator"]):
        return "Bevoelkerungsschutz allgemein"
    if any(k in combined for k in ["eu council", "eu jrc"]):
        return "NATO/International"

    return "Bevoelkerungsschutz allgemein"


def map_ebene(institution: str, category: str, title: str) -> str:
    """Bestimmt die Governance-Ebene heuristisch."""
    inst_lower = (institution or "").lower()
    cat_lower = clean_category(category or "").lower()
    title_lower = (title or "").lower()
    combined = f"{inst_lower} {cat_lower} {title_lower}"

    if any(k in inst_lower for k in NATO_KEYWORDS):
        return "nato"
    if any(k in inst_lower for k in EU_KEYWORDS):
        return "eu"
    if any(k in inst_lower for k in INTERNATIONAL_KEYWORDS):
        return "international"
    if any(k in combined for k in LAND_KEYWORDS):
        return "land"
    if any(k in combined for k in KOMMUNE_KEYWORDS):
        return "kommune"
    return "bund"


def normalize_date(date_str: str | None, fallback_year: int | None) -> str:
    """Normalisiert Datum auf YYYY-MM-DD."""
    if date_str:
        date_str = str(date_str).strip()
        # DD.MM.YYYY
        m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
        if m:
            return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        # YYYY-MM-DD (evtl. mit Uhrzeit)
        m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if m:
            return m.group(0)
        # Nur YYYY
        m = re.match(r'^(\d{4})$', date_str)
        if m:
            return f"{m.group(1)}-01-01"

    if fallback_year:
        return f"{fallback_year}-01-01"

    return "unknown"


def clean_description(desc: str | None) -> str:
    """Bereinigt description: entfernt Markdown-Links, kürzt auf 300 Zeichen."""
    if not desc:
        return "TODO"
    desc = str(desc)
    # Markdown-Links -> nur Text
    desc = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', desc)
    desc = desc.strip()
    if len(desc) > 300:
        desc = desc[:297] + "..."
    return desc if desc else "TODO"


def extract_nr_from_filename(filename: str) -> int | None:
    """Extrahiert Dokumentnummer aus Dateiname wie '44_IMK_AG_Bericht.md'."""
    m = re.match(r'^(\d+)_', filename)
    return int(m.group(1)) if m else None


def extract_bezug_from_fields(category: str | None, tags: list | None) -> list[int]:
    """Extrahiert nr-Referenzen aus Markdown-Links in category/tags."""
    bezug = set()
    for text in [str(category or ""), str(tags or "")]:
        for m in re.finditer(r'\((\d+)_[^)]+\.md\)', text):
            bezug.add(int(m.group(1)))
    return sorted(bezug) if bezug else []


def extract_title_from_body(content: str) -> str:
    """Für Dateien ohne Frontmatter: Titel aus erster Überschrift."""
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            return line.lstrip('# ').strip().strip('*')
    # Fallback: erste nicht-leere Zeile
    for line in content.split('\n'):
        line = line.strip()
        if line:
            return line[:100]
    return "Unbekannt"


def migrate_file(filepath: Path, classifications: dict, write: bool) -> dict:
    """Migriert eine einzelne Datei. Gibt Status-Dict zurück."""
    raw = filepath.read_text(encoding='utf-8')
    nr = extract_nr_from_filename(filepath.name)
    # JSON-Keys können "7" oder "07" sein
    classification = {}
    if nr is not None:
        classification = (classifications.get(str(nr))
                         or classifications.get(f"{nr:02d}")
                         or classifications.get(f"{nr:03d}")
                         or {})

    try:
        post = frontmatter.loads(raw)
        has_frontmatter = bool(post.metadata)
    except Exception:
        has_frontmatter = False
        post = frontmatter.Post(raw)

    old_meta = dict(post.metadata) if has_frontmatter else {}

    # Bereits migriert? (hat 'thema' und 'evidenzgrad' im Frontmatter)
    if 'thema' in old_meta and 'evidenzgrad' in old_meta:
        return {
            'file': filepath.name,
            'had_frontmatter': True,
            'nr': old_meta.get('nr', nr or 0),
            'thema': old_meta['thema'],
            'ebene': old_meta.get('ebene', 'bund'),
            'todo_summary': old_meta.get('zusammenfassung') == 'TODO',
            'todo_tags': old_meta.get('schlagworte') == ['TODO'],
            'skipped': True,
        }

    # --- Neue Felder aufbauen ---
    new_meta = {}

    # nr
    new_meta['nr'] = nr or old_meta.get('nr', 0)

    # title
    if old_meta.get('title'):
        new_meta['title'] = str(old_meta['title'])
    else:
        new_meta['title'] = extract_title_from_body(post.content)

    # datum
    old_date = old_meta.get('date') or old_meta.get('datum')
    new_meta['datum'] = normalize_date(
        str(old_date) if old_date else None,
        classification.get('jahr')
    )

    # institution (aus classification.json bevorzugt, Fallback: old source/author)
    new_meta['institution'] = (
        classification.get('institution')
        or old_meta.get('source')
        or old_meta.get('author')
        or "Unbekannt"
    )

    # typ
    new_meta['typ'] = classification.get('typ', old_meta.get('typ', 'grau'))

    # evidenzgrad
    new_meta['evidenzgrad'] = classification.get('evidenzgrad', old_meta.get('evidenzgrad', 'niedrig'))

    # thema
    old_category = str(old_meta.get('category', ''))
    new_meta['thema'] = map_thema(old_category, new_meta['title'], new_meta['institution'], filepath.name)

    # ebene
    new_meta['ebene'] = map_ebene(new_meta['institution'], old_category, new_meta['title'])

    # schlagworte (Platzhalter — wird in Phase C verfeinert)
    old_tags = old_meta.get('tags', [])
    if isinstance(old_tags, list) and old_tags:
        # Alte Tags bereinigen
        cleaned = [clean_category(str(t)).lower().replace(' ', '-').replace('/', '-')
                   for t in old_tags if t]
        # Nur behalten wenn sie nicht identisch mit thema sind
        thema_slug = new_meta['thema'].lower().replace(' ', '-').replace('/', '-')
        cleaned = [t for t in cleaned if t != thema_slug]
        new_meta['schlagworte'] = cleaned if cleaned else ["TODO"]
    else:
        new_meta['schlagworte'] = ["TODO"]

    # zusammenfassung
    new_meta['zusammenfassung'] = clean_description(old_meta.get('description'))

    # url (optional)
    if old_meta.get('url'):
        new_meta['url'] = str(old_meta['url'])

    # autor (optional — nur Personennamen, keine Institutionen)
    author = old_meta.get('author', '')
    if author and author != new_meta['institution']:
        # Heuristik: Personennamen enthalten Leerzeichen und sind kurz
        if ' ' in str(author) or len(str(author)) < 30:
            new_meta['autor'] = str(author)

    # bezug (optional)
    bezug = extract_bezug_from_fields(old_meta.get('category'), old_meta.get('tags'))
    if bezug:
        new_meta['bezug'] = bezug

    # --- Schreiben ---
    post.metadata = new_meta

    if write:
        # YAML-Feld-Reihenfolge sicherstellen
        output = build_yaml_output(new_meta, post.content)
        filepath.write_text(output, encoding='utf-8')

    return {
        'file': filepath.name,
        'had_frontmatter': has_frontmatter,
        'nr': new_meta['nr'],
        'thema': new_meta['thema'],
        'ebene': new_meta['ebene'],
        'todo_summary': new_meta['zusammenfassung'] == 'TODO',
        'todo_tags': new_meta['schlagworte'] == ['TODO'],
    }


def build_yaml_output(meta: dict, content: str) -> str:
    """Baut YAML-Frontmatter mit definierter Feldreihenfolge."""
    field_order = ['nr', 'title', 'datum', 'institution', 'typ', 'evidenzgrad',
                   'thema', 'ebene', 'schlagworte', 'zusammenfassung',
                   'url', 'autor', 'bezug']

    lines = ['---']
    for key in field_order:
        if key not in meta:
            continue
        val = meta[key]
        if isinstance(val, list):
            if all(isinstance(v, int) for v in val):
                lines.append(f"{key}: {json.dumps(val)}")
            else:
                lines.append(f"{key}: {json.dumps(val, ensure_ascii=False)}")
        elif isinstance(val, int):
            lines.append(f"{key}: {val}")
        elif '\n' in str(val):
            lines.append(f'{key}: >-')
            for l in str(val).split('\n'):
                lines.append(f'  {l}')
        elif any(c in str(val) for c in [':', '"', "'", '{', '}', '[', ']', '#', '&', '*', '!', '|', '>', '%', '@', '`']):
            escaped = str(val).replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
        else:
            lines.append(f"{key}: {val}")
    lines.append('---')
    lines.append('')

    # Content: ggf. alten Body beibehalten
    return '\n'.join(lines) + content


def main():
    parser = argparse.ArgumentParser(description='Migriert A311-Korpus auf neues Frontmatter-Schema')
    parser.add_argument('--write', action='store_true', help='Dateien tatsächlich schreiben')
    args = parser.parse_args()

    # Classification laden
    with open(CLASSIFICATION_FILE, encoding='utf-8') as f:
        classifications = json.load(f)

    # Alle .md Dateien (außer README, index)
    md_files = sorted(
        [f for f in MD_DIR.glob('*.md')
         if f.name not in ('README.md', 'index.md') and re.match(r'^\d+_', f.name)],
        key=lambda p: extract_nr_from_filename(p.name) or 0
    )

    print(f"{'DRY RUN' if not args.write else 'SCHREIBE'}: {len(md_files)} Dateien")
    print("=" * 70)

    stats = {
        'total': len(md_files),
        'migrated': 0,
        'no_frontmatter': 0,
        'todo_summary': 0,
        'todo_tags': 0,
        'thema_counts': {},
        'ebene_counts': {},
    }

    for f in md_files:
        result = migrate_file(f, classifications, write=args.write)
        stats['migrated'] += 1
        if result.get('skipped'):
            stats.setdefault('skipped', 0)
            stats['skipped'] += 1
        if not result['had_frontmatter']:
            stats['no_frontmatter'] += 1
        if result['todo_summary']:
            stats['todo_summary'] += 1
        if result['todo_tags']:
            stats['todo_tags'] += 1
        stats['thema_counts'][result['thema']] = stats['thema_counts'].get(result['thema'], 0) + 1
        stats['ebene_counts'][result['ebene']] = stats['ebene_counts'].get(result['ebene'], 0) + 1

        status = []
        if not result['had_frontmatter']:
            status.append("NEU")
        if result['todo_summary']:
            status.append("TODO:summary")
        if result['todo_tags']:
            status.append("TODO:tags")
        status_str = f"  [{', '.join(status)}]" if status else ""
        print(f"  {result['nr']:>3} | {result['thema']:<35} | {result['ebene']:<12}{status_str}")

    print("=" * 70)
    print(f"\nStatistik:")
    print(f"  Dateien gesamt:     {stats['total']}")
    print(f"  Übersprungen:       {stats.get('skipped', 0)}")
    print(f"  Ohne Frontmatter:   {stats['no_frontmatter']}")
    print(f"  TODO Summary:       {stats['todo_summary']}")
    print(f"  TODO Schlagworte:   {stats['todo_tags']}")
    print(f"\nThema-Verteilung:")
    for thema, count in sorted(stats['thema_counts'].items(), key=lambda x: -x[1]):
        print(f"  {thema:<40} {count:>3}")
    print(f"\nEbene-Verteilung:")
    for ebene, count in sorted(stats['ebene_counts'].items(), key=lambda x: -x[1]):
        print(f"  {ebene:<15} {count:>3}")

    if not args.write:
        print(f"\n⚠️  Dry-Run — keine Dateien geändert. Mit --write ausführen.")


if __name__ == '__main__':
    main()
