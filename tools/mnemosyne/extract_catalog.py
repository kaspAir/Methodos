#!/usr/bin/env python3
"""
tools/mnemosyne/extract_catalog.py

Mnemosyne-Prototyp Schritt 2: Extrahiert Wissen aus pseudonymisierten PIAs
und schlägt Katalogerweiterungen vor.

Verwendet die Anthropic API – aber nur auf bereits pseudonymisierten Texten!
Keine Originaldaten werden je an die Cloud gesendet.

Verwendung:
    python tools/mnemosyne/extract_catalog.py \
        --input   C:/Pfad/zu/output \
        --api-key $ANTHROPIC_API_KEY

    Oder via .env:
        ANTHROPIC_API_KEY=sk-ant-... python tools/mnemosyne/extract_catalog.py \
            --input C:/Pfad/zu/output

Ausgabe:
    <input>/catalog_additions.yaml   Vorgeschlagene Katalogeinträge (YAML)
    <input>/extraction_log.json      Rohdaten der Extraktion pro Dokument
"""
import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

import anthropic
import yaml


_SYSTEM_PROMPT = """\
Du bist ein HERMES-2022-Experte und analysierst pseudonymisierte \
Projektinitialisierungsaufträge (PIAs) aus dem Schweizer öffentlichen Sektor.

Extrahiere aus dem folgenden Text die strukturierten Informationen und gib \
sie als JSON zurück. Alle Namen (Personen, Organisationen) sind bereits \
pseudonymisiert ([Person_001], [Org_001] etc.) – ignoriere sie inhaltlich.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, kein Markdown, kein Text darum.
"""

_EXTRACTION_PROMPT = """\
Analysiere diesen pseudonymisierten HERMES-PIA-Text:

{text}

Extrahiere:
1. projekt_typ: Welcher HERMES-Projekttyp passt am besten?
   Möglichkeiten: "fachanwendung_einfuehrung", "organisationsentwicklung",
   "infrastruktur", "e_government", "studie", "unbekannt"
2. risiken: Liste der erwähnten Risiken (max. 10)
   Format: [{{"beschreibung": "...", "kategorie": "...", "schlagworte": [...]}}]
3. ziele: Liste der erwähnten Projektziele (max. 8)
   Format: [{{"beschreibung": "...", "kategorie": "Systemziel|Vorgehensziel"}}]
4. lieferergebnisse: Erwähnte Lieferergebnisse (max. 8)
   Format: [{{"name": "..."}}]
5. ausgangslage_zusammenfassung: 1-2 Sätze (pseudonymisiert, kein Original)

Antworte nur mit JSON:
{{
  "projekt_typ": "...",
  "risiken": [...],
  "ziele": [...],
  "lieferergebnisse": [...],
  "ausgangslage_zusammenfassung": "..."
}}
"""


def extract_from_pia(client: anthropic.Anthropic, text: str, model: str) -> dict:
    # Längere Texte auf ~8000 Zeichen kürzen (PIA-Inhalte sind selten länger)
    truncated = text[:8000]
    if len(text) > 8000:
        truncated += "\n[... Text gekürzt ...]"

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT.format(text=truncated)}],
    )
    raw = response.content[0].text.strip()

    # Markdown-Fences entfernen falls vorhanden
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1]
        raw = raw.rsplit('```', 1)[0]

    return json.loads(raw)


