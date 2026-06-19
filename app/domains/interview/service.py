"""Der Interview-Loop. MVP-Geruest - die Konversationslogik baust du am
Wochenende mit Claude aus. Die Lueckenpruefung (gap_check) ist bereits real.
"""
from app.domains.interview.gap_check import build_followups, find_missing_risks


class InterviewService:
    def __init__(self, method_service, catalog_service):
        self.methods = method_service
        self.catalogs = catalog_service

    def followups_for_risks(self, project_type_id, entered_risk_texts):
        """Liefert konkrete Nachfragen fuer fehlende, typische Risiken."""
        catalog_risks = self.catalogs.salient_risks(project_type_id)
        missing = find_missing_risks(entered_risk_texts, catalog_risks)
        return build_followups(missing)

    # TODO (Wochenende): naechste-Frage-Logik, Antwortextraktion via LLM,
    # Vollstaendigkeitspruefung je Abschnitt (completeness aus method.yaml).
