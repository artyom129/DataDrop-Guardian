from fastapi.testclient import TestClient
from app.main import create_app

def test_demo_and_export(settings):
    with TestClient(create_app(settings_override=settings)) as c:
        assert c.get("/health").status_code==200
        assert c.post("/api/demo/valid").json()["status"]=="accepted"
        assert c.post("/api/demo/invalid").json()["status"]=="quarantined"
        assert len(c.get("/api/files").json()["items"])==2
        assert c.get("/exports/files.xlsx").content.startswith(b"PK")

def test_upload(settings):
    content=b"customer_id,name,email,balance,signup_date\n5,John,john@example.com,20,2026-08-01\n"
    with TestClient(create_app(settings_override=settings)) as c:
        r=c.post("/api/upload",files={"file":("customer_api.csv",content,"text/csv")})
        assert r.status_code==200 and r.json()["status"]=="accepted"
