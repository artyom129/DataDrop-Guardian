from app.config import load_settings
from app.database import clear, init_db
from app.engine import Engine
from app.main import demo_file
from pathlib import Path
import shutil, csv

settings=load_settings(); init_db(settings.database_path); clear(settings.database_path)
for folder in (settings.incoming_dir,settings.processed_dir,settings.quarantine_dir):
    for p in folder.iterdir():
        if p.is_file() and p.name!=".gitkeep": p.unlink()
engine=Engine(settings)
for kind in ("valid","invalid"):
    result=engine.process(demo_file(settings,kind))
    print(kind,result["status"])
first=demo_file(settings,"duplicate"); result=engine.process(first)
source=Path(result["file_id"] and next(settings.processed_dir.glob("customer_duplicate_*.csv")))
copy=settings.incoming_dir/"customer_duplicate_copy.csv"; shutil.copy2(source,copy)
print("duplicate",engine.process(copy)["status"])
print("Demo history created.")