def aggregate_results(extractions: list[dict]) -> dict:
    """Aggregiert Extraktionsergebnisse und berechnet salience-Werte."""
    from collections import Counter, defaultdict

    total = len(extractions)
    risk_counter: Counter = Counter()
    risk_meta: dict = {}
    ziel_counter: Counter = Counter()
    lieferergebnis_counter: Counter = Counter()
    projekt_typ_counter: Counter = Counter()

    for ex in extractions:
        typ = ex.get('projekt_typ', 'unbekannt')
        projekt_typ_counter[typ] += 1

        for r in ex.get('risiken', []):
            desc = r.get('beschreibung', '').strip()
            if desc and len(desc) > 10:
                # Normalisierung: lowercase für Zählung
                key = desc.lower()[:60]
                risk_counter[key] += 1
                if key not in risk_meta:
                    risk_meta[key] = r

        for z in ex.get('ziele', []):
            desc = z.get('beschreibung', '').strip()
            if desc and len(desc) > 10:
                ziel_counter[desc.lower()[:60]] += 1

        for le in ex.get('lieferergebnisse', []):
            name = le.get('name', '').strip()
            if name and len(name) > 3:
                lieferergebnis_counter[name.lower()] += 1

    def salience(count: int, n: int) -> float:
        return round(min(count / n, 1.0), 2)

    # Nur Einträge mit salience >= 0.3 (mindestens 30% der PIAs)
    threshold = max(1, total * 0.3)

    risiken_yaml = []
    for key, count in risk_counter.most_common(20):
        if count >= threshold:
            meta = risk_meta[key]
            risiken_yaml.append({
                'beschreibung': meta.get('beschreibung', key),
                'kategorie': meta.get('kategorie', ''),
                'salience': salience(count, total),
                'schlagworte': meta.get('schlagworte', []),
                '_vorkommen': f"{count}/{total}",
            })

    return {
        'projekt_typen': dict(projekt_typ_counter.most_common()),
        'gesamt_pias': total,
        'risiken': risiken_yaml,
        'haeufige_ziele': [
            {'beschreibung': k[:80], '_vorkommen': f"{v}/{total}"}
            for k, v in ziel_counter.most_common(10)
            if v >= threshold
        ],
        'haeufige_lieferergebnisse': [
            {'name': k[:60], '_vorkommen': f"{v}/{total}"}
            for k, v in lieferergebnis_counter.most_common(10)
            if v >= threshold
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description='Mnemosyne: Wissensextraktion aus pseudonymisierten PIAs'
    )
    parser.add_argument('--input',   required=True,
                        help='Ordner mit *_pseudo.txt Dateien (Ausgabe von pseudonymize.py)')
    parser.add_argument('--api-key', default=os.environ.get('ANTHROPIC_API_KEY'),
                        help='Anthropic API Key (oder ANTHROPIC_API_KEY env)')
    parser.add_argument('--model',   default='claude-haiku-4-5-20251001',
                        help='Claude-Modell für Extraktion (Standard: Haiku – kostengünstig)')
    parser.add_argument('--limit',   type=int, default=0,
                        help='Anzahl Dateien begrenzen (0 = alle, nützlich zum Testen)')
    args = parser.parse_args()

    if not args.api_key:
        print("[FEHLER] Kein API-Key. Setze ANTHROPIC_API_KEY oder übergib --api-key.")
        sys.exit(1)

    input_dir = Path(args.input)
    files = sorted(input_dir.glob('*_pseudo.txt'))

    if not files:
        print(f"[FEHLER] Keine *_pseudo.txt Dateien in {input_dir}")
        print("  Zuerst pseudonymize.py ausführen!")
        sys.exit(1)

    if args.limit > 0:
        files = files[:args.limit]

    print(f"[Mnemosyne] Extraktion: {len(files)} Dateien mit Modell '{args.model}'")
    print(f"  Hinweis: Nur pseudonymisierte Daten werden an die API gesendet.\n")

    client = anthropic.Anthropic(api_key=args.api_key)

    extractions = []
    log_path = input_dir / 'extraction_log.json'

    for i, f in enumerate(files, 1):
        print(f"  [{i:3d}/{len(files)}] {f.name} … ", end='', flush=True)
        try:
            text = f.read_text(encoding='utf-8')
            result = extract_from_pia(client, text, args.model)
            result['_datei'] = f.name
            extractions.append(result)
            typ = result.get('projekt_typ', '?')
            n_risiken = len(result.get('risiken', []))
            print(f"OK  (Typ: {typ}, {n_risiken} Risiken)")
        except Exception as exc:
            print(f"FEHLER: {exc}")
            extractions.append({'_datei': f.name, '_fehler': str(exc)})

    # Log speichern
    log_path.write_text(json.dumps(extractions, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n[Mnemosyne] Rohdaten gespeichert: {log_path}")

    # Aggregieren
    valid = [e for e in extractions if '_fehler' not in e]
    if not valid:
        print("[FEHLER] Keine erfolgreichen Extraktionen.")
        sys.exit(1)

    print(f"[Mnemosyne] Aggregiere {len(valid)} erfolgreiche Extraktionen …")
    aggregated = aggregate_results(valid)

    # YAML ausgeben
    output_yaml = {
        '_mnemosyne_meta': {
            'quellen': f"{len(valid)} pseudonymisierte PIAs",
            'modell': args.model,
            'hinweis': (
                "Abgeleitetes Wissen – keine Rohdaten. "
                "Salience-Werte aus echter Häufigkeitsanalyse."
            ),
        },
        **aggregated,
    }

    yaml_path = input_dir / 'catalog_additions.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as fh:
        yaml.dump(output_yaml, fh, allow_unicode=True, default_flow_style=False,
                  sort_keys=False)

    print(f"[Mnemosyne] Katalog-Vorschläge gespeichert: {yaml_path}")
    print()

    # Kurze Zusammenfassung
    print("── Zusammenfassung ─────────────────────────────────────")
    print(f"  PIAs ausgewertet:   {len(valid)}")
    print(f"  Projekttypen:       {aggregated['projekt_typen']}")
    print(f"  Risiken vorgeschlagen: {len(aggregated['risiken'])}")
    print(f"  Nächster Schritt: catalog_additions.yaml prüfen und in")
    print(f"  catalogs/<projekttyp>.yaml einarbeiten.")


if __name__ == '__main__':
    main()
