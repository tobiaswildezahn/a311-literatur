# A311 — Strategische Planung Bevoelkerungsschutz Hamburg

## Projektstruktur

```
A311/
  CLAUDE.md                  ← Du bist hier
  Themenspeicher.md          ← Strategische Themen, Hypothesen, Forschungsfragen
  Literatur/
    md/                      ← Markdown-Korpus (180 Dokumente, mit YAML-Frontmatter)
    pdf/                     ← PDF-Originale (zum Lesen in PDF Expert, NICHT in Git)
    inbox/                   ← Drop-Zone fuer neue Dokumente (wird automatisch geleert)
    scripts/                 ← Python-Werkzeuge (extract_annotations, validate_frontmatter, etc.)
    daily_reports/           ← Automatische Tagesbriefings
    scripts/build_knowledge_graph.py ← Wissensgraph-Generator
    knowledge_graph.json     ← URL-Kookkurrenz-Netzwerk
    source_classification.json ← Quellenklassifikation (Legacy, Daten jetzt im Frontmatter)
    daily_history.json       ← Pipeline-State (letzer Lauf, bekannte URLs, Korpus-Statistik)
    FEHLENDE_DOWNLOADS.md    ← Dokumente die manuell heruntergeladen werden muessen
  output/                    ← Erzeugte Arbeitsdokumente (Vermerke, Praesentationen, etc.)
```

## Slash-Commands

| Command | Beschreibung |
|---------|-------------|
| `/a311-daily` | Voller Lauf: Recherche + Download + Klassifizierung + Report + E-Mail |
| `/a311-daily --inbox-only` | Nur Inbox verarbeiten, kein Report, keine Mail |
| `/a311-daily --dry-run` | Nur suchen, nichts herunterladen/committen |
| `/a311-daily --force` | Ignoriere History, durchsuche alles neu |
| `/a311-annotate` | PDF-Annotationen aus pdf/ in Korpus uebernehmen |
| `/a311-annotate 197` | Nur Nr. 197 annotieren |

## Dokument-Workflow

### Neue Quellen eingliedern
1. PDF/HTML/MD in `Literatur/inbox/` legen
2. `/a311-daily --inbox-only` ausfuehren
3. Dokument wird konvertiert, mit Frontmatter versehen, in `md/` gespeichert
4. PDF-Original wird nach `pdf/{NNN}_{Slug}.pdf` verschoben und in PDF Expert geoeffnet

### Dokument lesen und annotieren
1. PDF aus `Literatur/pdf/` in PDF Expert oeffnen
2. Wichtige Stellen gelb markieren (Highlight)
3. Kommentare an Markierungen schreiben
4. PDF Expert speichern (ueberschreibt die PDF in pdf/)
5. `/a311-annotate` ausfuehren — extrahiert Annotationen ins bestehende Markdown

### Inline-Markierungen im Markdown
Manuell oder automatisch (via PDF-Annotationen):
```markdown
Wichtiger Satz aus dem Dokument.
<!-- A311: Tobis Kommentar warum das relevant ist -->
```
Diese Marker werden bei Korpus-Suchen priorisiert.

## Frontmatter-Schema (13+1 Felder)

Jede .md-Datei in `Literatur/md/` hat diesen YAML-Header:

| Feld | Pflicht | Beschreibung |
|------|---------|-------------|
| nr | ja | Fortlaufende Dokumentnummer |
| title | ja | Dokumenttitel |
| datum | ja | Publikationsdatum (YYYY-MM-DD) |
| institution | ja | Herausgebende Organisation |
| typ | ja | primaer, sekundaer, grau, journalistisch, tertiaer, aktivistisch |
| evidenzgrad | ja | hoch, mittel, niedrig |
| thema | ja | Eines von 10 Themen (siehe unten) |
| ebene | ja | bund, land, kommune, nato, eu, international |
| schlagworte | ja | 2-6 lowercase Keywords mit Bindestrichen |
| zusammenfassung | ja | 1-3 Saetze, max 300 Zeichen |
| url | nein | Quell-URL |
| autor | nein | Personenname(n) |
| bezug | nein | Array von nr-Werten (Querverweise) |
| notizen | nein | Tobis Highlights und Kommentare aus PDF Expert |

### Thema-Vokabular (10 Werte)
- `Gesamtverteidigung/OPLAN`
- `KRITIS/Infrastrukturschutz`
- `Klimawandel/Naturgefahren`
- `Hybride Bedrohungen/Cyber`
- `Warnung/Uebungen/GeKoB`
- `Ehrenamt/Personal/BOS`
- `Strategietheorie`
- `NATO/International`
- `Recht/Gesetzgebung`
- `Bevoelkerungsschutz allgemein`

## Validierung

```bash
cd Literatur && uv run scripts/validate_frontmatter.py
```

Prueft: Pflichtfelder, Enum-Werte, Datumsformat, Zusammenfassungslaenge, doppelte Nummern, notizen-Typ.

## Ablageregeln

- **Literatur/md/**: Nur Markdown mit Frontmatter. Dateiname: `{NNN}_{Kurztitel}.md`
- **Literatur/pdf/**: PDF-Originale zum Lesen. Dateiname: `{NNN}_{Kurztitel}.pdf`
- **Literatur/inbox/**: Temporaer. Wird bei jedem `--inbox-only` geleert.
- **output/**: Alles was Claude erzeugt (Vermerke, Praesentationen, Analysen). NICHT in Git.
- **Themenspeicher.md**: Strategische Notizen, Hypothesen, Forschungsfragen. WIRD committed.

## Wichtig fuer Claude

- Lies IMMER die Frontmatter bevor du den Body eines Dokuments liest
- `zusammenfassung` und `notizen` reichen oft aus um Relevanz zu beurteilen
- `<!-- A311: -->` Marker im Body zeigen Tobis priorisierte Stellen
- Grepe nach `<!-- A311:` um alle annotierten Stellen im Korpus zu finden
- PDFs werden NICHT geloescht sondern nach pdf/ archiviert
- Nutze `uv` als Paketmanager fuer Python-Scripts
- Die Rechtssammlung unter `/Users/tobiaswildezahn/projekte/rechtssammlung/` ist READ-ONLY
