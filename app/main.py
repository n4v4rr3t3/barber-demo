from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db, get_conn
from app.routes import public, admin

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="Black Barber")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health", include_in_schema=False)
def health():
    with get_conn() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(public.router)
app.include_router(admin.router)
