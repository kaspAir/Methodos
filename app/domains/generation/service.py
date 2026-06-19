"""Dokumenterzeugung: fuellt die originale HERMES-.dotx mit den Interview-
Inhalten und gibt eine .docx zurueck.

ANSATZ (template-getrieben, NICHT Layout-im-Code):
  1. Die .dotx ist die Quelle der Wahrheit (Layout, Kopfzeilen, Tabellen).
  2. .dotx entpacken (es ist ein ZIP mit XML).
  3. In word/document.xml die farbig-kursiven Beispiel-/Hilfetexte und
     Platzhalter durch die echten Inhalte ersetzen; Tabellenzeilen je nach
     Anzahl Eintraege duplizieren.
  4. Wieder als .docx zusammenpacken und validieren.

Derselbe Mechanismus traegt spaeter kundeneigene Vorlagen: nur die
Bindungspunkte (Zuordnung Abschnitt -> Stelle im Dokument) wechseln.

Dieses Modul ist bewusst ein dokumentierter Stub - die XML-Fuelllogik
entsteht am Wochenende.
"""
from pathlib import Path


class GenerationService:
    def __init__(self, method_service):
        self.methods = method_service

    def template_path(self, method_id):
        method = self.methods.get(method_id)
        return Path(method["_dir"]) / method["template"]

    def generate(self, method_id, session_answers, out_path):
        raise NotImplementedError(
            "Wochenend-Aufgabe: .dotx entpacken, Platzhalter/Beispielzeilen "
            "durch session_answers ersetzen, als .docx packen. "
            "Siehe Docstring fuer den Ansatz."
        )
