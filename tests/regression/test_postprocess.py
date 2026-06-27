"""Beweist: deterministische HERMES-Korrekturen nach dem Befüllen eines Abschnitts."""
from app.config import get_config
from app.domains.catalog.service import CatalogService
from app.domains.interview.service import (
    InterviewService,
    _assign_termine_dates,
    _termin_woche,
)
from app.domains.method.service import MethodService


def _pos(rows, needle):
    for i, r in enumerate(rows):
        if needle.lower() in r["ergebnis"].lower():
            return i
    raise AssertionError(f"{needle} nicht gefunden")


def test_termin_woche_abhaengigkeitsrang():
    # Analysen + Prototyp VOR der Studie, danach die Folgeergebnisse
    assert _termin_woche("Beschaffungsanalyse") < _termin_woche("Studie")
    assert _termin_woche("Schutzbedarfsanalyse") < _termin_woche("Studie")
    assert _termin_woche("Prototyp: Fahrzeug") < _termin_woche("Studie")
    assert _termin_woche("Studie") < _termin_woche("Meilenstein Weiteres Vorgehen")
    assert _termin_woche("Meilenstein Weiteres Vorgehen") < _termin_woche("Projektmanagementplan")
    assert _termin_woche("Projektmanagementplan") < _termin_woche("Durchfuehrungsauftrag")
    assert _termin_woche("Durchfuehrungsauftrag") < _termin_woche("Meilenstein Durchfuehrungsfreigabe")


def test_assign_termine_dates_sortiert_nach_abhaengigkeit():
    rows = [
        {"ergebnis": "Stakeholder-Liste"},
        {"ergebnis": "Studie"},
        {"ergebnis": "Rechtsgrundlagenanalyse"},
        {"ergebnis": "Schutzbedarfsanalyse"},
        {"ergebnis": "Meilenstein Weiteres Vorgehen"},
        {"ergebnis": "Projektmanagementplan"},
        {"ergebnis": "Durchfuehrungsauftrag"},
        {"ergebnis": "Meilenstein Durchfuehrungsfreigabe"},
        {"ergebnis": "Beschaffungsanalyse"},
        {"ergebnis": "Prototyp: SAP"},
    ]
    _assign_termine_dates(rows, "2026-08-03")
    # Studie kommt nach allen einfliessenden Ergebnissen
    studie = _pos(rows, "Studie")
    for vor in ("Rechtsgrundlagen", "Schutzbedarf", "Beschaffungsanalyse", "Prototyp"):
        assert _pos(rows, vor) < studie, f"{vor} muss vor der Studie liegen"
    # Folgekette nach der Studie
    assert studie < _pos(rows, "Weiteres Vorgehen") < _pos(rows, "Projektmanagementplan")
    assert _pos(rows, "Projektmanagementplan") < _pos(rows, "Durchfuehrungsauftrag")
    assert _pos(rows, "Durchfuehrungsauftrag") < _pos(rows, "Durchfuehrungsfreigabe")
    # Alle haben ein Datum
    assert all(r.get("termin") for r in rows)


def _svc():
    cfg = get_config()
    return InterviewService(MethodService(cfg.METHODS_DIR), CatalogService(cfg.CATALOGS_DIR), None)


def test_kosten_nur_initialisierung():
    rows = [
        {"phase": "Initialisierung", "betrag": "85000"},
        {"phase": "Konzept", "betrag": "120000"},
        {"phase": "Realisierung", "betrag": "340000"},
        {"phase": "Einführung", "betrag": "95000"},
        {"phase": "Abschluss", "betrag": "25000"},
    ]
    keep = InterviewService._kosten_initialisierung_only(rows)
    assert len(keep) == 1
    assert keep[0]["phase"] == "Initialisierung"
    assert keep[0]["betrag"] == "85000"


def test_kosten_fallback_wenn_keine_initialisierung():
    rows = [{"phase": "Realisierung", "betrag": "340000"}]
    keep = InterviewService._kosten_initialisierung_only(rows)
    assert keep == [{"phase": "Initialisierung", "betrag": ""}]


def test_personalaufwand_ergaenzt_anwendervertreter_und_entwickler():
    rows = [{"rolle": "Projektleiter", "name": "", "aufwand": "15"}]
    answers = {"termine": {"extracted": [
        {"ergebnis": "Beschaffungsanalyse", "abnahme": "Anwendervertreter"},
        {"ergebnis": "Prototyp: SAP", "abnahme": "Entwickler"},
    ]}}
    InterviewService._ensure_deliverable_roles(rows, answers)
    rollen = [r["rolle"] for r in rows]
    assert "Anwendervertreter" in rollen
    assert "Entwickler" in rollen


def test_personalaufwand_keine_dubletten():
    rows = [
        {"rolle": "Anwendervertreter", "name": "", "aufwand": "4"},
        {"rolle": "Entwickler", "name": "", "aufwand": "8"},
    ]
    answers = {"termine": {"extracted": [
        {"ergebnis": "Beschaffungsanalyse", "abnahme": "Anwendervertreter"},
        {"ergebnis": "Prototyp", "abnahme": "Entwickler"},
    ]}}
    InterviewService._ensure_deliverable_roles(rows, answers)
    assert len(rows) == 2  # nichts dupliziert


def test_personalaufwand_keine_zusatzrollen_ohne_ergebnis():
    rows = [{"rolle": "Projektleiter", "name": "", "aufwand": "15"}]
    answers = {"termine": {"extracted": [
        {"ergebnis": "Studie", "abnahme": "Projektleiter"},
    ]}}
    InterviewService._ensure_deliverable_roles(rows, answers)
    assert [r["rolle"] for r in rows] == ["Projektleiter"]


def test_postprocess_kosten_ueber_dispatch():
    svc = _svc()
    section = svc._section_by_id("hermes_pia", "kosten")
    section_answer = {"extracted": [
        {"phase": "Initialisierung", "betrag": "85000"},
        {"phase": "Konzept", "betrag": "120000"},
    ]}
    svc._postprocess_section(section, section_answer, {})
    assert section_answer["extracted"] == [{"phase": "Initialisierung", "betrag": "85000"}]


def test_projektorganisation_spalten_decken_vorlage_ab():
    """Vorlage hat 9 Monate + Bestätigung -> method.yaml muss 1:1 passen,
    sonst rutscht 'ausstehend' in eine Monatsspalte."""
    svc = _svc()
    section = svc._section_by_id("hermes_pia", "projektorganisation")
    cols = [c["id"] for c in section["columns"]]
    assert cols[0] == "rolle_person"
    assert cols[-1] == "bestaetigung"
    assert [f"monat_{i}" for i in range(1, 10)] == cols[1:-1]
