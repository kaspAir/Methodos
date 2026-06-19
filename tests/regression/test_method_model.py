from app.config import get_config
from app.domains.method.service import MethodService


def test_pia_model_loads_with_expected_sections():
    svc = MethodService(get_config().METHODS_DIR)
    sections = svc.sections("hermes_pia")
    titles = [s["title"] for s in sections]
    assert "Ausgangslage" in titles
    assert "Risiken" in titles
    # Risiken muss eine Nachfrage-Sektion sein:
    gap = [s["id"] for s in svc.gap_check_sections("hermes_pia")]
    assert "risiken" in gap


def test_vocabularies_present():
    svc = MethodService(get_config().METHODS_DIR)
    model = svc.get("hermes_pia")
    assert model["vocabularies"]["prioritaet"] == ["Tief", "Mittel", "Hoch", "Muss"]
