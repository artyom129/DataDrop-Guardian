from __future__ import annotations
import asyncio, csv, shutil
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .config import load_settings
from .database import get_file, init_db, list_files, stats
from .engine import Engine
from .exporter import csv_bytes, xlsx_bytes

BASE = Path(__file__).resolve().parent

def demo_file(settings, kind):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = settings.incoming_dir / f"customer_{kind}_{stamp}.csv"
    rows = {
        "valid": [
            ["customer_id","name","email","balance","signup_date"],
            ["101","Anna Stone","anna@example.com","125.50","2026-08-01"],
            ["102","Mark Green","mark@example.com","0","2026-08-02"],
        ],
        "invalid": [
            ["customer_id","name","email","balance","signup_date"],
            ["201","","broken-email","-25","2026/08/01"],
            ["201","Duplicate","dupe@example.com","40","2026-08-02"],
            ["201","Duplicate Again","dupe2@example.com","45","2026-08-03"],
        ],
        "duplicate": [
            ["customer_id","name","email","balance","signup_date"],
            ["301","Same File","same@example.com","20","2026-08-01"],
        ],
    }
    if kind not in rows:
        raise ValueError(kind)
    with path.open("w",encoding="utf-8",newline="") as fh:
        csv.writer(fh).writerows(rows[kind])
    return path

def create_app(config_path=None, settings_override=None):
    settings = settings_override or load_settings(config_path)
    init_db(settings.database_path)
    engine = Engine(settings)

    @asynccontextmanager
    async def lifespan(app):
        stop = asyncio.Event()
        async def monitor():
            while not stop.is_set():
                for path in sorted(settings.incoming_dir.iterdir()):
                    if path.is_file() and not path.name.startswith("."):
                        try:
                            await asyncio.to_thread(engine.process, path)
                        except FileNotFoundError:
                            pass
                try:
                    await asyncio.wait_for(stop.wait(), timeout=settings.scan_interval_seconds)
                except asyncio.TimeoutError:
                    pass
        task = asyncio.create_task(monitor())
        yield
        stop.set(); task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    templates = Jinja2Templates(directory=BASE/"templates")
    app.mount("/static", StaticFiles(directory=BASE/"static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse(request=request,name="dashboard.html",context={
            "app_name":settings.app_name,"stats":stats(settings.database_path),
            "rows":list_files(settings.database_path,limit=12)
        })

    @app.get("/files", response_class=HTMLResponse)
    async def files_page(request: Request,status: str|None=None,q: str|None=None):
        return templates.TemplateResponse(request=request,name="files.html",context={
            "app_name":settings.app_name,
            "rows":list_files(settings.database_path,status=status or None,query=q or None),
            "status":status or "","q":q or ""
        })

    @app.get("/files/{file_id}", response_class=HTMLResponse)
    async def detail(request: Request,file_id:int):
        item=get_file(settings.database_path,file_id)
        if not item: raise HTTPException(404,"File not found")
        return templates.TemplateResponse(request=request,name="detail.html",context={
            "app_name":settings.app_name,"item":item
        })

    @app.post("/demo/{kind}")
    async def demo(kind:str):
        if kind=="duplicate":
            first=demo_file(settings,"duplicate")
            engine.process(first)
            source=next(settings.processed_dir.glob("customer_duplicate_*.csv"))
            target=settings.incoming_dir/f"customer_duplicate_copy_{datetime.now().timestamp():.0f}.csv"
            shutil.copy2(source,target)
            engine.process(target)
        else:
            engine.process(demo_file(settings,kind))
        return RedirectResponse("/",303)

    @app.post("/upload")
    async def upload(file:UploadFile=File(...)):
        target=settings.incoming_dir/Path(file.filename or "upload.bin").name
        target.write_bytes(await file.read())
        engine.process(target)
        return RedirectResponse("/",303)

    @app.post("/files/{file_id}/retry")
    async def retry(file_id:int):
        item=get_file(settings.database_path,file_id)
        if not item: raise HTTPException(404,"File not found")
        source=Path(item["final_path"])
        if not source.exists(): raise HTTPException(404,"File missing")
        target=settings.incoming_dir/f"{source.stem}_retry{source.suffix}"
        shutil.copy2(source,target); engine.process(target)
        return RedirectResponse("/files",303)

    @app.post("/api/demo/{kind}")
    async def api_demo(kind:str):
        if kind not in {"valid","invalid","duplicate"}: raise HTTPException(404,"Unknown demo")
        if kind=="duplicate":
            first=demo_file(settings,"duplicate"); one=engine.process(first)
            source=Path(get_file(settings.database_path,one["file_id"])["final_path"])
            target=settings.incoming_dir/f"customer_duplicate_copy_{datetime.now().timestamp():.0f}.csv"
            shutil.copy2(source,target); return engine.process(target)
        return engine.process(demo_file(settings,kind))

    @app.post("/api/upload")
    async def api_upload(file:UploadFile=File(...)):
        target=settings.incoming_dir/Path(file.filename or "upload.bin").name
        target.write_bytes(await file.read())
        return engine.process(target)

    @app.get("/api/files")
    async def api_files(status:str|None=None,limit:int=200):
        return {"items":list_files(settings.database_path,status=status,limit=min(max(limit,1),10000)),
                "stats":stats(settings.database_path)}

    @app.get("/api/files/{file_id}")
    async def api_file(file_id:int):
        item=get_file(settings.database_path,file_id)
        if not item: raise HTTPException(404,"File not found")
        return item

    @app.get("/api/stats")
    async def api_stats(): return stats(settings.database_path)

    @app.get("/exports/files.csv")
    async def export_csv():
        return Response(csv_bytes(list_files(settings.database_path,limit=10000)),
            media_type="text/csv",headers={"Content-Disposition":"attachment; filename=datadrop_audit.csv"})

    @app.get("/exports/files.xlsx")
    async def export_xlsx():
        return Response(xlsx_bytes(list_files(settings.database_path,limit=10000)),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition":"attachment; filename=datadrop_audit.xlsx"})

    @app.get("/health")
    async def health():
        return {"status":"ok","pipelines":len(settings.pipelines),"incoming":str(settings.incoming_dir)}

    return app

app=create_app()
