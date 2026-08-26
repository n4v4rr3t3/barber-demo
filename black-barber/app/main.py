from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routes import public, admin

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Black Barber — Demo")


@app.on_event("startup")
def on_startup():
    init_db()


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(public.router)
app.include_router(admin.router)
