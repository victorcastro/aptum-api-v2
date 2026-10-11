from fastapi.testclient import TestClient

from aptum.core.dependencies import get_db
from aptum.main import app
from aptum.modules.commons.models import Degree
from aptum.modules.commons.repository import CommonsRepository


def test_degrees_are_grouped_by_level_in_catalog_order(monkeypatch):
    catalog = [
        Degree(id=1, name="Technical Diploma", level="Technical and vocational", rank=1),
        Degree(id=2, name="Bachelor of Science", level="Undergraduate", rank=2),
        Degree(id=3, name="Bachelor of Arts", level="Undergraduate", rank=3),
    ]
    monkeypatch.setattr(CommonsRepository, "list_degrees", lambda self: catalog)
    app.dependency_overrides[get_db] = lambda: None
    try:
        response = TestClient(app).get("/commons/degrees")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert response.status_code == 200
    assert response.json() == [
        {"heading": "Technical and vocational", "options": [{"id": 1, "name": "Technical Diploma"}]},
        {
            "heading": "Undergraduate",
            "options": [{"id": 2, "name": "Bachelor of Science"}, {"id": 3, "name": "Bachelor of Arts"}],
        },
    ]
