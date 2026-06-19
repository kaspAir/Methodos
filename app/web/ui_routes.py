"""Minimale Routen, damit das Geruest laeuft. Die richtige UI baust du am
Wochenende (z.B. ein Decision-/Interview-Workspace analog Kairon).
"""
from flask import Blueprint, current_app, jsonify, render_template

bp = Blueprint("ui", __name__)


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "methodos"})


@bp.get("/")
def index():
    method = current_app.method_service.get("hermes_pia")
    sections = current_app.method_service.sections("hermes_pia")
    return render_template("index.html", method=method, sections=sections)


@bp.get("/demo/followups")
def demo_followups():
    """Zeigt das Nachfrage-Verhalten deterministisch.

    Beispiel: der Projektleiter hat nur EIN Risiko erfasst. Methodos erkennt,
    welche fuer diesen Projekttyp typischen Risiken fehlen, und fragt nach.
    """
    entered = ["Verzoegerung durch oeffentliche Beschaffung"]
    followups = current_app.interview_service.followups_for_risks(
        "fachanwendung_einfuehrung", entered
    )
    return jsonify({"erfasst": entered, "nachfragen": followups})
