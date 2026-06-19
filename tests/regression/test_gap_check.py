"""Beweist das Showpiece: fehlt ein typisches Risiko, wird nachgefragt."""
from app.config import get_config
from app.domains.catalog.service import CatalogService
from app.domains.interview.service import InterviewService
from app.domains.method.service import MethodService


def _interview():
    cfg = get_config()
    return InterviewService(MethodService(cfg.METHODS_DIR), CatalogService(cfg.CATALOGS_DIR))


def test_missing_acceptance_risk_triggers_followup():
    # Projektleiter hat nur das Beschaffungsrisiko erfasst.
    entered = ["Verzoegerung durch oeffentliche Beschaffung"]
    followups = _interview().followups_for_risks("fachanwendung_einfuehrung", entered)
    risk_ids = {f["risk_id"] for f in followups}
    # Akzeptanz und Schluesselpersonen fehlen -> muessen nachgefragt werden:
    assert "r_akzeptanz" in risk_ids
    assert "r_schluesselpersonen" in risk_ids


def test_covered_risk_is_not_asked_again():
    entered = ["Geringe Akzeptanz der Anwender, Widerstand gegen die Aenderung"]
    followups = _interview().followups_for_risks("fachanwendung_einfuehrung", entered)
    risk_ids = {f["risk_id"] for f in followups}
    assert "r_akzeptanz" not in risk_ids
