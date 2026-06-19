"""Laedt Methoden-Modelle und Referenzkataloge aus YAML.

Das ist der Kern des Prinzips "Konfiguration vor Programmierung":
neue Methoden oder Projekttypen = neue YAML-Dateien, kein Codeumbau.
"""
from pathlib import Path

import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_method(methods_dir, method_id):
    path = Path(methods_dir) / method_id / "method.yaml"
    data = load_yaml(path)
    data["_dir"] = str(Path(methods_dir) / method_id)
    return data


def load_catalog(catalogs_dir, project_type_id):
    path = Path(catalogs_dir) / f"{project_type_id}.yaml"
    return load_yaml(path)
