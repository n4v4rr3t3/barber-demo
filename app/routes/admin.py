import os
import secrets
from pathlib import Path
from datetime import date

from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.database import BUSINESS, listar_turnos, actualizar_estado, USE_POSTGRES

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
router = APIRouter(prefix="/admin")
security = HTTPBasic()

ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASS = os.environ.get("ADMIN_PASS")
if not USE_POSTGRES:
    ADMIN_USER = ADMIN_USER or "admin"
    ADMIN_PASS = ADMIN_PASS or "blackbarber2026"


def verificar_credenciales(credentials: HTTPBasicCredentials = Depends(security)):
    if not ADMIN_USER or not ADMIN_PASS:
        raise HTTPException(status_code=503, detail="Panel admin no configurado")
    usuario_ok = secrets.compare_digest(credentials.username, ADMIN_USER)
    pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (usuario_ok and pass_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas", headers={"WWW-Authenticate": "Basic"})
    return credentials.username


@router.get("")
def dashboard(request: Request, fecha: str = None, user: str = Depends(verificar_credenciales)):
    fecha = fecha or date.today().isoformat()
    turnos = listar_turnos(fecha=fecha)
    todos = listar_turnos()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "business": BUSINESS, "turnos": turnos,
        "fecha": fecha, "hoy": date.today().isoformat(), "total_turnos": len(todos),
    })


@router.post("/turnos/{turno_id}/estado")
def cambiar_estado(turno_id: int, estado: str = Form(...), fecha: str = Form(...), user: str = Depends(verificar_credenciales)):
    try:
        actualizar_estado(turno_id, estado)
    except ValueError:
        raise HTTPException(400, "Estado inválido")
    return RedirectResponse(url=f"/admin?fecha={fecha}", status_code=303)
