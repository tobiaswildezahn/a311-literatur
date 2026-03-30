#!/usr/bin/env python3
"""Validiert alle Frontmatter im Korpus gegen das neue Schema."""
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///

import os
import re
import sys

import yaml

THEMA = ['Gesamtverteidigung/OPLAN', 'KRITIS/Infrastrukturschutz', 'Klimawandel/Naturgefahren',
         'Hybride Bedrohungen/Cyber', 'Warnung/Uebungen/GeKoB', 'Ehrenamt/Personal/BOS',
         'Strategietheorie', 'NATO/International', 'Recht/Gesetzgebung', 'Bevoelkerungsschutz allgemein']
EBENE = ['bund', 'land', 'kommune', 'nato', 'eu', 'international']
TYP = ['primaer', 'sekundaer', 'grau', 'journalistisch', 'tertiaer', 'aktivistisch']
EVIDENZ = ['hoch', 'mittel', 'niedrig']
REQUIRED = ['nr', 'title', 'datum', 'institution', 'typ', 'evidenzgrad', 'thema', 'ebene', 'schlagworte', 'zusammenfassung']

errors = []
todo_summary = 0
todo_tags = 0
annotated_count = 0
ok = 0
all_nrs = set()

md_dir = os.path.join(os.path.dirname(__file__), 'md')

for f in sorted(os.listdir(md_dir)):
    if not f.endswith('.md') or not re.match(r'^\d+_', f):
        continue
    path = os.path.join(md_dir, f)
    text = open(path, encoding='utf-8').read()
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        errors.append(f'{f}: kein Frontmatter')
        continue
    # Finde das schließende --- (muss eine eigene Zeile sein)
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            end_idx = i
            break
    if end_idx is None:
        errors.append(f'{f}: kein schließendes ---')
        continue
    yaml_block = '\n'.join(lines[1:end_idx])
    try:
        meta = yaml.safe_load(yaml_block)
    except Exception as e:
        errors.append(f'{f}: YAML-Fehler: {e}')
        continue
    if not meta:
        errors.append(f'{f}: leeres Frontmatter')
        continue

    for field in REQUIRED:
        if field not in meta:
            errors.append(f'{f}: fehlt {field}')

    if meta.get('thema') not in THEMA:
        errors.append(f'{f}: ungültiges thema: {meta.get("thema")}')
    if meta.get('ebene') not in EBENE:
        errors.append(f'{f}: ungültige ebene: {meta.get("ebene")}')
    if meta.get('typ') not in TYP:
        errors.append(f'{f}: ungültiger typ: {meta.get("typ")}')
    if meta.get('evidenzgrad') not in EVIDENZ:
        errors.append(f'{f}: ungültiger evidenzgrad: {meta.get("evidenzgrad")}')

    if meta.get('zusammenfassung') == 'TODO':
        todo_summary += 1
    if meta.get('schlagworte') == ['TODO']:
        todo_tags += 1

    d = str(meta.get('datum', ''))
    if d and not re.match(r'^\d{4}-\d{2}-\d{2}$', d):
        errors.append(f'{f}: ungültiges datum: {d}')

    zf = str(meta.get('zusammenfassung', ''))
    if zf != 'TODO' and len(zf) > 350:
        errors.append(f'{f}: zusammenfassung zu lang: {len(zf)} Zeichen')

    # notizen: optional, aber wenn vorhanden muss es ein String sein
    notizen = meta.get('notizen')
    if notizen is not None:
        if not isinstance(notizen, str):
            errors.append(f'{f}: notizen muss ein String sein, ist {type(notizen).__name__}')
        elif len(str(notizen)) > 2000:
            errors.append(f'{f}: notizen zu lang: {len(str(notizen))} Zeichen (max 2000)')
        annotated_count += 1

    nr = meta.get('nr')
    if nr in all_nrs:
        errors.append(f'{f}: doppelte nr: {nr}')
    all_nrs.add(nr)

    # bezug: alle referenzierten nrs existieren?
    bezug = meta.get('bezug', [])
    if isinstance(bezug, list):
        for ref in bezug:
            if isinstance(ref, int) and ref not in all_nrs:
                pass  # Kann erst nach vollständigem Scan geprüft werden

    ok += 1

print(f'Dateien geprüft: {ok}')
print(f'TODO Summary:    {todo_summary}')
print(f'TODO Tags:       {todo_tags}')
print(f'Mit Notizen:     {annotated_count}')
print(f'Fehler:          {len(errors)}')
for e in errors:
    print(f'  {e}')

sys.exit(1 if errors else 0)
