from pathlib import Path
from app.engine import Engine
from app.database import get_file

def valid(path):
    path.write_text("customer_id,name,email,balance,signup_date\n1,Alice,alice@example.com,10,2026-08-01\n",encoding="utf-8")

def test_accept(settings):
    p=settings.incoming_dir/"customer_ok.csv"; valid(p)
    r=Engine(settings).process(p)
    assert r["status"]=="accepted"
    assert Path(get_file(settings.database_path,r["file_id"])["final_path"]).parent==settings.processed_dir

def test_quarantine(settings):
    p=settings.incoming_dir/"customer_bad.csv"
    p.write_text("customer_id,name,email,balance,signup_date\n1,,bad,-5,nope\n",encoding="utf-8")
    r=Engine(settings).process(p)
    assert r["status"]=="quarantined" and r["error_count"]>=4

def test_duplicate(settings):
    e=Engine(settings)
    a=settings.incoming_dir/"customer_one.csv"; valid(a); assert e.process(a)["status"]=="accepted"
    b=settings.incoming_dir/"customer_two.csv"; valid(b); assert e.process(b)["status"]=="duplicate"

def test_unknown_pipeline(settings):
    p=settings.incoming_dir/"random.csv"; p.write_text("a,b\n1,2\n",encoding="utf-8")
    assert Engine(settings).process(p)["status"]=="quarantined"
