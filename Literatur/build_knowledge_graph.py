#!/usr/bin/env python3
"""
Wissensgraph-Generator fuer den A311-Literaturkorpus.

Zwei Graphtypen:
1. URL-Kookkurrenz: Dokumente, die auf dieselbe externe URL verweisen, sind verbunden.
2. Themen-Cluster: Dokumente werden nach geteilten URL-Domaenen gruppiert.

Ausgabe: Mermaid-Diagramm, JSON-Daten, Analyse-Report.

Nutzung:
    python3 build_knowledge_graph.py [--min-shared 1] [--output-dir .]
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

MD_DIR = Path(__file__).parent / "md"
DEFAULT_MIN_SHARED = 2  # Mindestanzahl geteilter URLs fuer eine Kante

# Quellenklassifikation nach wissenschaftlichen Standards
SOURCE_CLASSIFICATION = {
    "01": {"typ": "primaer", "institution": "Bundesregierung", "jahr": 2023, "evidenzgrad": "hoch"},
    "02": {"typ": "primaer", "institution": "BMI/BMVg", "jahr": 2024, "evidenzgrad": "hoch"},
    "04": {"typ": "primaer", "institution": "BMVg", "jahr": 2024, "evidenzgrad": "hoch"},
    "05": {"typ": "primaer", "institution": "BMI/Bundesregierung", "jahr": 2016, "evidenzgrad": "hoch"},
    "06": {"typ": "primaer", "institution": "Deutscher Bundestag", "jahr": 2024, "evidenzgrad": "hoch"},
    "07": {"typ": "primaer", "institution": "BMI/Bundesregierung", "jahr": 2026, "evidenzgrad": "hoch"},
    "08": {"typ": "primaer", "institution": "BBK/BMI", "jahr": 2024, "evidenzgrad": "hoch"},
    "10": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "11": {"typ": "primaer", "institution": "Bundesregierung/BBK", "jahr": 2023, "evidenzgrad": "hoch"},
    "12": {"typ": "primaer", "institution": "Deutscher Bundestag", "jahr": 2022, "evidenzgrad": "hoch"},
    "13": {"typ": "primaer", "institution": "Deutscher Bundestag", "jahr": 2024, "evidenzgrad": "hoch"},
    "14": {"typ": "primaer", "institution": "Deutscher Bundestag", "jahr": 2025, "evidenzgrad": "hoch"},
    "15": {"typ": "primaer", "institution": "Deutscher Bundestag", "jahr": 2026, "evidenzgrad": "hoch"},
    "16": {"typ": "sekundaer", "institution": "datenschutz-notizen.de", "jahr": 2026, "evidenzgrad": "mittel"},
    "17": {"typ": "grau", "institution": "BayIKa-Bau / Prof. Gebbeken", "jahr": 2026, "evidenzgrad": "mittel"},
    "18": {"typ": "grau", "institution": "Roedl & Partner", "jahr": 2026, "evidenzgrad": "mittel"},
    "20": {"typ": "journalistisch", "institution": "Radio Hamburg", "jahr": 2024, "evidenzgrad": "niedrig"},
    "21": {"typ": "primaer", "institution": "BV Hamburg-Nord", "jahr": 2022, "evidenzgrad": "mittel"},
    "22": {"typ": "primaer", "institution": "NATO", "jahr": 2024, "evidenzgrad": "hoch"},
    "24": {"typ": "grau", "institution": "NATO CIMIC COE", "jahr": 2018, "evidenzgrad": "mittel"},
    "28": {"typ": "sekundaer", "institution": "IOS Press", "jahr": 2023, "evidenzgrad": "hoch"},
    "29": {"typ": "grau", "institution": "NATO CPG", "jahr": 2024, "evidenzgrad": "mittel"},
    "30": {"typ": "grau", "institution": "Bertelsmann Stiftung", "jahr": 2025, "evidenzgrad": "mittel"},
    "31": {"typ": "grau", "institution": "NAADSN", "jahr": 2025, "evidenzgrad": "mittel"},
    "33": {"typ": "sekundaer", "institution": "EU JRC", "jahr": 2024, "evidenzgrad": "hoch"},
    "34": {"typ": "grau", "institution": "EU/DG ECHO/Weltbank", "jahr": 2024, "evidenzgrad": "mittel"},
    "36": {"typ": "sekundaer", "institution": "US Army War College / Parameters", "jahr": 2016, "evidenzgrad": "hoch"},
    "37": {"typ": "sekundaer", "institution": "US Army War College / Parameters", "jahr": 2017, "evidenzgrad": "hoch"},
    "38": {"typ": "sekundaer", "institution": "Modern War Institute / West Point", "jahr": 2020, "evidenzgrad": "mittel"},
    "39": {"typ": "sekundaer", "institution": "Army War College War Room", "jahr": 2021, "evidenzgrad": "mittel"},
    "40": {"typ": "sekundaer", "institution": "StrategyCentral / J. Meiser", "jahr": 2024, "evidenzgrad": "mittel"},
    "41": {"typ": "sekundaer", "institution": "US Army CGSC", "jahr": 2022, "evidenzgrad": "hoch"},
    "42": {"typ": "sekundaer", "institution": "US Army War College / Yarger", "jahr": 2006, "evidenzgrad": "hoch"},
    "44": {"typ": "primaer", "institution": "IMK / Bund-Laender-AG ZV/ZMZ", "jahr": 2025, "evidenzgrad": "hoch"},
    "45": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "46": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "47": {"typ": "primaer", "institution": "BfV", "jahr": 2025, "evidenzgrad": "hoch"},
    "48": {"typ": "journalistisch", "institution": "CORRECTIV", "jahr": 2024, "evidenzgrad": "mittel"},
    "49": {"typ": "journalistisch", "institution": "CORRECTIV", "jahr": 2025, "evidenzgrad": "mittel"},
    "50": {"typ": "grau", "institution": "StMWi Bayern", "jahr": 2024, "evidenzgrad": "mittel"},
    "51": {"typ": "journalistisch", "institution": "Handelsblatt", "jahr": 2026, "evidenzgrad": "niedrig"},
    "52": {"typ": "journalistisch", "institution": "Ukrainska Pravda", "jahr": 2025, "evidenzgrad": "niedrig"},
    "53": {"typ": "journalistisch", "institution": "blogist.de", "jahr": 2025, "evidenzgrad": "niedrig"},
    "54": {"typ": "sekundaer", "institution": "it-service.network", "jahr": 2025, "evidenzgrad": "niedrig"},
    "55": {"typ": "grau", "institution": "security-network.com", "jahr": 2025, "evidenzgrad": "mittel"},
    "56": {"typ": "grau", "institution": "defence-network.com", "jahr": 2025, "evidenzgrad": "mittel"},
    "57": {"typ": "grau", "institution": "security-network.com", "jahr": 2025, "evidenzgrad": "mittel"},
    "58": {"typ": "journalistisch", "institution": "Behoerden Spiegel", "jahr": 2024, "evidenzgrad": "niedrig"},
    "59": {"typ": "journalistisch", "institution": "Reservistenverband", "jahr": 2024, "evidenzgrad": "niedrig"},
    "60": {"typ": "tertiaer", "institution": "Wikipedia", "jahr": 2025, "evidenzgrad": "niedrig"},
    "61": {"typ": "tertiaer", "institution": "Wikipedia", "jahr": 2024, "evidenzgrad": "niedrig"},
    "62": {"typ": "journalistisch", "institution": "CORRECTIV", "jahr": 2025, "evidenzgrad": "mittel"},
    "63": {"typ": "grau", "institution": "sachgebiet5.de", "jahr": 2025, "evidenzgrad": "niedrig"},
    "64": {"typ": "grau", "institution": "Strategy& (PwC) / MSC", "jahr": 2024, "evidenzgrad": "mittel"},
    "65": {"typ": "sekundaer", "institution": "DGAP", "jahr": 2025, "evidenzgrad": "hoch"},
    "66": {"typ": "sekundaer", "institution": "DGAP", "jahr": 2025, "evidenzgrad": "hoch"},
    "67": {"typ": "sekundaer", "institution": "DGAP", "jahr": 2025, "evidenzgrad": "hoch"},
    "68": {"typ": "sekundaer", "institution": "Metis Institut / UniBw", "jahr": 2024, "evidenzgrad": "hoch"},
    "69": {"typ": "sekundaer", "institution": "Heinrich-Boell-Stiftung", "jahr": 2025, "evidenzgrad": "mittel"},
    "70": {"typ": "sekundaer", "institution": "ISDP", "jahr": 2025, "evidenzgrad": "hoch"},
    "71": {"typ": "sekundaer", "institution": "Krisennavigator / Univ. Kiel", "jahr": 2024, "evidenzgrad": "mittel"},
    "72": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "73": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "74": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "75": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "76": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "77": {"typ": "sekundaer", "institution": "bpb / Univ. Wuppertal", "jahr": 2023, "evidenzgrad": "hoch"},
    "78": {"typ": "journalistisch", "institution": "ZDF Frontal", "jahr": 2026, "evidenzgrad": "mittel"},
    "79": {"typ": "grau", "institution": "EnBW", "jahr": 2024, "evidenzgrad": "niedrig"},
    "80": {"typ": "journalistisch", "institution": "t-online", "jahr": 2022, "evidenzgrad": "niedrig"},
    "81": {"typ": "journalistisch", "institution": "produktion.de", "jahr": 2022, "evidenzgrad": "niedrig"},
    "82": {"typ": "journalistisch", "institution": "Markt und Mittelstand", "jahr": 2026, "evidenzgrad": "niedrig"},
    "83": {"typ": "sekundaer", "institution": "ESKP / Helmholtz", "jahr": 2024, "evidenzgrad": "hoch"},
    "84": {"typ": "grau", "institution": "ECCT", "jahr": 2026, "evidenzgrad": "niedrig"},
    "85": {"typ": "tertiaer", "institution": "Wikipedia", "jahr": 2026, "evidenzgrad": "niedrig"},
    "86": {"typ": "journalistisch", "institution": "Tagesspiegel", "jahr": 2026, "evidenzgrad": "mittel"},
    "87": {"typ": "journalistisch", "institution": "Cleanthinking.de", "jahr": 2026, "evidenzgrad": "niedrig"},
    "88": {"typ": "grau", "institution": "GrafKerssenbrock.com", "jahr": 2026, "evidenzgrad": "mittel"},
    "89": {"typ": "primaer", "institution": "BKA / GBA", "jahr": 2026, "evidenzgrad": "hoch"},
    "90": {"typ": "journalistisch", "institution": "ZDF", "jahr": 2026, "evidenzgrad": "mittel"},
    "91": {"typ": "journalistisch", "institution": "t-online", "jahr": 2026, "evidenzgrad": "mittel"},
    "92": {"typ": "journalistisch", "institution": "nd-aktuell", "jahr": 2026, "evidenzgrad": "mittel"},
    "93": {"typ": "journalistisch", "institution": "Security Insider", "jahr": 2026, "evidenzgrad": "mittel"},
    "94": {"typ": "journalistisch", "institution": "inFranken.de", "jahr": 2026, "evidenzgrad": "niedrig"},
    "95": {"typ": "grau", "institution": "DWD", "jahr": 2025, "evidenzgrad": "hoch"},
    "96": {"typ": "primaer", "institution": "DWD", "jahr": 2025, "evidenzgrad": "hoch"},
    "97": {"typ": "grau", "institution": "Bundesregierung", "jahr": 2025, "evidenzgrad": "mittel"},
    "98": {"typ": "tertiaer", "institution": "bpb", "jahr": 2023, "evidenzgrad": "mittel"},
    "99": {"typ": "aktivistisch", "institution": "Greenpeace", "jahr": 2024, "evidenzgrad": "mittel"},
    "100": {"typ": "tertiaer", "institution": "Wikipedia", "jahr": 2024, "evidenzgrad": "niedrig"},
    "101": {"typ": "grau", "institution": "BBK", "jahr": 2024, "evidenzgrad": "mittel"},
    "102": {"typ": "sekundaer", "institution": "UFZ / GFZ Helmholtz", "jahr": 2024, "evidenzgrad": "hoch"},
    "103": {"typ": "primaer", "institution": "Umweltbundesamt", "jahr": 2023, "evidenzgrad": "hoch"},
    "104": {"typ": "primaer", "institution": "RKI", "jahr": 2025, "evidenzgrad": "hoch"},
    "105": {"typ": "tertiaer", "institution": "bpb", "jahr": 2025, "evidenzgrad": "mittel"},
    "106": {"typ": "grau", "institution": "DStGB", "jahr": 2024, "evidenzgrad": "mittel"},
    "107": {"typ": "primaer", "institution": "GDV", "jahr": 2025, "evidenzgrad": "hoch"},
    "108": {"typ": "grau", "institution": "DStGB / DFV", "jahr": 2022, "evidenzgrad": "mittel"},
    "110": {"typ": "journalistisch", "institution": "Blick Aktuell", "jahr": 2024, "evidenzgrad": "niedrig"},
    "111": {"typ": "aktivistisch", "institution": "SPD-Fraktion RLP", "jahr": 2024, "evidenzgrad": "niedrig"},
    "112": {"typ": "sekundaer", "institution": "BBK / HoWaS2021-Konsortium", "jahr": 2023, "evidenzgrad": "hoch"},
    "113": {"typ": "primaer", "institution": "Bundesregierung (BMI/BMF)", "jahr": 2021, "evidenzgrad": "hoch"},
    "114": {"typ": "grau", "institution": "BBK", "jahr": 2026, "evidenzgrad": "mittel"},
    "115": {"typ": "journalistisch", "institution": "Behoerden Spiegel", "jahr": 2026, "evidenzgrad": "mittel"},
    "116": {"typ": "journalistisch", "institution": "Finanznachrichten.de", "jahr": 2026, "evidenzgrad": "niedrig"},
    "117": {"typ": "grau", "institution": "Deutscher Staedtetag", "jahr": 2026, "evidenzgrad": "mittel"},
    "118": {"typ": "grau", "institution": "BBK / BBSR / DWD / UBA / THW", "jahr": 2025, "evidenzgrad": "mittel"},
    "119": {"typ": "grau", "institution": "THW", "jahr": 2026, "evidenzgrad": "mittel"},
    "120": {"typ": "grau", "institution": "VATM / Vodafone", "jahr": 2023, "evidenzgrad": "mittel"},
    "121": {"typ": "journalistisch", "institution": "Protector.de", "jahr": 2023, "evidenzgrad": "mittel"},
    "122": {"typ": "grau", "institution": "Publicus / Boorberg", "jahr": 2024, "evidenzgrad": "mittel"},
    "123": {"typ": "primaer", "institution": "Bundesrechnungshof", "jahr": 2024, "evidenzgrad": "hoch"},
    "124": {"typ": "grau", "institution": "SIFO / BBK / BMBF", "jahr": 2025, "evidenzgrad": "mittel"},
    "125": {"typ": "grau", "institution": "Polizei Hamburg / BBK", "jahr": 2025, "evidenzgrad": "mittel"},
    "126": {"typ": "journalistisch", "institution": "kommunal.de", "jahr": 2017, "evidenzgrad": "niedrig"},
    "127": {"typ": "journalistisch", "institution": "Blaulicht Magazin", "jahr": 2023, "evidenzgrad": "niedrig"},
    "128": {"typ": "grau", "institution": "THW", "jahr": 2024, "evidenzgrad": "mittel"},
    "131": {"typ": "sekundaer", "institution": "BBK Magazin", "jahr": 2025, "evidenzgrad": "mittel"},
    "132": {"typ": "journalistisch", "institution": "Le Monde Diplomatique", "jahr": 2024, "evidenzgrad": "mittel"},
    "133": {"typ": "journalistisch", "institution": "ZDF", "jahr": 2024, "evidenzgrad": "mittel"},
    "134": {"typ": "grau", "institution": "Deutscher Landkreistag", "jahr": 2025, "evidenzgrad": "mittel"},
    "135": {"typ": "journalistisch", "institution": "Schweizer Bauer", "jahr": 2024, "evidenzgrad": "mittel"},
    "136": {"typ": "grau", "institution": "SPD-Bundestagsfraktion", "jahr": 2021, "evidenzgrad": "niedrig"},
    "138": {"typ": "primaer", "institution": "TAB / Deutscher Bundestag", "jahr": 2011, "evidenzgrad": "hoch"},
    "139": {"typ": "primaer", "institution": "MSB Schweden", "jahr": 2024, "evidenzgrad": "hoch"},
    "140": {"typ": "primaer", "institution": "Bundesregierung (Brandt)", "jahr": 1972, "evidenzgrad": "hoch"},
    "141": {"typ": "primaer", "institution": "Landtag RLP / UA 18/1", "jahr": 2024, "evidenzgrad": "hoch"},
    "142": {"typ": "primaer", "institution": "NATO", "jahr": 2022, "evidenzgrad": "hoch"},
    "143": {"typ": "primaer", "institution": "BMI/BMVg", "jahr": 2024, "evidenzgrad": "hoch"},
}

TYP_LABELS = {
    "primaer": "Primaerquelle",
    "sekundaer": "Sekundaerquelle",
    "tertiaer": "Tertiaerquelle",
    "grau": "Graue Literatur",
    "journalistisch": "Journalistische Quelle",
    "aktivistisch": "Aktivistische Quelle",
}

TYP_STYLES = {
    "primaer": "fill:#2563eb,color:#fff",
    "sekundaer": "fill:#7c3aed,color:#fff",
    "tertiaer": "fill:#6b7280,color:#fff",
    "grau": "fill:#d97706,color:#fff",
    "journalistisch": "fill:#059669,color:#fff",
    "aktivistisch": "fill:#dc2626,color:#fff",
}


def extract_urls(text: str) -> set[str]:
    """Extrahiere alle HTTP(S)-URLs aus Markdown-Text."""
    pattern = r'https?://[^\s\)\]\"\'<>,;}{]+'
    urls = set()
    for match in re.findall(pattern, text):
        # Bereinige trailing Satzzeichen
        clean = match.rstrip('.,;:!?)\'\"')
        # Ignoriere Social-Media-Share-Links und Tracking
        if any(skip in clean for skip in [
            'sharer/sharer', 'intent/tweet', 'pinterest.com/pin',
            'api.whatsapp.com/send', 'policies.google.com',
            'facebook.com/sharer', 't.me/share', 'bsky.app/intent',
            'safelinks.protection.outlook.com'
        ]):
            continue
        urls.add(clean)
    return urls


def normalize_url(url: str) -> str:
    """Normalisiere URL fuer Vergleich (ohne Fragment, trailing slash)."""
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    except ValueError:
        return url


def doc_id_from_filename(filename: str) -> str:
    """Extrahiere Dok-Nummer aus Dateiname."""
    match = re.match(r'^(\d+)_', filename)
    return match.group(1) if match else filename.replace('.md', '')


def short_label(filename: str) -> str:
    """Kurzlabel fuer Graph-Darstellung."""
    name = filename.replace('.md', '')
    # Entferne Nummer und nimm die ersten 3 Wort-Teile
    parts = name.split('_')
    if parts[0].isdigit():
        parts = parts[1:]
    return '_'.join(parts[:3])


def build_graph(min_shared: int = DEFAULT_MIN_SHARED):
    """Baue den Wissensgraphen."""
    md_files = sorted(MD_DIR.glob('[0-9]*.md'))

    # Phase 1: URLs pro Dokument extrahieren
    doc_urls: dict[str, set[str]] = {}
    url_to_docs: dict[str, set[str]] = defaultdict(set)
    doc_labels: dict[str, str] = {}

    for f in md_files:
        doc_id = doc_id_from_filename(f.name)
        doc_labels[doc_id] = short_label(f.name)
        text = f.read_text(encoding='utf-8', errors='ignore')
        urls = {normalize_url(u) for u in extract_urls(text)}
        doc_urls[doc_id] = urls
        for url in urls:
            url_to_docs[url].add(doc_id)

    # Phase 2: Kookkurrenz-Matrix
    edges: dict[tuple[str, str], set[str]] = defaultdict(set)
    for url, docs in url_to_docs.items():
        if len(docs) < 2:
            continue
        doc_list = sorted(docs)
        for i, d1 in enumerate(doc_list):
            for d2 in doc_list[i + 1:]:
                edges[(d1, d2)].add(url)

    # Phase 3: Domaenen-Cluster
    domain_docs: dict[str, set[str]] = defaultdict(set)
    for doc_id, urls in doc_urls.items():
        for url in urls:
            try:
                domain = urlparse(url).netloc.replace('www.', '')
            except ValueError:
                continue
            domain_docs[domain].add(doc_id)

    # Phase 4: Analyse
    # Isolierte Dokumente (keine geteilten URLs)
    connected = set()
    for (d1, d2), shared in edges.items():
        if len(shared) >= min_shared:
            connected.add(d1)
            connected.add(d2)
    all_docs = set(doc_urls.keys())
    isolated = all_docs - connected

    # Hub-Dokumente (meiste Verbindungen)
    connection_count: dict[str, int] = defaultdict(int)
    for (d1, d2), shared in edges.items():
        if len(shared) >= min_shared:
            connection_count[d1] += 1
            connection_count[d2] += 1
    hubs = sorted(connection_count.items(), key=lambda x: -x[1])[:15]

    # Meistzitierte externe URLs
    url_freq = sorted(
        [(url, docs) for url, docs in url_to_docs.items() if len(docs) >= 2],
        key=lambda x: -len(x[1])
    )[:20]

    # Meistgenutzte Domaenen
    domain_freq = sorted(
        [(d, docs) for d, docs in domain_docs.items() if len(docs) >= 3],
        key=lambda x: -len(x[1])
    )[:20]

    # Phase 5: Quellenklassifikation
    classification = {}
    typ_counts: dict[str, int] = defaultdict(int)
    evidenz_counts: dict[str, int] = defaultdict(int)
    for doc_id in all_docs:
        meta = SOURCE_CLASSIFICATION.get(doc_id, {
            "typ": "unbekannt", "institution": "?", "jahr": None, "evidenzgrad": "unbekannt"
        })
        classification[doc_id] = meta
        typ_counts[meta["typ"]] += 1
        evidenz_counts[meta["evidenzgrad"]] += 1

    return {
        'doc_urls': {k: len(v) for k, v in doc_urls.items()},
        'doc_labels': doc_labels,
        'classification': classification,
        'edges': {f"{d1}-{d2}": list(shared) for (d1, d2), shared in edges.items()
                  if len(shared) >= min_shared},
        'edge_weights': {f"{d1}-{d2}": len(shared) for (d1, d2), shared in edges.items()
                         if len(shared) >= min_shared},
        'isolated': sorted(isolated),
        'hubs': hubs,
        'url_freq': [(url, sorted(docs)) for url, docs in url_freq],
        'domain_freq': [(domain, sorted(docs)) for domain, docs in domain_freq],
        'stats': {
            'total_docs': len(all_docs),
            'total_urls': sum(len(v) for v in doc_urls.values()),
            'unique_urls': len(url_to_docs),
            'connected_docs': len(connected),
            'isolated_docs': len(isolated),
            'edges': len([e for e in edges if len(edges[e]) >= min_shared]),
        },
        'typ_counts': dict(typ_counts),
        'evidenz_counts': dict(evidenz_counts),
    }


def generate_mermaid(graph: dict) -> str:
    """Erzeuge Mermaid-Graphen mit Farben nach Quellentyp."""
    lines = ['graph LR']

    # Knoten mit Labels und Quellentyp
    style_classes = defaultdict(list)
    for doc_id, label in sorted(graph['doc_labels'].items()):
        if doc_id in graph['isolated']:
            continue
        meta = graph['classification'].get(doc_id, {})
        typ = meta.get('typ', 'unbekannt')
        typ_short = typ[:3].upper()
        url_count = graph['doc_urls'].get(doc_id, 0)
        lines.append(f'    D{doc_id}["{doc_id}: {label}<br/>{typ_short} | {url_count} URLs"]')
        style_classes[typ].append(f'D{doc_id}')

    # Kanten
    for edge_key, weight in sorted(graph['edge_weights'].items(),
                                     key=lambda x: -x[1]):
        d1, d2 = edge_key.split('-')
        if weight >= 3:
            lines.append(f'    D{d1} ==>|{weight}| D{d2}')
        else:
            lines.append(f'    D{d1} -->|{weight}| D{d2}')

    # Style-Klassen nach Quellentyp
    for typ, style in TYP_STYLES.items():
        nodes = style_classes.get(typ, [])
        if nodes:
            lines.append(f'    style {",".join(nodes)} {style}')

    return '\n'.join(lines)


def generate_report(graph: dict) -> str:
    """Erzeuge Analyse-Report als Markdown."""
    lines = [
        '# Wissensgraph — A311 Literaturkorpus',
        '',
        f'Stand: {__import__("datetime").date.today()}',
        '',
        '## Statistik',
        '',
        f'- **{graph["stats"]["total_docs"]}** Dokumente im Korpus',
        f'- **{graph["stats"]["unique_urls"]}** unique externe URLs',
        f'- **{graph["stats"]["connected_docs"]}** Dokumente mit geteilten Quellen',
        f'- **{graph["stats"]["isolated_docs"]}** isolierte Dokumente (keine geteilten URLs)',
        f'- **{graph["stats"]["edges"]}** Verbindungen (mind. 2 geteilte URLs)',
        '',
        '## Hub-Dokumente (meiste Verbindungen)',
        '',
        '| Dok | Label | Verbindungen |',
        '|-----|-------|-------------|',
    ]
    for doc_id, count in graph['hubs']:
        label = graph['doc_labels'].get(doc_id, '?')
        lines.append(f'| {doc_id} | {label} | {count} |')

    lines += [
        '',
        '## Meistzitierte externe Quellen',
        '',
        '| URL | Dokumente |',
        '|-----|-----------|',
    ]
    for url, docs in graph['url_freq'][:15]:
        lines.append(f'| {url} | {", ".join(docs)} |')

    lines += [
        '',
        '## Meistgenutzte Domaenen',
        '',
        '| Domain | Anzahl Dokumente | Dok-IDs |',
        '|--------|-----------------|---------|',
    ]
    for domain, docs in graph['domain_freq']:
        lines.append(f'| {domain} | {len(docs)} | {", ".join(docs[:10])}{"..." if len(docs) > 10 else ""} |')

    # Quellenklassifikation
    lines += [
        '',
        '## Quellenklassifikation',
        '',
        '### Verteilung nach Quellentyp',
        '',
        '| Typ | Anzahl | Anteil |',
        '|-----|--------|--------|',
    ]
    total = graph['stats']['total_docs']
    for typ in ['primaer', 'sekundaer', 'grau', 'journalistisch', 'tertiaer', 'aktivistisch']:
        count = graph.get('typ_counts', {}).get(typ, 0)
        pct = f'{count/total*100:.0f}%' if total > 0 else '0%'
        lines.append(f'| {TYP_LABELS.get(typ, typ)} | {count} | {pct} |')

    lines += [
        '',
        '### Verteilung nach Evidenzgrad',
        '',
        '| Evidenzgrad | Anzahl | Anteil |',
        '|-------------|--------|--------|',
    ]
    for grad in ['hoch', 'mittel', 'niedrig']:
        count = graph.get('evidenz_counts', {}).get(grad, 0)
        pct = f'{count/total*100:.0f}%' if total > 0 else '0%'
        lines.append(f'| {grad} | {count} | {pct} |')

    lines += [
        '',
        '### Farbcodierung im Graph',
        '',
        '- **Blau** = Primaerquelle (Gesetze, Amtliche Dokumente, Risikoanalysen)',
        '- **Violett** = Sekundaerquelle (Think-Tank-Studien, Peer-reviewed, Fachanalysen)',
        '- **Orange** = Graue Literatur (Behoerdenberichte, Policy Briefs, Working Papers)',
        '- **Gruen** = Journalistische Quelle (Nachrichtenartikel, Investigativ)',
        '- **Grau** = Tertiaerquelle (Wikipedia, Enzyklopaedien)',
        '- **Rot** = Aktivistische Quelle (NGOs, Interessengruppen)',
        '',
        '### Vollstaendige Klassifikationstabelle',
        '',
        '| Dok | Label | Typ | Institution | Jahr | Evidenz |',
        '|-----|-------|-----|-------------|------|---------|',
    ]
    for doc_id in sorted(graph['classification'].keys(), key=lambda x: int(x)):
        meta = graph['classification'][doc_id]
        label = graph['doc_labels'].get(doc_id, '?')
        lines.append(
            f'| {doc_id} | {label} | {meta["typ"]} | {meta["institution"]} '
            f'| {meta.get("jahr", "?")} | {meta["evidenzgrad"]} |'
        )

    lines += [
        '',
        '## Isolierte Dokumente',
        '',
        'Diese Dokumente teilen keine URLs mit anderen Dokumenten im Korpus:',
        '',
    ]
    for doc_id in graph['isolated']:
        label = graph['doc_labels'].get(doc_id, '?')
        meta = graph['classification'].get(doc_id, {})
        typ = meta.get('typ', '?')
        lines.append(f'- {doc_id}: {label} ({typ})')

    lines += [
        '',
        '## Kookkurrenz-Graph',
        '',
        '```mermaid',
        generate_mermaid(graph),
        '```',
        '',
    ]
    return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='A311 Wissensgraph-Generator')
    parser.add_argument('--min-shared', type=int, default=DEFAULT_MIN_SHARED,
                        help='Mindestanzahl geteilter URLs fuer eine Kante')
    parser.add_argument('--output-dir', type=str, default=str(Path(__file__).parent),
                        help='Ausgabeverzeichnis')
    args = parser.parse_args()

    graph = build_graph(min_shared=args.min_shared)

    out = Path(args.output_dir)

    # JSON
    json_path = out / 'knowledge_graph.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f"JSON: {json_path}", file=sys.stderr)

    # Report
    report_path = out / 'knowledge_graph.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(generate_report(graph))
    print(f"Report: {report_path}", file=sys.stderr)

    # Zusammenfassung auf stdout
    print(json.dumps(graph['stats'], indent=2))


if __name__ == '__main__':
    main()
