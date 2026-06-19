"""Stellt den Referenzkatalog eines Projekttyps bereit (abgeleitetes Wissen)."""
from app.shared.config_loader import load_catalog


class CatalogService:
    def __init__(self, catalogs_dir):
        self.catalogs_dir = catalogs_dir
        self._cache = {}

    def get(self, project_type_id):
        if project_type_id not in self._cache:
            self._cache[project_type_id] = load_catalog(self.catalogs_dir, project_type_id)
        return self._cache[project_type_id]

    def salient_risks(self, project_type_id, threshold=0.8):
        risks = self.get(project_type_id).get("risiken", [])
        return [r for r in risks if r.get("salience", 0) >= threshold]
